"""명령줄 해석과 대화형 실행을 담당하는 기능."""

from __future__ import annotations

import re
import shlex

try:
    # 방향키 커서 이동과 명령 히스토리를 지원한다. (Windows 등에서는 없을 수 있음)
    import readline  # noqa: F401
except ImportError:
    pass

from errors import MiniGitError
from repository import MiniGitRepository

# ANSI 이스케이프 시퀀스(예: 방향키 "\x1b[A")와 그 밖의 제어 문자
_CONTROL_SEQUENCE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1bO.|[\x00-\x08\x0b-\x1f\x7f]")


class MiniGitCLI:
    """명령줄을 한 줄씩 해석하여 저장소의 해당 기능을 실행한다."""

    def __init__(self, repository: MiniGitRepository | None = None) -> None:
        self.repository = repository or MiniGitRepository()

    @staticmethod
    def _invalid_args(condition: bool) -> None:
        if condition:
            raise MiniGitError("Invalid args")

    @staticmethod
    def _validate_arguments(arguments: list[str], expected_count: int) -> None:
        if len(arguments) != expected_count or any(
            not argument.strip() for argument in arguments
        ):
            raise MiniGitError("Invalid args")

    @staticmethod
    def _option_value(arguments: list[str], name: str) -> str:
        """긴 옵션의 --name=value와 --name value 형식을 해석한다."""

        if len(arguments) == 1 and arguments[0].lower().startswith(name + "="):
            value = arguments[0].split("=", 1)[1]
        elif len(arguments) == 2 and arguments[0].lower() == name:
            value = arguments[1]
        else:
            raise MiniGitError("Invalid args")
        if not value.strip():
            raise MiniGitError("Invalid args")
        return value

    def execute(self, line: str) -> tuple[bool, str]:
        """한 줄을 실행하고 (REPL 계속 여부, 출력 문자열)을 반환한다."""

        if _CONTROL_SEQUENCE.search(line):
            return True, "Invalid args"
        try:
            parts = shlex.split(line)
        except ValueError:
            return True, "Invalid args"
        if not parts:
            return True, ""

        command = parts[0].lower()
        arguments = parts[1:]
        positional_only = bool(arguments and arguments[0] == "--")
        if positional_only:
            arguments = arguments[1:]
        try:
            if command in {"exit", "quit"}:
                self._invalid_args(bool(arguments))
                return False, "Goodbye."

            if command == "init":
                self._validate_arguments(arguments, 1)
                return True, self.repository.init(arguments[0])

            if command == "branch":
                self._validate_arguments(arguments, 1)
                return True, self.repository.create_branch(arguments[0])

            if command == "switch":
                self._validate_arguments(arguments, 1)
                return True, self.repository.switch(arguments[0])

            if command == "commit":
                self._validate_arguments(arguments, 1)
                return True, self.repository.commit(arguments[0])

            if command == "log":
                if not arguments:
                    return True, self.repository.log()
                self._invalid_args(positional_only)
                sort_by = self._option_value(arguments, "--sort-by").lower()
                self._invalid_args(sort_by not in {"date", "author"})
                return True, self.repository.log(sort_by)

            if command == "path":
                self._validate_arguments(arguments, 2)
                return True, self.repository.path(arguments[0], arguments[1])

            if command == "ancestors":
                self._validate_arguments(arguments, 1)
                return True, self.repository.ancestors(arguments[0])

            if command == "search":
                if not positional_only and arguments and (
                    arguments[0].lower() == "--author"
                    or arguments[0].lower().startswith("--author=")
                ):
                    author = self._option_value(arguments, "--author")
                    return True, self.repository.search_author(author)
                self._validate_arguments(arguments, 1)
                query = arguments[0]
                self._invalid_args(not positional_only and query.startswith("--"))
                return True, self.repository.search_keyword(query)

            return True, f"Unknown command: {parts[0]}"
        except MiniGitError as error:
            return True, str(error)


def _print_safely(message: str) -> bool:
    """출력 오류를 전파하지 않고 출력 성공 여부를 반환한다."""

    try:
        print(message, flush=True)
    except (OSError, UnicodeError, ValueError):
        return False
    return True


def run_cli(cli: MiniGitCLI | None = None) -> int:
    """REPL을 실행하고 정상 종료 0, 입출력 오류 1, 사용자 중단 130을 반환한다."""

    cli = cli or MiniGitCLI()
    try:
        while True:
            try:
                line = input("mini-git> ")
            except EOFError:
                return 0 if _print_safely("\nGoodbye.") else 1
            except (OSError, UnicodeError, ValueError) as error:
                _print_safely(f"\nInput error: {error}")
                return 1

            should_continue, output = cli.execute(line)
            if output and not _print_safely(output):
                return 1
            if not should_continue:
                return 0
    except KeyboardInterrupt:
        # 입력, 명령 실행, 출력 중의 Ctrl+C를 한 곳에서 처리한다.
        _print_safely("\nGoodbye.")
        return 130
