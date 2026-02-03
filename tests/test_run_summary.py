from __future__ import annotations

import json
from pathlib import Path

from purway_geotagger.core.run_summary import RunSummary, ExifSummary, MethaneOutputSummary, write_run_summary


def test_write_run_summary(tmp_path: Path) -> None:
    summary = RunSummary(
        run_id="abc",
        run_mode="methane",
        inputs=["/tmp/input"],
        settings={"methane_threshold": 1000, "methane_generate_kmz": False},
        exif=ExifSummary(total=2, success=2, failed=0),
        methane_outputs=[
            MethaneOutputSummary(
                source_csv="/tmp/methane.csv",
                cleaned_csv="/tmp/methane_Cleaned_1000-PPM.csv",
                cleaned_status="success",
                cleaned_rows=1,
                cleaned_error="",
                kmz=None,
                kmz_status="skipped",
                kmz_rows=0,
                kmz_error="",
            )
        ],
    )

    path = tmp_path / "run_summary.json"
    write_run_summary(path, summary)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["run_id"] == "abc"
    assert data["exif"]["success"] == 2
    assert data["methane_outputs"][0]["cleaned_status"] == "success"
