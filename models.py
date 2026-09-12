"""Mini Git의 데이터 모델."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Commit:
    """커밋 DAG를 구성하는 불변 노드 하나."""

    hash: str
    message: str
    author: str
    timestamp: datetime
    parents: tuple[str, ...]
