"""명령줄 해석과 대화형 실행을 담당하는 기능."""

from __future__ import annotations

import shlex

from errors import MiniGitError
from file_diff import line_diff
from repository import MiniGitRepository


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

    def execute(self, line: str) -> tuple[bool, str]:
        """한 줄을 실행하고 (REPL 계속 여부, 출력 문자열)을 반환한다."""

        try:
            parts = shlex.split(line)
        except ValueError:
            return True, "Invalid args"
        if not parts:
            return True, ""

        command = parts[0].lower()
        arguments = parts[1:]
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
                self._invalid_args(len(arguments) != 1)
                option = arguments[0]
                self._invalid_args(not option.lower().startswith("--sort-by="))
                sort_by = option.split("=", 1)[1].lower()
                self._invalid_args(sort_by not in {"date", "author"})
                return True, self.repository.log(sort_by)

            if command == "path":
                self._validate_arguments(arguments, 2)
                return True, self.repository.path(arguments[0], arguments[1])

            if command == "ancestors":
                self._validate_arguments(arguments, 1)
                return True, self.repository.ancestors(arguments[0])

            if command == "search":
                self._validate_arguments(arguments, 1)
                query = arguments[0]
                if query.lower().startswith("--author="):
                    author = query.split("=", 1)[1]
                    self._invalid_args(not author.strip())
                    return True, self.repository.search_author(author)
                self._invalid_args(query.startswith("--"))
                return True, self.repository.search_keyword(query)

            if command == "merge":
                self._validate_arguments(arguments, 1)
                return True, self.repository.merge(arguments[0])

            if command == "diff":
                self._validate_arguments(arguments, 2)
                return True, line_diff(arguments[0], arguments[1])

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


def run_cli(cli: MiniGitCLI | None = None) -> None:
    """전달받은 CLI로 읽기-평가-출력 반복문을 실행한다."""

    cli = cli or MiniGitCLI()
    while True:
        try:
            line = input("mini-git> ")
        except (EOFError, KeyboardInterrupt):
            _print_safely("\nGoodbye.")
            break
        except (OSError, UnicodeError, ValueError) as error:
            _print_safely(f"\nInput error: {error}")
            break

        try:
            should_continue, output = cli.execute(line)
        except KeyboardInterrupt:
            _print_safely("\nGoodbye.")
            break
        if output and not _print_safely(output):
            break
        if not should_continue:
            break
