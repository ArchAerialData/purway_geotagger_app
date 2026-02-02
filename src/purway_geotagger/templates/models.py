from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class RenameTemplate:
    id: str
    name: str
    client: str
    pattern: str
    description: str = ""
    start_index: int = 1
