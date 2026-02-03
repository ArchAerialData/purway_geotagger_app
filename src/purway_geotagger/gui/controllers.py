from __future__ import annotations

import uuid
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QProgressBar

from purway_geotagger.core.settings import AppSettings
from purway_geotagger.core.job import Job, JobOptions
from purway_geotagger.core.modes import RunMode, encroachment_run_base
from purway_geotagger.gui.workers import JobWorker
from purway_geotagger.gui.mode_state import ModeState
from purway_geotagger.templates.template_manager import TemplateManager
from purway_geotagger.templates.models import RenameTemplate
from purway_geotagger.util.platform import open_in_finder

class JobController(QObject):
    jobs_changed = Signal()

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.settings = settings
        self.inputs: list[Path] = []
        self.jobs: list[Job] = []
        self.template_manager = TemplateManager()
        self._workers: dict[str, JobWorker] = {}
        self._queue: list[Job] = []
        self._active_job_id: str | None = None
        self._progress_bars: dict[str, QProgressBar] = {}

    def add_inputs(self, paths: list[Path]) -> None:
        for p in paths:
            if p not in self.inputs:
                self.inputs.append(p)
        self.jobs_changed.emit()

    def suggest_template_id(self, paths: list[Path]) -> str | None:
        if not paths:
            return None
        text = " ".join(str(p).lower() for p in paths)
        for t in self.template_manager.list_templates():
            if t.id.lower() in text or t.name.lower() in text or t.client.lower() in text:
                return t.id
        return None

    def clear_inputs(self) -> None:
        self.inputs = []
        self.jobs_changed.emit()

    def start_job(
        self,
        output_root: Path,
        overwrite_originals: bool,
        flatten: bool,
        cleanup_empty_dirs: bool,
        sort_by_ppm: bool,
        dry_run: bool,
        write_xmp: bool,
        enable_renaming: bool,
        rename_template_id: str | None,
        start_index: int,
        purway_payload: str,
        progress_bar: QProgressBar,
        inputs_override: list[Path] | None = None,
    ) -> Job:
        # Create run folder immediately
        run_folder = AppSettings.new_run_folder(output_root)

        rename_template = self.template_manager.templates.get(rename_template_id) if rename_template_id else None

        opts = JobOptions(
            output_root=run_folder,
            overwrite_originals=overwrite_originals,
            create_backup_on_overwrite=self.settings.create_backup_on_overwrite,
            flatten=flatten,
            cleanup_empty_dirs=cleanup_empty_dirs,
            sort_by_ppm=sort_by_ppm,
            ppm_bin_edges=self.settings.ppm_bin_edges,
            write_xmp=write_xmp,
            dry_run=dry_run,
            max_join_delta_seconds=self.settings.max_join_delta_seconds,
            purway_payload=purway_payload,
            enable_renaming=enable_renaming,
            rename_template=rename_template,
            start_index=start_index,
        )

        inputs = inputs_override if inputs_override is not None else self.inputs.copy()
        return self._enqueue_job(opts, inputs, progress_bar)

    def start_job_from_mode_state(self, state: ModeState, progress_bar: QProgressBar) -> Job | None:
        if not state.inputs:
            return None
        opts = self.build_job_options_from_mode_state(state)
        return self._enqueue_job(opts, state.inputs.copy(), progress_bar)

    def _enqueue_job(self, options: JobOptions, inputs: list[Path], progress_bar: QProgressBar) -> Job:
        job = Job(
            id=str(uuid.uuid4()),
            name=f"Job {len(self.jobs)+1}",
            inputs=inputs,
            options=options,
        )
        job.run_folder = options.output_root
        self.jobs.append(job)
        self._progress_bars[job.id] = progress_bar
        self.jobs_changed.emit()

        if self._active_job_id is None:
            self._start_worker(job)
        else:
            job.state.stage = "QUEUED"
            job.state.message = "Queued"
            self._queue.append(job)
            self.jobs_changed.emit()
        return job

    def build_job_options_from_mode_state(self, state: ModeState) -> JobOptions:
        resolved = state.resolved()
        output_photos_root: Path | None = None
        if state.mode == RunMode.METHANE:
            output_base = resolved.methane_log_base
        elif state.mode == RunMode.ENCROACHMENT:
            output_photos_root = resolved.encroachment_output_base
            output_base = encroachment_run_base(output_photos_root) if output_photos_root else None
        else:
            output_photos_root = resolved.encroachment_output_base
            output_base = encroachment_run_base(output_photos_root) if output_photos_root else None
        output_base = output_base or Path.home()
        run_folder = AppSettings.new_run_folder(output_base)

        rename_template = None
        if state.encroachment_template_id:
            rename_template = self.template_manager.templates.get(state.encroachment_template_id)
        elif state.encroachment_rename_enabled and state.encroachment_client_abbr.strip():
            rename_template = RenameTemplate(
                id="manual",
                name="Manual",
                client=state.encroachment_client_abbr.strip(),
                pattern="{client}_{index:04d}",
                description="Manual client abbreviation",
                start_index=max(1, int(state.encroachment_start_index)),
            )

        overwrite_originals = self.settings.overwrite_originals_default
        flatten = self.settings.flatten_default
        cleanup_empty_dirs = self.settings.cleanup_empty_dirs_default
        sort_by_ppm = self.settings.sort_by_ppm_default
        enable_renaming = state.encroachment_rename_enabled

        if state.mode == RunMode.METHANE:
            overwrite_originals = True
            flatten = False
            cleanup_empty_dirs = False
            sort_by_ppm = False
            enable_renaming = False
        elif state.mode == RunMode.ENCROACHMENT:
            overwrite_originals = False
            flatten = False
            cleanup_empty_dirs = False
            sort_by_ppm = False
        elif state.mode == RunMode.COMBINED:
            overwrite_originals = True
            flatten = False
            cleanup_empty_dirs = False
            sort_by_ppm = False

        return JobOptions(
            output_root=run_folder,
            overwrite_originals=overwrite_originals,
            create_backup_on_overwrite=self.settings.create_backup_on_overwrite,
            flatten=flatten,
            cleanup_empty_dirs=cleanup_empty_dirs,
            sort_by_ppm=sort_by_ppm,
            ppm_bin_edges=self.settings.ppm_bin_edges,
            write_xmp=self.settings.write_xmp_default,
            dry_run=self.settings.dry_run_default,
            max_join_delta_seconds=self.settings.max_join_delta_seconds,
            purway_payload="",
            enable_renaming=enable_renaming,
            rename_template=rename_template,
            start_index=max(1, int(state.encroachment_start_index)),
            run_mode=state.mode,
            methane_threshold=state.methane_threshold,
            methane_generate_kmz=state.methane_generate_kmz,
            methane_log_base=resolved.methane_log_base,
            encroachment_output_base=resolved.encroachment_output_base,
            output_photos_root=output_photos_root,
        )

    def cancel_job(self, job: Job) -> None:
        if job.id in self._workers:
            w = self._workers.get(job.id)
            if w:
                w.cancel()
            return
        if job in self._queue:
            self._queue.remove(job)
            job.state.stage = "CANCELLED"
            job.state.message = "Cancelled before start."
            self.jobs_changed.emit()

    def open_output_folder(self, job: Job) -> None:
        if job.run_folder:
            open_in_finder(job.run_folder)

    def export_manifest_path(self, job: Job) -> Path | None:
        if not job.run_folder:
            return None
        p = job.run_folder / "manifest.csv"
        return p if p.exists() else None

    def rerun_failed_only(self, job: Job, progress_bar: QProgressBar) -> Job | None:
        manifest_path = self.export_manifest_path(job)
        if not manifest_path:
            return None
        failed_paths = _failed_paths_from_manifest(manifest_path)
        if not failed_paths:
            return None
        output_root = job.run_folder.parent if job.run_folder else Path.home()
        opts = job.options
        return self.start_job(
            output_root=output_root,
            overwrite_originals=opts.overwrite_originals,
            flatten=opts.flatten,
            cleanup_empty_dirs=opts.cleanup_empty_dirs,
            sort_by_ppm=opts.sort_by_ppm,
            dry_run=opts.dry_run,
            write_xmp=opts.write_xmp,
            enable_renaming=opts.enable_renaming,
            rename_template_id=opts.rename_template.id if opts.rename_template else None,
            start_index=opts.start_index,
            purway_payload=opts.purway_payload,
            progress_bar=progress_bar,
            inputs_override=failed_paths,
        )

    def _on_progress(self, job: Job, pct: int, msg: str, bar: QProgressBar) -> None:
        job.state.progress = pct
        job.state.message = msg
        if bar:
            bar.setValue(pct)
            bar.setFormat(f"{pct}% — {msg}")
        self.jobs_changed.emit()

    def _on_finished(self, job: Job) -> None:
        bar = self._progress_bars.get(job.id)
        if bar:
            bar.setValue(100)
            bar.setFormat("100% — Done.")
        self._workers.pop(job.id, None)
        self._active_job_id = None
        self.jobs_changed.emit()
        self._start_next_queued()

    def _on_failed(self, job: Job, err: str) -> None:
        job.state.stage = "FAILED"
        job.state.message = err
        bar = self._progress_bars.get(job.id)
        if bar:
            msg = err.strip() if err else "Failed."
            if len(msg) > 120:
                msg = msg[:117] + "..."
            bar.setValue(job.state.progress or 0)
            bar.setFormat(f"Failed — {msg}")
        self._workers.pop(job.id, None)
        self._active_job_id = None
        self.jobs_changed.emit()
        self._start_next_queued()

    def _start_worker(self, job: Job) -> None:
        bar = self._progress_bars.get(job.id)
        if bar:
            bar.setValue(0)
            bar.setFormat("0% — Starting...")
        worker = JobWorker(job=job)
        self._workers[job.id] = worker
        self._active_job_id = job.id
        worker.progress.connect(lambda pct, msg: self._on_progress(job, pct, msg, bar))
        worker.finished.connect(lambda: self._on_finished(job))
        worker.failed.connect(lambda err: self._on_failed(job, err))
        worker.start()

    def _start_next_queued(self) -> None:
        if not self._queue:
            return
        next_job = self._queue.pop(0)
        next_job.state.stage = "PENDING"
        next_job.state.message = "Starting..."
        self._start_worker(next_job)


def _failed_paths_from_manifest(path: Path) -> list[Path]:
    import csv
    failed: list[Path] = []
    with path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("status") == "FAILED":
                src = row.get("source_path") or ""
                if src:
                    p = Path(src)
                    if p.exists():
                        failed.append(p)
    return failed
