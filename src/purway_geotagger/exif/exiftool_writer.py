from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import subprocess
from typing import Callable

from purway_geotagger.core.photo_task import PhotoTask
from purway_geotagger.util.errors import ExifToolError, UserCancelledError

@dataclass
class ExifWriteResult:
    success: bool
    error: str = ""

class ExifToolWriter:
    def __init__(self, write_xmp: bool, dry_run: bool) -> None:
        self.write_xmp = write_xmp
        self.dry_run = dry_run

    def write_tasks(
        self,
        tasks: list[PhotoTask],
        work_dir: Path,
        progress_cb: Callable[[int, int], None],
        cancel_cb: Callable[[], bool],
    ) -> dict[Path, ExifWriteResult]:
        """Write EXIF/XMP for all matched tasks.

        Contract:
        - Only tasks with task.matched == True are written.
        - ExifTool import CSV uses SourceFile=absolute path to task.output_path.
        - Returns mapping: output_path (at write time) -> result.

        NOTE: ExifTool CSV import does not yield strong per-file status.
        Production SHOULD verify tags after writing and set results accordingly.
        """
        matched = [t for t in tasks if t.matched and t.status not in ("FAILED", "SKIPPED")]
        results: dict[Path, ExifWriteResult] = {}

        if not matched:
            return results

        if self.dry_run:
            for t in matched:
                results[t.output_path] = ExifWriteResult(success=True)
            return results

        import_csv = work_dir / "_exiftool_import.csv"
        self._write_import_csv(import_csv, matched)

        cmd = [
            "exiftool",
            "-overwrite_original",
            f"-csv={import_csv}",
        ]

        proc = subprocess.run(
            cmd,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
        )

        if proc.returncode != 0:
            raise ExifToolError(proc.stderr.strip() or "ExifTool returned non-zero exit code.")

        results = self._verify_written(matched, work_dir)
        for i, t in enumerate(matched, start=1):
            if cancel_cb():
                raise UserCancelledError()
            # Ensure every task has a result entry.
            results.setdefault(t.output_path, ExifWriteResult(success=False, error="verification missing result"))
            progress_cb(i, len(matched))

        return results

    def _write_import_csv(self, path: Path, tasks: list[PhotoTask]) -> None:
        fields = [
            "SourceFile",
            "GPSLatitude",
            "GPSLongitude",
            "GPSLatitudeRef",
            "GPSLongitudeRef",
            "DateTimeOriginal",
            "ImageDescription",
        ]
        if self.write_xmp:
            fields += ["XMP:GPSLatitude", "XMP:GPSLongitude", "XMP:Description"]

        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for t in tasks:
                # Use absolute paths to support overwrite-originals mode (files may be outside run folder).
                src = str(t.output_path.expanduser().resolve())
                row = {
                    "SourceFile": src,
                    "GPSLatitude": t.lat,
                    "GPSLongitude": t.lon,
                    "GPSLatitudeRef": _gps_lat_ref(t.lat),
                    "GPSLongitudeRef": _gps_lon_ref(t.lon),
                    "DateTimeOriginal": t.datetime_original or "",
                    "ImageDescription": t.image_description,
                }
                if self.write_xmp:
                    row["XMP:GPSLatitude"] = t.lat
                    row["XMP:GPSLongitude"] = t.lon
                    row["XMP:Description"] = t.image_description
                w.writerow(row)

    def _verify_written(self, tasks: list[PhotoTask], work_dir: Path) -> dict[Path, ExifWriteResult]:
        """Verify that required GPS tags exist after writing.

        Uses ExifTool to read back GPSLatitude/GPSLongitude/GPSLatitudeRef/GPSLongitudeRef.
        """
        files = [str(t.output_path.expanduser().resolve()) for t in tasks]
        cmd = [
            "exiftool",
            "-csv",
            "-GPSLatitude",
            "-GPSLongitude",
            "-GPSLatitudeRef",
            "-GPSLongitudeRef",
            *files,
        ]

        proc = subprocess.run(
            cmd,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
        )

        if proc.returncode != 0:
            raise ExifToolError(proc.stderr.strip() or "ExifTool verification failed.")

        out = (proc.stdout or "").strip()
        if not out:
            raise ExifToolError("ExifTool verification returned no output.")

        rows = list(csv.DictReader(out.splitlines()))
        if not rows:
            raise ExifToolError("ExifTool verification produced no rows.")

        by_file: dict[Path, dict[str, str]] = {}
        for r in rows:
            src = r.get("SourceFile")
            if not src:
                continue
            by_file[Path(src).expanduser().resolve()] = r

        results: dict[Path, ExifWriteResult] = {}
        for t in tasks:
            src = t.output_path.expanduser().resolve()
            r = by_file.get(src)
            if not r:
                results[t.output_path] = ExifWriteResult(False, "verification missing SourceFile")
                continue

            lat = (r.get("GPSLatitude") or "").strip()
            lon = (r.get("GPSLongitude") or "").strip()
            lat_ref = (r.get("GPSLatitudeRef") or "").strip()
            lon_ref = (r.get("GPSLongitudeRef") or "").strip()

            if lat and lon and lat_ref and lon_ref:
                results[t.output_path] = ExifWriteResult(True)
            else:
                results[t.output_path] = ExifWriteResult(False, "verification missing GPS tags")

        return results


def _gps_lat_ref(lat: float | None) -> str:
    if lat is None:
        return ""
    return "N" if lat >= 0 else "S"


def _gps_lon_ref(lon: float | None) -> str:
    if lon is None:
        return ""
    return "E" if lon >= 0 else "W"
