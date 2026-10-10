"""Mini Git CLI의 실행 진입점과 공개 API 모음."""

from cli import MiniGitCLI, run_cli
from errors import MiniGitError
from models import Commit
from repository import MiniGitRepository
from sorting import merge_sort

__all__ = [
    "Commit",
    "MiniGitCLI",
    "MiniGitError",
    "MiniGitRepository",
    "main",
    "merge_sort",
]


def main() -> int:
    """Mini Git을 실행하고 프로세스 종료 코드를 반환한다."""

    return run_cli(MiniGitCLI())


if __name__ == "__main__":
    raise SystemExit(main())
