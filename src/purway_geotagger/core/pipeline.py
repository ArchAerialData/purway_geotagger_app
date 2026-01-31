from __future__ import annotations

from pathlib import Path
from typing import Callable
import json
import time
from dataclasses import asdict, is_dataclass

from purway_geotagger.core.job import Job
from purway_geotagger.core.scanner import scan_inputs, ScanResult
from purway_geotagger.core.photo_task import PhotoTask
from purway_geotagger.core.manifest import ManifestRow, ManifestWriter
from purway_geotagger.core.run_logger import RunLogger
from purway_geotagger.parsers.purway_csv import PurwayCSVIndex
from purway_geotagger.exif.exiftool_writer import ExifToolWriter
from purway_geotagger.ops.copier import ensure_target_photos
from purway_geotagger.ops.sorter import sort_into_ppm_bins
from purway_geotagger.ops.renamer import maybe_rename
from purway_geotagger.ops.flattener import maybe_flatten
from purway_geotagger.util.errors import UserCancelledError, CorrelationError

ProgressCb = Callable[[int, str], None]  # percent, message
CancelCb = Callable[[], bool]  # returns True if cancelled

def run_job(job: Job, progress_cb: ProgressCb, cancel_cb: CancelCb) -> None:
    """Run a single job end-to-end (worker-thread safe).

    Outputs (must exist at end of run, even if failures occurred):
      - run_config.json
      - run_log.txt
      - manifest.csv
    """
    opts = job.options
    run_folder = opts.output_root
    job.run_folder = run_folder
    run_folder.mkdir(parents=True, exist_ok=True)

    logger = RunLogger(run_folder / "run_log.txt")
    logger.log("Job started.")
    logger.log(f"Inputs: {[str(p) for p in job.inputs]}")

    _write_run_config(job, run_folder)

    scan: ScanResult = ScanResult(photos=[], csvs=[])
    tasks: list[PhotoTask] = []
    error_message = ""
    cancelled = False

    try:
        job.state.stage = "SCAN"
        progress_cb(0, "Scanning inputs...")
        scan = scan_inputs(job.inputs)
        job.state.scanned_photos = len(scan.photos)
        job.state.scanned_csvs = len(scan.csvs)
        logger.log(f"Scanned photos: {job.state.scanned_photos}, CSVs: {job.state.scanned_csvs}")

        if cancel_cb():
            raise UserCancelledError()

        job.state.stage = "PARSE"
        progress_cb(5, "Parsing CSV files...")
        logger.log("Parsing CSV files...")
        csv_index = PurwayCSVIndex.from_csv_files(scan.csvs)

        if cancel_cb():
            raise UserCancelledError()

        job.state.stage = "COPY" if not opts.overwrite_originals else "PREPARE"
        progress_cb(10, "Preparing target photos...")
        logger.log("Preparing target photos (copy/backup as needed)...")
        target_map = ensure_target_photos(
            photos=scan.photos,
            run_folder=run_folder,
            overwrite=opts.overwrite_originals,
            create_backup_on_overwrite=opts.create_backup_on_overwrite,
        )

        tasks = [
            PhotoTask(src_path=src, work_path=tgt, output_path=tgt)
            for src, tgt in target_map.items()
        ]

        if cancel_cb():
            raise UserCancelledError()

        job.state.stage = "MATCH"
        progress_cb(20, "Matching photos to CSV rows...")
        logger.log("Matching photos to CSV rows...")
        last_update = time.monotonic()
        for i, t in enumerate(tasks):
            if cancel_cb():
                raise UserCancelledError()

            try:
                match = csv_index.match_photo(
                    photo_path=t.src_path,
                    max_join_delta_seconds=opts.max_join_delta_seconds,
                )
                t.matched = True
                t.join_method = match.join_method
                t.csv_path = match.csv_path
                t.lat = match.lat
                t.lon = match.lon
                t.ppm = match.ppm
                t.datetime_original = match.datetime_original
                t.image_description = match.image_description
                if opts.purway_payload:
                    if t.image_description:
                        t.image_description = f"{t.image_description}; purway_payload={opts.purway_payload}"
                    else:
                        t.image_description = f"purway_payload={opts.purway_payload}"
                job.state.matched += 1
            except CorrelationError as e:
                t.status = "FAILED"
                t.reason = str(e)
                job.state.failed += 1

            now = time.monotonic()
            if i % 25 == 0 or (now - last_update) >= 1.0:
                pct = 20 + int(30 * (i / max(1, len(tasks))))
                progress_cb(pct, f"Matched {i}/{len(tasks)} photos...")
                last_update = now

        if cancel_cb():
            raise UserCancelledError()

        job.state.stage = "WRITE"
        progress_cb(55, "Writing EXIF/XMP via ExifTool...")
        logger.log("Writing EXIF/XMP via ExifTool...")
        writer = ExifToolWriter(write_xmp=opts.write_xmp, dry_run=opts.dry_run)
        results = writer.write_tasks(
            tasks=tasks,
            work_dir=run_folder,
            progress_cb=lambda done, total: progress_cb(
                55 + int(25 * (done / max(1, total))),
                f"Writing metadata {done}/{total}..."
            ),
            cancel_cb=cancel_cb,
        )

        for t in tasks:
            if t.status == "FAILED" or not t.matched:
                continue
            res = results.get(t.output_path)
            if res and res.success:
                t.status = "SUCCESS"
                t.exif_written = (not opts.dry_run)
                job.state.success += 1
            else:
                t.status = "FAILED"
                t.reason = (res.error if res else "unknown exiftool error")
                job.state.failed += 1

        if cancel_cb():
            raise UserCancelledError()

        job.state.stage = "RENAME"
        progress_cb(82, "Renaming (if enabled)...")
        logger.log("Renaming (if enabled)...")
        maybe_rename(job, tasks)

        if cancel_cb():
            raise UserCancelledError()

        job.state.stage = "SORT"
        progress_cb(88, "Sorting by PPM (if enabled)...")
        logger.log("Sorting by PPM (if enabled)...")
        if opts.sort_by_ppm:
            sort_into_ppm_bins(job, tasks)

        if cancel_cb():
            raise UserCancelledError()

        job.state.stage = "FLATTEN"
        progress_cb(94, "Flattening/moving JPGs (if enabled)...")
        logger.log("Flattening/moving JPGs (if enabled)...")
        maybe_flatten(job, tasks)

        job.state.stage = "DONE"
        logger.log("Job finished.")
        progress_cb(100, "Done.")
    except UserCancelledError:
        cancelled = True
        error_message = "Cancelled by user."
        logger.log(error_message)
        raise
    except Exception as e:
        error_message = str(e)
        logger.log(f"Job failed: {error_message}")
        raise
    finally:
        logger.log("Writing manifest...")
        _write_manifest(run_folder, tasks, scan.photos, error_message if (cancelled or error_message) else "")

def _write_run_config(job: Job, run_folder: Path) -> None:
    path = run_folder / "run_config.json"
    payload = {
        "job": {
            "id": job.id,
            "name": job.name,
            "inputs": [str(p) for p in job.inputs],
        },
        "options": _jsonify(asdict(job.options)),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

def _jsonify(obj):
    """Recursively convert dataclass/asdict output into JSON-safe types."""
    if isinstance(obj, dict):
        return {k: _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_jsonify(v) for v in obj]
    if isinstance(obj, Path):
        return str(obj)
    return obj

def _write_manifest(
    run_folder: Path,
    tasks: list[PhotoTask],
    scanned_photos: list[Path],
    default_reason: str,
) -> None:
    """Write manifest.csv for all discovered photos.

    Ensures a manifest is written even if the job failed or was cancelled.
    """
    manifest = ManifestWriter(run_folder / "manifest.csv")

    if tasks:
        for t in tasks:
            status = t.status
            if status == "PENDING":
                status = "FAILED" if default_reason else ("FAILED" if not t.matched else "PENDING")
            reason = t.reason or default_reason
            manifest.add(ManifestRow(
                source_path=str(t.src_path),
                output_path=str(t.output_path),
                status=status,
                reason=reason,
                lat="" if t.lat is None else str(t.lat),
                lon="" if t.lon is None else str(t.lon),
                ppm="" if t.ppm is None else str(t.ppm),
                csv_path=t.csv_path,
                join_method=t.join_method,
                exif_written="YES" if t.exif_written else "NO",
            ))
    else:
        for p in scanned_photos:
            manifest.add(ManifestRow(
                source_path=str(p),
                output_path="",
                status="FAILED" if default_reason else "PENDING",
                reason=default_reason,
                lat="",
                lon="",
                ppm="",
                csv_path="",
                join_method="NONE",
                exif_written="NO",
            ))

    manifest.write()
