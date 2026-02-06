from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from purway_geotagger.gui.controllers import JobController

HEADERS = [
    "Started",
    "Mode",
    "Job",
    "Status",
    "Progress",
    "Output Folder",
    "Inputs",
    "Photos",
    "CSVs",
    "Matched",
    "Success",
    "Failed",
    "Message",
]

class JobTableModel(QAbstractTableModel):
    def __init__(self, controller: JobController) -> None:
        super().__init__()
        self.controller = controller

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.controller.jobs)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return HEADERS[section]
        return str(section)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        job = self.controller.jobs[index.row()]
        st = job.state
        col = index.column()
        if col == 0:
            return _format_started(job)
        if col == 1:
            return _mode_label(job)
        if col == 2:
            return job.name
        if col == 3:
            return _stage_label(st.stage)
        if col == 4:
            return _progress_label(st.stage, st.progress)
        if col == 5:
            return str(job.run_folder or "")
        if col == 6:
            return len(job.inputs)
        if col == 7:
            return st.scanned_photos
        if col == 8:
            return st.scanned_csvs
        if col == 9:
            return st.matched
        if col == 10:
            return st.success
        if col == 11:
            return st.failed
        if col == 12:
            return st.message
        return None


def _format_started(job) -> str:
    if not job.run_folder:
        return ""
    name = job.run_folder.name
    prefix = "PurwayGeotagger_"
    if not name.startswith(prefix):
        return ""
    stamp = name[len(prefix):]
    try:
        dt = datetime.strptime(stamp, "%Y%m%d_%H%M%S")
    except ValueError:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _mode_label(job) -> str:
    mode = getattr(job.options, "run_mode", None)
    if mode is None:
        return "Custom"
    if mode.value == "methane":
        return "Methane"
    if mode.value == "encroachment":
        return "Encroachment"
    if mode.value == "combined":
        return "Combined"
    return mode.value.title()


def _stage_label(stage: str) -> str:
    value = (stage or "").upper()
    if value == "DONE":
        return "Completed"
    if value == "FAILED":
        return "Failed"
    if value == "CANCELLED":
        return "Cancelled"
    if value == "QUEUED":
        return "Queued"
    if value == "PENDING":
        return "Pending"
    return stage.title() if stage else ""


def _progress_label(stage: str, progress: int) -> str:
    value = (stage or "").upper()
    if value in {"DONE", "FAILED", "CANCELLED", "QUEUED"}:
        return "—"
    return f"{max(0, int(progress))}%"
