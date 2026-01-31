from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

@dataclass
class RunLogger:
    path: Path

    def log(self, message: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.path.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] {message}\n")
