from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Repository:
    name: str
    updated_at: datetime
    stars: int
    forks: int