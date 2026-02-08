from __future__ import annotations

from pathlib import Path

from purway_geotagger.core.preview import build_preview


def test_build_preview_rows_and_schema(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    jpg = input_dir / "IMG_0001.jpg"
    jpg.write_text("x", encoding="utf-8")
    csv_path = input_dir / "data.csv"
    with csv_path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(
            "Latitude,Longitude,PPM,Photo\n"
            "1.0,2.0,10,IMG_0001.jpg\n",
        )

    result = build_preview([input_dir], max_rows=5, max_join_delta_seconds=3)
    assert result.scanned_photos == 1
    assert result.scanned_csvs == 1
    assert len(result.rows) == 1
    assert result.rows[0].status == "MATCHED"
    assert len(result.schemas) == 1
    schema = result.schemas[0]
    assert schema.photo_col is not None
