from __future__ import annotations

from pathlib import Path
import tempfile

import pytest

from purway_geotagger.core.job import Job, JobOptions
from purway_geotagger.core.pipeline import run_job
from purway_geotagger.util.errors import UserCancelledError


def test_run_job_writes_artifacts_on_cancel() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        run_folder = tmp_path / "PurwayGeotagger_TEST_RUN"

        opts = JobOptions(
            output_root=run_folder,
            overwrite_originals=False,
            create_backup_on_overwrite=True,
            flatten=False,
            cleanup_empty_dirs=False,
            sort_by_ppm=False,
            ppm_bin_edges=[0, 100, 500, 1000],
            write_xmp=True,
            dry_run=True,
            max_join_delta_seconds=3,
            purway_payload="",
            enable_renaming=False,
            rename_template=None,
            start_index=1,
        )

        job = Job(
            id="test",
            name="test",
            inputs=[],
            options=opts,
        )

        with pytest.raises(UserCancelledError):
            run_job(
                job=job,
                progress_cb=lambda _pct, _msg: None,
                cancel_cb=lambda: True,
            )

        assert (run_folder / "run_log.txt").exists()
        assert (run_folder / "run_config.json").exists()
        manifest = run_folder / "manifest.csv"
        assert manifest.exists()
        header = manifest.read_text(encoding="utf-8").splitlines()[0]
        assert "source_path" in header and "output_path" in header
