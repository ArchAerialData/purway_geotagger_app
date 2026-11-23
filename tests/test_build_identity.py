import json
import sys
from purway_geotagger.core.build_identity import build_identity


def test_development_does_not_claim_packaged_identity(monkeypatch):
    monkeypatch.setattr(sys, 'frozen', False, raising=False)
    assert 'development' in build_identity()[0]


def test_frozen_identity_and_local_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path), raising=False)
    info=dict(app_version='6.2.0',build_id='20261123-1200-abcdef12',git_revision='1234567',
              source_modified=True,built_at_utc='2026-11-23T12:00:00Z',input_fingerprint='abcdef12')
    (tmp_path/'build-info.json').write_text(json.dumps(info),encoding='utf-8-sig')
    label,details=build_identity()
    assert label=='v6.2.0 · 20261123-1200-abcdef12'
    assert '1234567 + local changes' in details
    assert '2026-11-23T12:00:00Z' in details


def test_missing_or_invalid_metadata_is_explicit(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path), raising=False)
    assert 'build unknown' in build_identity()[0]
    (tmp_path/'build-info.json').write_text('{}',encoding='utf-8')
    assert 'build unknown' in build_identity()[0]
