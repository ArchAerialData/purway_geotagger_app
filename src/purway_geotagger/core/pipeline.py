from __future__ import annotations

from pathlib import Path
from typing import Callable
import json
import time
from dataclasses import asdict, is_dataclass

from purway_geotagger.core.job import Job, JobOptions
from purway_geotagger.core.modes import RunMode, common_parent
from purway_geotagger.core.run_summary import RunSummary, ExifSummary, MethaneOutputSummary, write_run_summary
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
from purway_geotagger.ops.methane_outputs import generate_methane_outputs, MethaneCsvResult
from purway_geotagger.util.errors import UserCancelledError, CorrelationError, ExifToolError

ProgressCb = Callable[[int, str], None]  # percent, message
CancelCb = Callable[[], bool]  # returns True if cancelled

def run_job(job: Job, progress_cb: ProgressCb, cancel_cb: CancelCb) -> None:
    """Run a single job end-to-end (worker-thread safe).

    Outputs (must exist at end of run, even if failures occurred):
      - run_config.json
      - run_log.txt
      - manifest.csv
      - run_summary.json
    """
    opts = job.options
    run_folder = opts.output_root
    job.run_folder = run_folder
    run_folder.mkdir(parents=True, exist_ok=True)

    logger = RunLogger(run_folder / "run_log.txt")
    logger.log("Job started.")
    logger.log(f"Inputs: {[str(p) for p in job.inputs]}")
    _log_run_settings(logger, opts)

    _write_run_config(job, run_folder)

    scan: ScanResult = ScanResult(photos=[], csvs=[])
    tasks: list[PhotoTask] = []
    tasks_for_manifest: list[PhotoTask] = []
    methane_results: list[MethaneCsvResult] = []
    exif_summary = ExifSummary(total=0, success=0, failed=0)
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

        methane_failure_count = 0
        if opts.run_mode in (RunMode.METHANE, RunMode.COMBINED):
            job.state.stage = "METHANE_OUTPUTS"
            progress_cb(8, "Generating cleaned methane CSVs...")
            logger.log("Generating cleaned methane CSVs...")
            methane_results = generate_methane_outputs(
                csv_paths=scan.csvs,
                threshold=opts.methane_threshold,
                generate_kmz=opts.methane_generate_kmz,
            )
            methane_failure_count = _log_methane_results(
                logger,
                methane_results,
                opts.methane_generate_kmz,
            )

        if cancel_cb():
            raise UserCancelledError()

        overwrite = opts.overwrite_originals
        if opts.run_mode == RunMode.METHANE:
            overwrite = True
        elif opts.run_mode == RunMode.ENCROACHMENT:
            overwrite = False
        elif opts.run_mode == RunMode.COMBINED:
            overwrite = True

        job.state.stage = "COPY" if not overwrite else "PREPARE"
        progress_cb(10, "Preparing target photos...")
        logger.log("Preparing target photos (copy/backup as needed)...")
        copy_root = opts.output_photos_root if opts.run_mode == RunMode.ENCROACHMENT else None
        backup_root = run_folder / "BACKUPS"
        backup_rel_base = common_parent(job.inputs)
        target_map = ensure_target_photos(
            photos=scan.photos,
            run_folder=run_folder,
            overwrite=overwrite,
            create_backup_on_overwrite=opts.create_backup_on_overwrite,
            copy_root=copy_root,
            use_subdir=(copy_root is None),
            backup_root=backup_root,
            backup_rel_base=backup_rel_base,
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
                
                # Extended fields
                t.altitude = match.altitude
                t.relative_altitude = match.relative_altitude
                t.light_intensity = match.light_intensity
                t.uav_pitch = match.uav_pitch
                t.uav_roll = match.uav_roll
                t.uav_yaw = match.uav_yaw
                t.gimbal_pitch = match.gimbal_pitch
                t.gimbal_roll = match.gimbal_roll
                t.gimbal_yaw = match.gimbal_yaw
                t.camera_focal_length = match.camera_focal_length
                t.camera_zoom = match.camera_zoom
                t.timestamp_raw = match.timestamp_raw
                t.pac = match.pac

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
        try:
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
        except ExifToolError as exc:
            error_message = str(exc)
            logger.log(f"EXIF write failed: {error_message}")
            for t in tasks:
                if not t.matched or t.status == "FAILED":
                    continue
                t.status = "FAILED"
                t.reason = error_message
                job.state.failed += 1

        exif_summary = _summarize_exif(tasks)
        logger.log(f"EXIF injected: {exif_summary.success}/{exif_summary.total} photos.")

        if cancel_cb():
            raise UserCancelledError()

        post_tasks = tasks
        if opts.run_mode == RunMode.COMBINED:
            job.state.stage = "ENCROACHMENT_COPY"
            progress_cb(78, "Preparing encroachment copies...")
            logger.log("Preparing encroachment copies...")
            copy_root = opts.output_photos_root or opts.encroachment_output_base or run_folder
            copy_map = ensure_target_photos(
                photos=scan.photos,
                run_folder=run_folder,
                overwrite=False,
                create_backup_on_overwrite=False,
                copy_root=copy_root,
                use_subdir=False,
                backup_root=None,
                backup_rel_base=None,
            )
            post_tasks = _clone_tasks_for_copy(tasks, copy_map)

        tasks_for_manifest = post_tasks

        job.state.stage = "RENAME"
        progress_cb(82, "Renaming (if enabled)...")
        logger.log("Renaming (if enabled)...")
        maybe_rename(job, post_tasks)

        if cancel_cb():
            raise UserCancelledError()

        job.state.stage = "SORT"
        progress_cb(88, "Sorting by PPM (if enabled)...")
        logger.log("Sorting by PPM (if enabled)...")
        if opts.sort_by_ppm:
            sort_into_ppm_bins(job, post_tasks)

        if cancel_cb():
            raise UserCancelledError()

        job.state.stage = "FLATTEN"
        progress_cb(94, "Flattening/moving JPGs (if enabled)...")
        logger.log("Flattening/moving JPGs (if enabled)...")
        maybe_flatten(job, post_tasks)

        if not error_message and methane_failure_count:
            error_message = f"Methane outputs failed for {methane_failure_count} CSV(s)."

        if error_message:
            raise RuntimeError(error_message)

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
        manifest_tasks = tasks_for_manifest or tasks
        _write_manifest(
            run_folder,
            manifest_tasks,
            scan.photos,
            error_message if (cancelled or error_message) else "",
        )
        try:
            summary = _build_run_summary(job, exif_summary, methane_results)
            write_run_summary(run_folder / "run_summary.json", summary)
        except Exception as exc:  # pragma: no cover - do not crash on summary failures
            logger.log(f"Run summary failed: {exc}")

def _log_run_settings(logger: RunLogger, opts: JobOptions) -> None:
    mode = opts.run_mode.value if isinstance(opts.run_mode, RunMode) else "custom"
    logger.log(f"Run mode: {mode}")
    if opts.run_mode in (RunMode.METHANE, RunMode.COMBINED):
        logger.log(f"Methane threshold: {opts.methane_threshold}")
        logger.log(f"KMZ enabled: {'Yes' if opts.methane_generate_kmz else 'No'}")
    if opts.run_mode in (RunMode.ENCROACHMENT, RunMode.COMBINED):
        if opts.output_photos_root:
            logger.log(f"Encroachment output: {opts.output_photos_root}")
        if opts.enable_renaming:
            template_id = opts.rename_template.id if opts.rename_template else "manual"
            logger.log(f"Renaming: enabled ({template_id}), start_index={opts.start_index}")
        else:
            logger.log("Renaming: disabled")
    logger.log(f"Dry run: {'Yes' if opts.dry_run else 'No'}")


def _log_methane_results(
    logger: RunLogger,
    results: list[MethaneCsvResult],
    kmz_enabled: bool,
) -> int:
    if not results:
        logger.log("No methane CSVs found for cleaned outputs.")
        return 0

    cleaned_success = sum(1 for r in results if r.cleaned_status == "success")
    cleaned_failed = sum(1 for r in results if r.cleaned_status == "failed")
    cleaned_skipped = sum(1 for r in results if r.cleaned_status == "skipped")

    kmz_success = sum(1 for r in results if r.kmz_status == "success")
    kmz_failed = sum(1 for r in results if r.kmz_status == "failed")
    kmz_skipped = sum(1 for r in results if r.kmz_status == "skipped")

    logger.log(
        f"Cleaned CSVs: {cleaned_success} success, {cleaned_failed} failed, {cleaned_skipped} skipped."
    )
    if kmz_enabled:
        logger.log(
            f"KMZ outputs: {kmz_success} success, {kmz_failed} failed, {kmz_skipped} skipped."
        )
    else:
        logger.log("KMZ outputs: skipped (disabled).")

    for r in results:
        if r.cleaned_status == "failed":
            logger.log(f"Cleaned CSV failed for {r.source_csv}: {r.cleaned_error}")
        if r.kmz_status == "failed":
            logger.log(f"KMZ failed for {r.source_csv}: {r.kmz_error}")

    return cleaned_failed + kmz_failed


def _summarize_exif(tasks: list[PhotoTask]) -> ExifSummary:
    total = len(tasks)
    success = sum(1 for t in tasks if t.status == "SUCCESS")
    failed = total - success
    return ExifSummary(total=total, success=success, failed=failed)


def _clone_tasks_for_copy(
    source_tasks: list[PhotoTask],
    copy_map: dict[Path, Path],
) -> list[PhotoTask]:
    by_src = {t.src_path: t for t in source_tasks}
    clones: list[PhotoTask] = []
    for src, dest in copy_map.items():
        base = by_src.get(src)
        clone = PhotoTask(src_path=src, work_path=dest, output_path=dest)
        if base:
            clone.matched = base.matched
            clone.join_method = base.join_method
            clone.csv_path = base.csv_path
            clone.lat = base.lat
            clone.lon = base.lon
            clone.ppm = base.ppm
            clone.datetime_original = base.datetime_original
            clone.image_description = base.image_description
            clone.status = base.status
            clone.reason = base.reason
            clone.exif_written = base.exif_written
            
            # Extended fields
            clone.altitude = base.altitude
            clone.relative_altitude = base.relative_altitude
            clone.light_intensity = base.light_intensity
            clone.uav_pitch = base.uav_pitch
            clone.uav_roll = base.uav_roll
            clone.uav_yaw = base.uav_yaw
            clone.gimbal_pitch = base.gimbal_pitch
            clone.gimbal_roll = base.gimbal_roll
            clone.gimbal_yaw = base.gimbal_yaw
            clone.camera_focal_length = base.camera_focal_length
            clone.camera_zoom = base.camera_zoom
            clone.timestamp_raw = base.timestamp_raw
            clone.pac = base.pac
        clones.append(clone)
    return clones


def _build_run_summary(
    job: Job,
    exif_summary: ExifSummary,
    methane_results: list[MethaneCsvResult],
) -> RunSummary:
    outputs: list[MethaneOutputSummary] = []
    for r in methane_results:
        outputs.append(MethaneOutputSummary(
            source_csv=str(r.source_csv),
            cleaned_csv=str(r.cleaned_csv) if r.cleaned_csv else None,
            cleaned_status=r.cleaned_status,
            cleaned_rows=r.cleaned_rows,
            cleaned_error=r.cleaned_error,
            kmz=str(r.kmz) if r.kmz else None,
            kmz_status=r.kmz_status,
            kmz_rows=r.kmz_rows,
            kmz_error=r.kmz_error,
        ))

    opts = job.options
    mode = opts.run_mode.value if isinstance(opts.run_mode, RunMode) else None
    settings = {
        "methane_threshold": opts.methane_threshold,
        "methane_generate_kmz": opts.methane_generate_kmz,
        "enable_renaming": opts.enable_renaming,
        "start_index": opts.start_index,
        "dry_run": opts.dry_run,
        "overwrite_originals": opts.overwrite_originals,
        "output_photos_root": str(opts.output_photos_root) if opts.output_photos_root else None,
        "encroachment_output_base": str(opts.encroachment_output_base) if opts.encroachment_output_base else None,
    }

    return RunSummary(
        run_id=job.id,
        run_mode=mode,
        inputs=[str(p) for p in job.inputs],
        settings=settings,
        exif=exif_summary,
        methane_outputs=outputs,
    )

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
                # Extended fields
                altitude="" if t.altitude is None else str(t.altitude),
                relative_altitude="" if t.relative_altitude is None else str(t.relative_altitude),
                light_intensity="" if t.light_intensity is None else str(t.light_intensity),
                pac="" if t.pac is None else str(t.pac),
                uav_pitch="" if t.uav_pitch is None else str(t.uav_pitch),
                uav_roll="" if t.uav_roll is None else str(t.uav_roll),
                uav_yaw="" if t.uav_yaw is None else str(t.uav_yaw),
                gimbal_pitch="" if t.gimbal_pitch is None else str(t.gimbal_pitch),
                gimbal_roll="" if t.gimbal_roll is None else str(t.gimbal_roll),
                gimbal_yaw="" if t.gimbal_yaw is None else str(t.gimbal_yaw),
                camera_focal_length="" if t.camera_focal_length is None else str(t.camera_focal_length),
                camera_zoom="" if t.camera_zoom is None else str(t.camera_zoom),
                capture_time=t.timestamp_raw or "",
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
