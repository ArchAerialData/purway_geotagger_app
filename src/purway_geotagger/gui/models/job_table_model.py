from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from purway_geotagger.gui.controllers import JobController

HEADERS = ["Name", "Inputs", "Stage", "Progress", "Photos", "CSVs", "Matched", "Success", "Failed", "Message", "Output Folder"]

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
        if col == 0: return job.name
        if col == 1: return len(job.inputs)
        if col == 2: return st.stage
        if col == 3: return f"{st.progress}%"
        if col == 4: return st.scanned_photos
        if col == 5: return st.scanned_csvs
        if col == 6: return st.matched
        if col == 7: return st.success
        if col == 8: return st.failed
        if col == 9: return st.message
        if col == 10: return str(job.run_folder or "")
        return None
