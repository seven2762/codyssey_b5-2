"""Mini Git CLI의 실행 진입점과 공개 API 모음."""

from cli import MiniGitCLI, run_cli
from errors import MiniGitError
from file_diff import line_diff
from models import Commit
from repository import MiniGitRepository
from sorting import merge_sort

__all__ = [
    "Commit",
    "MiniGitCLI",
    "MiniGitError",
    "MiniGitRepository",
    "line_diff",
    "main",
    "merge_sort",
]


def main() -> None:
    """Mini Git의 읽기-평가-출력 반복문을 실행한다."""

    run_cli(MiniGitCLI())


if __name__ == "__main__":
    main()
