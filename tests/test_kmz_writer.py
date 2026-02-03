from __future__ import annotations

from pathlib import Path
import csv
import zipfile
import xml.etree.ElementTree as ET

from purway_geotagger.ops.methane_outputs import generate_methane_outputs, kmz_path_for_cleaned, cleaned_csv_path


def _write_csv(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["latitude", "longitude", "ppm"])
        writer.writerow(["1.0", "2.0", "1200"])
        writer.writerow(["3.0", "4.0", "1500"])


def test_kmz_generation_from_cleaned_csv(tmp_path: Path) -> None:
    src = tmp_path / "methane.csv"
    _write_csv(src)

    results = generate_methane_outputs([src], threshold=1000, generate_kmz=True)
    res = results[0]
    assert res.kmz_status == "success"
    cleaned = cleaned_csv_path(src, 1000)
    kmz_path = kmz_path_for_cleaned(cleaned)
    assert kmz_path.exists()

    with zipfile.ZipFile(kmz_path, "r") as zf:
        kml_bytes = zf.read("doc.kml")
    root = ET.fromstring(kml_bytes)
    ns = {"k": "http://www.opengis.net/kml/2.2"}
    placemarks = root.findall(".//k:Placemark", ns)
    assert len(placemarks) == 2
    names = [pm.find("k:name", ns).text for pm in placemarks]
    assert "1200" in names
    assert "1500" in names
