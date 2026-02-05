from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import os
import shutil
import subprocess
import sys
from typing import Callable

from purway_geotagger.core.photo_task import PhotoTask
from purway_geotagger.util.errors import ExifToolError, UserCancelledError
from purway_geotagger.core.utils import resource_path

@dataclass
class ExifWriteResult:
    success: bool
    error: str = ""

class ExifToolWriter:
    def __init__(self, write_xmp: bool, dry_run: bool) -> None:
        self.write_xmp = write_xmp
        self.dry_run = dry_run
        self.exiftool_path = _resolve_exiftool_path()

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

        files = [str(t.output_path.expanduser().resolve()) for t in matched]
        
        # Get path to ExifTool config for custom XMP namespace
        config_path = resource_path("config/exiftool_config.txt")
        config_args = []
        if config_path and config_path.exists():
            config_args = [f"-config", str(config_path)]
        
        cmd = [
            self.exiftool_path,
            *config_args,
            "-overwrite_original",
            f"-csv={import_csv}",
            *files,
        ]

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as e:
            raise ExifToolError(_exiftool_missing_message()) from e

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
            "GPSAltitude",
            "DateTimeOriginal",
            "ImageDescription",
        ]
        
        # Custom XMP-ArchAerial fields
        xmp_extended_fields = [
            "XMP-ArchAerial:MethaneConcentration",
            "XMP-ArchAerial:PAC",
            "XMP-ArchAerial:RelativeAltitude",
            "XMP-ArchAerial:LightIntensity",
            "XMP-ArchAerial:UAVPitch",
            "XMP-ArchAerial:UAVRoll",
            "XMP-ArchAerial:UAVYaw",
            "XMP-ArchAerial:GimbalPitch",
            "XMP-ArchAerial:GimbalRoll",
            "XMP-ArchAerial:GimbalYaw",
            "XMP-ArchAerial:CaptureTime",
            "XMP-ArchAerial:CameraFocalLength",
            "XMP-ArchAerial:CameraZoom",
        ]
        fields += xmp_extended_fields
        
        if self.write_xmp:
            fields += ["XMP:GPSLatitude", "XMP:GPSLongitude", "XMP:Description"]

        def _val(v) -> str:
            """Convert value to string, returning empty string for None."""
            return "" if v is None else str(v)

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
                    "GPSAltitude": _val(t.altitude),
                    "DateTimeOriginal": t.datetime_original or "",
                    "ImageDescription": t.image_description,
                    # Custom XMP-ArchAerial fields
                    "XMP-ArchAerial:MethaneConcentration": _val(t.ppm),
                    "XMP-ArchAerial:PAC": _val(t.pac),
                    "XMP-ArchAerial:RelativeAltitude": _val(t.relative_altitude),
                    "XMP-ArchAerial:LightIntensity": _val(t.light_intensity),
                    "XMP-ArchAerial:UAVPitch": _val(t.uav_pitch),
                    "XMP-ArchAerial:UAVRoll": _val(t.uav_roll),
                    "XMP-ArchAerial:UAVYaw": _val(t.uav_yaw),
                    "XMP-ArchAerial:GimbalPitch": _val(t.gimbal_pitch),
                    "XMP-ArchAerial:GimbalRoll": _val(t.gimbal_roll),
                    "XMP-ArchAerial:GimbalYaw": _val(t.gimbal_yaw),
                    "XMP-ArchAerial:CaptureTime": _val(t.timestamp_raw),
                    "XMP-ArchAerial:CameraFocalLength": _val(t.camera_focal_length),
                    "XMP-ArchAerial:CameraZoom": _val(t.camera_zoom),
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
            self.exiftool_path,
            "-csv",
            "-GPSLatitude",
            "-GPSLongitude",
            "-GPSLatitudeRef",
            "-GPSLongitudeRef",
            *files,
        ]

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as e:
            raise ExifToolError(_exiftool_missing_message()) from e

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


def _resolve_exiftool_path() -> str:
    """Resolve an ExifTool executable path.

    Resolution order:
    1) PURWAY_EXIFTOOL_PATH env var (explicit override)
    2) Bundled binary next to the app executable (PyInstaller onedir/.app)
    3) PATH lookup
    4) Common macOS locations
    5) Fallback: "exiftool" (may still fail at runtime with a friendly error)
    """
    env_path = os.environ.get("PURWAY_EXIFTOOL_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return str(p)

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        bundled = exe_dir / "bin" / "exiftool"
        if bundled.exists():
            return str(bundled)

    which = shutil.which("exiftool")
    if which:
        return which

    for cand in ("/opt/homebrew/bin/exiftool", "/usr/local/bin/exiftool", "/usr/bin/exiftool"):
        if Path(cand).exists():
            return cand

    return "exiftool"


def _exiftool_missing_message() -> str:
    return (
        "ExifTool not found. Install ExifTool or set PURWAY_EXIFTOOL_PATH, "
        "or use a bundled ExifTool in the packaged app."
    )


def is_exiftool_available() -> bool:
    path = _resolve_exiftool_path()
    if path == "exiftool":
        return shutil.which("exiftool") is not None
    return Path(path).exists()
