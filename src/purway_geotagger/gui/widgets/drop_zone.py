from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

class DropZone(QFrame):
    """A drag & drop area that emits dropped filesystem paths.

    Accepts:
    - directories
    - files (jpg/csv)
    """
    paths_dropped = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.setFrameShape(QFrame.StyledPanel)
        self.setAcceptDrops(True)
        # Apply the QSS class
        self.setProperty("cssClass", "dropzone")

        layout = QVBoxLayout(self)
        lbl = QLabel("Drop folders or files here")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setProperty("cssClass", "subtitle")
        layout.addWidget(lbl)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
        if paths:
            self.paths_dropped.emit(paths)
        event.acceptProposedAction()
