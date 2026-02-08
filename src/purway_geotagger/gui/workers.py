from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from pathlib import Path

from purway_geotagger.core.preview import build_preview, PreviewResult
from purway_geotagger.core.wind_weather_autofill import (
    WindAutofillRequest,
    WindWeatherAutofillService,
)

from purway_geotagger.core.job import Job
from purway_geotagger.core.pipeline import run_job
from purway_geotagger.util.errors import UserCancelledError

class JobWorker(QThread):
    progress = Signal(int, str)  # percent, message
    finished = Signal()
    failed = Signal(str)

    def __init__(self, job: Job) -> None:
        super().__init__()
        self.job = job
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            run_job(
                job=self.job,
                progress_cb=lambda pct, msg: self.progress.emit(int(pct), msg),
                cancel_cb=lambda: self._cancelled,
            )
            self.finished.emit()
        except UserCancelledError:
            self.failed.emit("Cancelled by user.")
        except Exception as e:
            self.failed.emit(str(e))


class PreviewWorker(QThread):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, inputs: list[Path], max_rows: int, max_join_delta_seconds: int) -> None:
        super().__init__()
        self.inputs = inputs
        self.max_rows = max_rows
        self.max_join_delta_seconds = max_join_delta_seconds

    def run(self) -> None:
        try:
            result = build_preview(self.inputs, self.max_rows, self.max_join_delta_seconds)
            self.finished.emit(result)
        except Exception as e:
            self.failed.emit(str(e))


class WindLocationSearchWorker(QThread):
    results_ready = Signal(object)
    failed = Signal(str)

    def __init__(self, query: str, limit: int = 8) -> None:
        super().__init__()
        self.query = query
        self.limit = limit

    def run(self) -> None:
        try:
            service = WindWeatherAutofillService()
            results = service.search_locations(self.query, limit=self.limit)
            self.results_ready.emit(results)
        except Exception as e:
            self.failed.emit(str(e))


class WindAutofillWorker(QThread):
    result_ready = Signal(object)
    failed = Signal(str)

    def __init__(self, request: WindAutofillRequest) -> None:
        super().__init__()
        self.request = request

    def run(self) -> None:
        try:
            service = WindWeatherAutofillService()
            result = service.build_autofill(self.request)
            self.result_ready.emit(result)
        except Exception as e:
            self.failed.emit(str(e))
