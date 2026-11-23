from __future__ import annotations

import csv
import json
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from openpyxl import Workbook, load_workbook

from purway_geotagger.core.pac_calculator import calculate_pac
from purway_geotagger.core.preview import build_preview
from purway_geotagger.core.scanner import scan_inputs
from purway_geotagger.ops.methane_outputs import generate_methane_outputs, cleaned_csv_path
from purway_geotagger.ops.table_export import write_tables
from purway_geotagger.parsers.columns import pick_column, PPM_COL_CANDIDATES, REL_ALT_COL_CANDIDATES
from purway_geotagger.parsers.purway_csv import PurwayCSVIndex
from purway_geotagger.parsers.table_inputs import read_tables
from purway_geotagger.util.errors import CorrelationError, UserCancelledError


def csv_file(path, header, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def workbook_file(path, sheets):
    book = Workbook()
    book.remove(book.active)
    for name, rows in sheets.items():
        sheet = book.create_sheet(name)
        for row in rows:
            sheet.append(row)
    book.save(path)
    book.close()
    return path


def csv_values(path):
    with path.open(newline='', encoding='utf-8') as f:
        return list(csv.reader(f))


@pytest.mark.parametrize('enabled,calibration,threshold,retained,unavailable', [(True, 3, 1, 6, 4), (False, 0, 1, 9, 6)])
def test_calibration_boundaries_counts_and_atomic_repeat(tmp_path, enabled, calibration, threshold, retained, unavailable):
    path = csv_file(tmp_path/'readings.csv', ['methane_concentration','relative_altitude','photo'], [
        [1500,-1,'a.jpg'], [1500,0,'a.jpg'], [1500,.99,'a.jpg'], [1500,1,'a.jpg'],
        [1500,2,'a.jpg'], [0,0,'a.jpg'], [1500,'','a.jpg'], [1500,'bad','a.jpg'],
        [1500,'NaN','a.jpg'], [1500,'inf','a.jpg'], [1500,2,'missing.jpg'],
        ['inf',2,'a.jpg'], ['NaN',2,'a.jpg'], ['',2,'a.jpg'],
    ])
    (tmp_path/'a.jpg').touch()
    original = path.read_bytes()
    for _ in range(2):
        result, = generate_methane_outputs([path], 1000, False, enabled)
        assert result.cleaned_status == 'success', result.cleaned_error
        counts = result.counts
        assert counts['calibration_excluded'] == calibration
        assert counts['threshold_excluded'] == threshold
        assert counts['missing_photo_rows'] == 1
        assert counts['invalid_methane_excluded'] == 3
        assert counts['retained_rows'] == retained
        assert counts['pac_unavailable'] == unavailable
        assert counts['altitude_unavailable'] == 4
        assert counts['input_rows'] == sum(counts[k] for k in ('calibration_excluded','threshold_excluded','missing_photo_rows','invalid_methane_excluded','retained_rows'))
        assert result.warnings and len(csv_values(result.cleaned_csv)) == retained + 1
    assert path.read_bytes() == original
    assert not list(tmp_path.glob('.purway-*'))


def test_zero_methane_is_not_calibration_and_missing_altitude(tmp_path):
    path = csv_file(tmp_path/'zero.csv', ['methane_concentration','relative_altitude'], [[0,-1],[0,0],[0,.99],[0,1]])
    result, = generate_methane_outputs([path], 0, False)
    assert result.counts['calibration_excluded'] == 0
    assert result.cleaned_rows == 4
    path = csv_file(tmp_path/'no-alt.csv', ['methane_concentration'], [[1500]])
    result, = generate_methane_outputs([path],1000,False)
    assert csv_values(result.cleaned_csv) == [['methane_concentration','PAC'],['1500','']]
    assert result.counts['pac_unavailable'] == 1
    assert result.counts['altitude_unavailable'] == 1


@pytest.mark.parametrize('position', [0,1,2])
@pytest.mark.parametrize('header', ['PAC',' pAc '])
@pytest.mark.parametrize('suffix', ['.csv','.xlsx'])
def test_existing_pac_is_authoritative(tmp_path, position, header, suffix):
    columns = ['methane_concentration','relative_altitude']
    columns.insert(position, header)
    rows = []
    for pac in ('',999,'literal'):
        row = [1500,3]
        row.insert(position,pac)
        rows.append(row)
    path = tmp_path/('pac'+suffix)
    if suffix == '.csv':
        csv_file(path, columns, rows)
    else:
        workbook_file(path, {'Data':[columns,*rows]})
    result, = generate_methane_outputs([path],1000,False)
    assert result.cleaned_status == 'success', result.cleaned_error
    table, = read_tables(result.cleaned_csv)
    assert table.columns == columns
    actual = [row.values[position] for row,_ in table.data_rows()]
    assert [(str(v) if v is not None else '') for v in actual] == ['', '999', 'literal']
    assert result.counts['pac_preserved'] == 3
    assert result.counts['pac_calculated'] == result.counts['pac_unavailable'] == 0


@pytest.mark.parametrize('ppm,altitude', [(float('nan'),2),(float('inf'),2),(1,float('inf')),(1,float('nan')),(1e308,1e-308)])
def test_shared_pac_rejects_nonfinite_inputs_and_result(ppm, altitude):
    assert calculate_pac(ppm,altitude) is None


def test_workbook_all_sheets_values_formats_matching_and_kmz(tmp_path):
    path = workbook_file(tmp_path/'mission.xlsx', {
        'Flight A': [['Pilot notes'], [], ['photo','relative_altitude','methane_concentration','latitude','longitude','time'],
                     ['a.jpg',.5,1500,28,-97,datetime(2026,9,28,9,30)],
                     ['b.jpg',3,1600,28,-97,datetime(2026,9,28,15,30)]],
        'Hidden Flight': [['PAC','Methane Concentration','Relative-Altitude','Latitude','Longitude','Photo'],
                          [999,2000,2,29,-98,'c.jpg'],[None,2000,2,29,-98,'d.jpg']],
        'Notes': [['Notes'], ['=literal text'], [datetime(2026,9,28)]],
    })
    book=load_workbook(path)
    book['Hidden Flight'].sheet_state='hidden'
    book['Notes']['A2'].data_type='s'
    book['Notes']['A3'].number_format='yyyy-mm-dd'
    book['Flight A']['F5'].number_format='h:mm AM/PM'
    book.save(path)
    book.close()
    for name in 'abcd':
        (tmp_path/f'{name}.jpg').touch()
    original=path.read_bytes()
    index=PurwayCSVIndex.from_csv_files([path])
    assert not index.errors
    match=index.match_photo(tmp_path/'b.jpg',3)
    assert (match.source_sheet,match.source_row,match.pac)==('Flight A',5,533.33)
    assert index.match_photo(tmp_path/'a.jpg',3).pac==3000
    assert index.match_photo(tmp_path/'c.jpg',3).pac==1000  # independent of saved PAC 999
    result,=generate_methane_outputs([path],1000,True)
    assert result.cleaned_status==result.kmz_status=='success', (result.cleaned_error,result.kmz_error)
    assert result.cleaned_rows==result.kmz_rows==3
    assert result.counts['calibration_excluded']==1
    assert result.counts['pac_preserved']==2
    assert result.counts['pac_calculated']==1
    output=load_workbook(result.cleaned_csv,data_only=False)
    assert output.sheetnames==['Flight A','Hidden Flight','Notes']
    assert output['Hidden Flight'].sheet_state=='hidden'
    assert output['Flight A']['A1'].value=='Pilot notes'
    assert output['Flight A']['A4'].value=='b.jpg'
    assert output['Flight A']['G4'].value==match.pac
    assert output['Flight A']['F4'].number_format=='h:mm AM/PM'
    assert output['Notes']['A2'].value=='=literal text' and output['Notes']['A2'].data_type=='s'
    assert output['Notes']['A3'].number_format=='yyyy-mm-dd'
    assert output['Hidden Flight']['A3'].value is None
    output.close()
    assert result.kmz.name.endswith('_XLSX.kmz')
    with zipfile.ZipFile(result.kmz) as archive:
        kml=ET.fromstring(archive.read('doc.kml'))
    ns={'k':'http://www.opengis.net/kml/2.2'}
    assert [e.text for e in kml.findall('.//k:Folder/k:name',ns)]==['Flight A','Hidden Flight']
    assert len(kml.findall('.//k:Placemark',ns))==3
    assert path.read_bytes()==original
    preview=build_preview([tmp_path],10,3)
    assert preview.scanned_workbooks==1 and len(preview.rows)==4
    assert next(r for r in preview.rows if r.photo_path.endswith('b.jpg')).source_row==5
    assert next(s for s in preview.schemas if s.source_sheet=='Flight A').header_row==3


def add_formula_cache(path, cache):
    # Excel stores cached results in <v>; openpyxl deliberately doesn't calculate formulas.
    with zipfile.ZipFile(path) as archive:
        entries={name:archive.read(name) for name in archive.namelist()}
    key='xl/worksheets/sheet1.xml'
    root=ET.fromstring(entries[key])
    ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    cell=root.find(".//s:c[@r='A2']",ns)
    assert cell.find('s:f',ns).text=='1500*2'
    cell.find('s:v',ns).text=str(cache)
    entries[key]=ET.tostring(root)
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,data in entries.items():
            archive.writestr(name,data)


def test_cached_formula_and_missing_cache_fail_without_replacing_output(tmp_path):
    path=workbook_file(tmp_path/'formula.xlsx',{'Flight':[['methane_concentration','relative_altitude'],['=1500*2',3]]})
    old=cleaned_csv_path(path,1000)
    old.write_bytes(b'previous successful output')
    result,=generate_methane_outputs([path],1000,False)
    assert result.cleaned_status=='failed'
    assert 'Flight' in result.cleaned_error and 'Recalculate and save' in result.cleaned_error
    assert old.read_bytes()==b'previous successful output'
    add_formula_cache(path,3000)
    result,=generate_methane_outputs([path],1000,False)
    assert result.cleaned_status=='success',result.cleaned_error
    book=load_workbook(result.cleaned_csv,data_only=False)
    assert book.active['A2'].value==3000 and book.active['A2'].data_type!='f'
    assert book.active['C2'].value==1000
    book.close()


@pytest.mark.parametrize('rows', [
    [['ppm','photo'],[1500,'a.jpg'],['ppm','photo'],[2000,'b.jpg']],
    [['ppm','photo','Photo'],[1500,'a.jpg','b.jpg']],
    [['ppm','ch4','relative_altitude'],[1500,1600,2]],
    [['methane_concentration','relative_altitude','PAC',' pac '],[1500,2,1,2]],
])
def test_ambiguous_sheet_fails(tmp_path,rows):
    path=workbook_file(tmp_path/'bad.xlsx',{'Ambiguous sheet':rows})
    result,=generate_methane_outputs([path],1000,False)
    assert result.cleaned_status=='failed' and 'Ambiguous sheet' in result.cleaned_error
    assert not cleaned_csv_path(path,1000).exists()


def test_explicit_headers_preferred_and_normalized():
    assert pick_column(['PPM',' Methane-Concentration '],PPM_COL_CANDIDATES)==' Methane-Concentration '
    assert pick_column(['AGL',' Relative Altitude '],REL_ALT_COL_CANDIDATES)==' Relative Altitude '


@pytest.mark.parametrize('across_files',[False,True])
def test_conflicting_photo_sources_fail_instead_of_last_wins(tmp_path,across_files):
    columns=['methane_concentration','relative_altitude','photo','latitude','longitude']
    path=workbook_file(tmp_path/'a.xlsx',{'Flight A':[columns,[1500,2,'a.jpg',28,-97]]})
    if across_files:
        paths=[path,csv_file(tmp_path/'b.csv',columns,[[1600,2,'a.jpg',28,-97]])]
    else:
        path=workbook_file(path,{'Flight A':[columns,[1500,2,'a.jpg',28,-97]],'Flight B':[columns,[1600,2,'a.jpg',28,-97]]})
        paths=[path]
    index=PurwayCSVIndex.from_csv_files(paths)
    assert not index.errors
    with pytest.raises(CorrelationError,match='Ambiguous'):
        index.match_photo(tmp_path/'a.jpg',3)


def test_scanner_exclusions_and_bad_workbook_isolated(tmp_path):
    for name in ('a.csv','b.xlsx','~$b.xlsx','._b.xlsx','b_Cleaned_1000-PPM.xlsx','a_Cleaned_1-PPM.csv','old.xls','macro.xlsm'):
        (tmp_path/name).touch()
    nested=tmp_path/'__MACOSX'
    nested.mkdir()
    (nested/'data.xlsx').touch()
    scan=scan_inputs([tmp_path,*tmp_path.iterdir()])
    assert [p.name for p in scan.tables]==['a.csv','b.xlsx']
    csv_file(tmp_path/'a.csv',['ppm','lat','lon','photo'],[[1500,28,-97,'a.jpg']])
    index=PurwayCSVIndex.from_csv_files(scan.tables)
    assert len(index.errors)==1 and len(index.records)==1


@pytest.mark.parametrize('suffix',['.csv','.xlsx'])
def test_failed_replace_and_cancel_preserve_previous_outputs(tmp_path,monkeypatch,suffix):
    from purway_geotagger.ops import table_export
    columns=['methane_concentration','relative_altitude']
    source=tmp_path/('a'+suffix)
    if suffix=='.csv':
        csv_file(source,columns,[[1500,3]])
    else:
        workbook_file(source,{'Data':[columns,[1500,3]]})
    destination=cleaned_csv_path(source,1000)
    destination.write_bytes(b'previous')
    original=source.read_bytes()
    tables=read_tables(source)
    def fail(*args):
        raise PermissionError('locked destination')
    with monkeypatch.context() as m:
        m.setattr(table_export.os,'replace',fail)
        result,=generate_methane_outputs([source],1000,False)
    assert result.cleaned_status=='failed'
    assert destination.read_bytes()==b'previous'
    calls=0
    def cancelled():
        nonlocal calls
        calls+=1
        return calls==2
    with pytest.raises(UserCancelledError):
        write_tables(destination,tables,cancelled)
    assert destination.read_bytes()==b'previous'
    assert source.read_bytes()==original
    assert not list(tmp_path.glob('.purway-*'))
    with pytest.raises(UserCancelledError):
        read_tables(source,lambda:True)


def test_workbook_without_data_is_skipped(tmp_path):
    path=workbook_file(tmp_path/'notes.xlsx',{'Notes':[['PAC'],[123]]})
    result,=generate_methane_outputs([path],1000,True)
    assert result.cleaned_status=='skipped' and result.cleaned_csv is None

@pytest.mark.parametrize('mode_name',['METHANE','COMBINED','ENCROACHMENT'])
def test_xlsx_pipeline_provenance_metadata_and_unfiltered_photos(tmp_path,mode_name):
    from purway_geotagger.core.job import Job, JobOptions
    from purway_geotagger.core.modes import RunMode
    from purway_geotagger.core.pipeline import run_job
    source_dir=tmp_path/'source'
    source_dir.mkdir()
    source=workbook_file(source_dir/'flight.xlsx',{'Flight':[
        ['Pilot notes'],
        ['methane_concentration','relative_altitude','latitude','longitude','dest_latitude','dest_longitude','distance','file_name'],
        [1500,.5,28,-97,28.1,-97.1,12,'calibration.jpg'],
        [1600,3,28,-97,28.1,-97.1,12,'flight.jpg'],
    ]})
    for photo in ('calibration.jpg','flight.jpg'):
        (source_dir/photo).write_bytes(b'fake photo for dry run')
    original=source.read_bytes()
    mode=getattr(RunMode,mode_name)
    opts=JobOptions(output_root=tmp_path/'run',overwrite_originals=True,create_backup_on_overwrite=True,
        flatten=False,cleanup_empty_dirs=False,sort_by_ppm=False,ppm_bin_edges=[0,1000],write_xmp=True,
        dry_run=True,max_join_delta_seconds=3,purway_payload='',enable_renaming=False,rename_template=None,
        start_index=1,run_mode=mode,methane_generate_kmz=True,output_photos_root=tmp_path/'copies')
    job=Job(id='xlsx-test',name='XLSX',inputs=[source_dir],options=opts)
    run_job(job,lambda *_:None,lambda:False)
    manifest=list(csv.DictReader((opts.output_root/'manifest.csv').open(encoding='utf-8')))
    assert all(r['status']=='SUCCESS' for r in manifest),manifest
    assert {r['source_sheet'] for r in manifest}=={'Flight'}
    assert {r['source_row'] for r in manifest}=={'3','4'}
    assert {r['pac'] for r in manifest}=={'3000.0','533.33'}
    assert job.state.scanned_workbooks==1
    summary=json.loads((opts.output_root/'run_summary.json').read_text())
    config=json.loads((opts.output_root/'run_config.json').read_text())
    assert config['options']['methane_exclude_calibration'] is True
    if mode_name=='ENCROACHMENT':
        assert summary['methane_outputs']==[]
        assert not cleaned_csv_path(source,1000).exists()
    else:
        out,=summary['methane_outputs']
        assert out['source_format']=='xlsx' and out['cleaned_rows']==1
        assert out['counts']['calibration_excluded']==1
        assert out['sheets'][0]['header_row']==2
    assert source.read_bytes()==original


def test_cancellation_keeps_completed_output_in_run_results(tmp_path):
    first=csv_file(tmp_path/'a.csv',['ppm','relative_altitude'],[[1500,2]])
    second=csv_file(tmp_path/'b.csv',['ppm','relative_altitude'],[[1500,2]])
    published=cleaned_csv_path(first,1000)
    results=[]
    with pytest.raises(UserCancelledError):
        generate_methane_outputs([first,second],1000,False,cancel_cb=published.exists,completed_results=results)
    assert len(results)==1 and results[0].cleaned_status=='success'
    assert published.exists() and not cleaned_csv_path(second,1000).exists()


def test_uncached_formula_on_unrelated_sheet_fails_whole_workbook(tmp_path):
    path=workbook_file(tmp_path/'flight.xlsx',{'Data':[['ppm','relative_altitude'],[1500,2]],'Notes':[['=1+1']]})
    index=PurwayCSVIndex.from_csv_files([path])
    assert not index.records and 'Notes' in index.errors[0]
    result,=generate_methane_outputs([path],1000,False)
    assert result.cleaned_status=='failed' and 'Notes' in result.cleaned_error


def test_csv_and_same_stem_workbook_have_separate_kmz(tmp_path):
    columns=['ppm','relative_altitude','lat','lon']
    source=csv_file(tmp_path/'flight.csv',columns,[[1500,2,28,-97]])
    workbook=workbook_file(tmp_path/'flight.xlsx',{'Data':[columns,[1600,2,28,-97]]})
    results=generate_methane_outputs([source,workbook],1000,True)
    assert all(r.kmz_status=='success' for r in results)
    assert len({r.kmz for r in results})==2


@pytest.mark.parametrize('altitude',['-inf','inf','NaN','','invalid'])
def test_unavailable_altitude_never_classified_as_calibration(tmp_path,altitude):
    path=csv_file(tmp_path/'input.csv',['ppm','relative_altitude'],[[1500,altitude]])
    result,=generate_methane_outputs([path],1000,False)
    assert result.cleaned_rows==1 and result.counts['calibration_excluded']==0
    assert result.counts['pac_unavailable']==1 and result.warnings

@pytest.mark.parametrize('saved_cache',[False,True])
def test_empty_string_formula_result_requires_actual_saved_cache(tmp_path,saved_cache):
    path=workbook_file(tmp_path/'blank.xlsx',{'Data':[['ppm','relative_altitude','PAC'],[1500,3,'=""']]})
    with zipfile.ZipFile(path) as archive:
        entries={name:archive.read(name) for name in archive.namelist()}
    key='xl/worksheets/sheet1.xml'
    root=ET.fromstring(entries[key])
    ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    cell=root.find(".//s:c[@r='C2']",ns)
    cell.set('t','str')
    if not saved_cache:
        cell.remove(cell.find('s:v',ns))
    entries[key]=ET.tostring(root)
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,data in entries.items():
            archive.writestr(name,data)
    result,=generate_methane_outputs([path],1000,False)
    assert result.cleaned_status==('success' if saved_cache else 'failed')
    if saved_cache:
        assert result.counts['pac_preserved']==1
        assert read_tables(result.cleaned_csv)[0].rows[1].values[2] is None


def test_explicit_relative_altitude_takes_precedence_in_full_reader(tmp_path):
    path=csv_file(tmp_path/'a.csv',['ppm','methane_concentration','relative_altitude','rel_alt','lat','lon'],[[1,1500,3,.5,28,-97]])
    index=PurwayCSVIndex.from_csv_files([path])
    assert not index.errors
    assert index.records[0].relative_altitude==3
    result,=generate_methane_outputs([path],1000,False)
    assert result.cleaned_status=='success' and result.counts['pac_calculated']==1


def test_workbook_xml_entities_are_rejected(tmp_path):
    path=workbook_file(tmp_path/'unsafe.xlsx',{'Data':[['ppm','relative_altitude'],[1500,2]]})
    with zipfile.ZipFile(path) as archive:
        entries={name:archive.read(name) for name in archive.namelist()}
    key='xl/worksheets/sheet1.xml'
    xml=entries[key].decode()
    xml='<!DOCTYPE worksheet [<!ENTITY sample "ppm">]>'+xml.replace('>ppm<','>&sample;<')
    entries[key]=xml.encode()
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,data in entries.items():
            archive.writestr(name,data)
    result,=generate_methane_outputs([path],1000,False)
    assert result.cleaned_status=='failed'
    assert 'invalid XML' in result.cleaned_error
    from defusedxml.common import EntitiesForbidden
    with pytest.raises(ValueError) as error:
        read_tables(path)
    assert isinstance(error.value.__cause__, EntitiesForbidden)
    assert not cleaned_csv_path(path,1000).exists()


def test_absolute_altitude_identifies_table_but_does_not_substitute_for_relative(tmp_path):
    path=workbook_file(tmp_path/'absolute.xlsx',{'Data':[['methane_concentration','altitude'],[1500,.5]]})
    result,=generate_methane_outputs([path],1000,False)
    assert result.cleaned_status=='success'
    assert result.cleaned_rows==1 and result.counts['calibration_excluded']==0
    assert result.counts['pac_unavailable']==1
