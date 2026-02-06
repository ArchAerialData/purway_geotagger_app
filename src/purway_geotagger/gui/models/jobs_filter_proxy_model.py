from __future__ import annotations

from PySide6.QtCore import QSortFilterProxyModel


class JobsFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._status_filter = "all"
        self._search_text = ""
        self._show_all_history = False
        self._recent_limit = 20

    def set_status_filter(self, value: str) -> None:
        text = (value or "all").strip().lower()
        if text not in {"all", "running", "failed", "completed"}:
            text = "all"
        if self._status_filter == text:
            return
        self._status_filter = text
        self.invalidateFilter()

    def set_search_text(self, value: str) -> None:
        text = (value or "").strip().lower()
        if self._search_text == text:
            return
        self._search_text = text
        self.invalidateFilter()

    def set_show_all_history(self, enabled: bool) -> None:
        value = bool(enabled)
        if self._show_all_history == value:
            return
        self._show_all_history = value
        self.invalidateFilter()

    def set_recent_limit(self, limit: int) -> None:
        value = max(1, int(limit))
        if self._recent_limit == value:
            return
        self._recent_limit = value
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        model = self.sourceModel()
        controller = getattr(model, "controller", None)
        if controller is None:
            return True

        jobs = controller.jobs
        if source_row < 0 or source_row >= len(jobs):
            return False

        job = jobs[source_row]
        stage = (job.state.stage or "").upper()

        if self._status_filter == "running" and stage in {"DONE", "FAILED", "CANCELLED"}:
            return False
        if self._status_filter == "failed" and stage != "FAILED":
            return False
        if self._status_filter == "completed" and stage != "DONE":
            return False

        if not self._show_all_history:
            cutoff = max(0, len(jobs) - self._recent_limit)
            if source_row < cutoff:
                return False

        if self._search_text:
            mode = getattr(job.options, "run_mode", None)
            mode_text = mode.value if mode is not None else "custom"
            haystack = " ".join(
                [
                    job.name or "",
                    job.state.stage or "",
                    job.state.message or "",
                    str(job.run_folder or ""),
                    mode_text,
                ]
            ).lower()
            if self._search_text not in haystack:
                return False

        return True
