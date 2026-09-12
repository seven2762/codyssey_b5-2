"""대화형 CLI를 제공하는 소규모 메모리 기반 Git형 커밋 그래프."""

from __future__ import annotations

import hashlib
import shlex
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, TypeVar


T = TypeVar("T")


def merge_sort(items: Iterable[T], key: Callable[[T], Any] = lambda item: item) -> list[T]:
    """*items*를 안정 병합 정렬한 복사본을 O(n log n)에 반환한다.

    Python 내장 정렬 API를 사용하지 않고 직접 구현한다. 키가 같으면 왼쪽
    원소를 먼저 선택하므로 정렬 결과의 기존 순서가 유지된다.
    """

    values = list(items)
    if len(values) <= 1:
        return values

    middle = len(values) // 2
    left = merge_sort(values[:middle], key)
    right = merge_sort(values[middle:], key)
    merged: list[T] = []
    left_index = 0
    right_index = 0

    while left_index < len(left) and right_index < len(right):
        if key(left[left_index]) <= key(right[right_index]):
            merged.append(left[left_index])
            left_index += 1
        else:
            merged.append(right[right_index])
            right_index += 1

    merged.extend(left[left_index:])
    merged.extend(right[right_index:])
    return merged


@dataclass(frozen=True)
class Commit:
    """커밋 DAG를 구성하는 불변 노드 하나."""

    hash: str
    message: str
    author: str
    timestamp: datetime
    parents: tuple[str, ...]


class MiniGitError(Exception):
    """사용자에게 안내할 수 있는 예상된 Mini Git 오류."""


class MiniGitRepository:
    """브랜치, 커밋, 그래프 간선, 역색인을 메모리에 저장한다."""

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or datetime.now
        self._session_id = uuid.uuid4().hex
        self._next_commit_id = 1
        self.initialized = False
        self.user = ""
        self.current_branch = ""
        self.branches: dict[str, str | None] = {}
        self.commits: dict[str, Commit] = {}
        self.children: dict[str, set[str]] = {}
        self.keyword_index: dict[str, set[str]] = {}
        self.author_index: dict[str, set[str]] = {}

    def init(self, user_name: str) -> str:
        """메모리 저장소를 새로 만들거나 초기 상태로 되돌린다."""

        if not user_name.strip():
            raise MiniGitError("Invalid args")

        self._session_id = uuid.uuid4().hex
        self._next_commit_id = 1
        self.initialized = True
        self.user = user_name
        self.current_branch = "main"
        self.branches = {"main": None}
        self.commits = {}
        self.children = {}
        self.keyword_index = {}
        self.author_index = {}
        return (
            "Initialized repository.\n"
            "Current branch: main\n"
            f"Current user: {user_name}"
        )

    def _require_initialized(self) -> None:
        if not self.initialized:
            raise MiniGitError("Repository not initialized")

    def _new_hash(
        self, message: str, timestamp: datetime, parents: tuple[str, ...]
    ) -> str:
        """현재 세션에서 고유한 짧은 커밋 해시를 만들고 충돌을 검사한다."""

        while True:
            material = "\0".join(
                (
                    self._session_id,
                    str(self._next_commit_id),
                    self.user,
                    timestamp.isoformat(),
                    message,
                    *parents,
                )
            )
            self._next_commit_id += 1
            candidate = hashlib.sha1(material.encode("utf-8")).hexdigest()[:10]
            if candidate not in self.commits:
                return candidate

    @staticmethod
    def _message_tokens(message: str) -> set[str]:
        """과제 기준에 따라 공백으로 분리하고 소문자화한 토큰을 만든다."""

        return {token.lower() for token in message.split() if token}

    def _index_commit(self, commit: Commit) -> None:
        self.author_index.setdefault(commit.author, set()).add(commit.hash)
        for token in self._message_tokens(commit.message):
            self.keyword_index.setdefault(token, set()).add(commit.hash)

    def _create_commit(self, message: str, parents: tuple[str, ...]) -> Commit:
        timestamp = self._clock()
        commit_hash = self._new_hash(message, timestamp, parents)
        commit = Commit(commit_hash, message, self.user, timestamp, parents)
        self.commits[commit_hash] = commit
        self.children[commit_hash] = set()
        for parent_hash in parents:
            self.children[parent_hash].add(commit_hash)
        self.branches[self.current_branch] = commit_hash
        self._index_commit(commit)
        return commit

    def create_branch(self, branch_name: str) -> str:
        """현재 브랜치의 HEAD를 가리키는 새 브랜치를 만든다."""

        self._require_initialized()
        if not branch_name.strip():
            raise MiniGitError("Invalid args")
        if branch_name in self.branches:
            raise MiniGitError(f"Branch already exists: {branch_name}")
        self.branches[branch_name] = self.branches[self.current_branch]
        return f"Created branch: {branch_name}"

    def switch(self, branch_name: str) -> str:
        """심볼릭 HEAD를 이미 존재하는 브랜치로 옮긴다."""

        self._require_initialized()
        if branch_name not in self.branches:
            raise MiniGitError(f"Unknown branch: {branch_name}")
        self.current_branch = branch_name
        return f"Switched to branch: {branch_name}"

    def commit(self, message: str) -> str:
        """현재 브랜치 HEAD를 부모로 하는 일반 커밋을 만든다."""

        self._require_initialized()
        if not message.strip():
            raise MiniGitError("Invalid args")
        head = self.branches[self.current_branch]
        parents = () if head is None else (head,)
        new_commit = self._create_commit(message, parents)
        return f"[{self.current_branch} {new_commit.hash}] {message}"

    def merge(self, branch_name: str) -> str:
        """부모가 두 개인 병합 커밋을 만든다(선택 보너스 명령)."""

        self._require_initialized()
        if branch_name not in self.branches:
            raise MiniGitError(f"Unknown branch: {branch_name}")
        if branch_name == self.current_branch:
            raise MiniGitError("Cannot merge the current branch")

        current_head = self.branches[self.current_branch]
        other_head = self.branches[branch_name]
        if current_head is None or other_head is None:
            raise MiniGitError("Cannot merge a branch without commits")
        if current_head == other_head:
            return "Already up to date."

        message = f"Merge branch '{branch_name}'"
        new_commit = self._create_commit(message, (current_head, other_head))
        return f"[{self.current_branch} {new_commit.hash}] {message}"

    def _ordered_children(self, commit_hash: str) -> list[str]:
        return merge_sort(self.children.get(commit_hash, set()), key=lambda value: value)

    def topological_hashes(self) -> list[str]:
        """모든 부모가 자식보다 앞에 오도록 전체 커밋 해시를 반환한다."""

        indegree = {
            commit_hash: len(commit.parents)
            for commit_hash, commit in self.commits.items()
        }
        roots = merge_sort(
            (commit_hash for commit_hash, degree in indegree.items() if degree == 0),
            key=lambda value: value,
        )
        queue = deque(roots)
        result: list[str] = []

        while queue:
            commit_hash = queue.popleft()
            result.append(commit_hash)
            for child_hash in self._ordered_children(commit_hash):
                indegree[child_hash] -= 1
                if indegree[child_hash] == 0:
                    queue.append(child_hash)

        if len(result) != len(self.commits):
            raise RuntimeError("Commit graph contains a cycle")
        return result

    def log_hashes(self, sort_by: str | None = None) -> list[str]:
        """기본 위상 순서 또는 지정한 기준의 병합 정렬 순서를 선택한다."""

        self._require_initialized()
        if sort_by is None:
            return self.topological_hashes()

        commits = list(self.commits.values())
        if sort_by == "date":
            ordered = merge_sort(commits, key=lambda item: (item.timestamp, item.hash))
        elif sort_by == "author":
            ordered = merge_sort(
                commits,
                key=lambda item: (
                    item.author.casefold(),
                    item.author,
                    item.timestamp,
                    item.hash,
                ),
            )
        else:
            raise MiniGitError("Invalid args")
        return [commit.hash for commit in ordered]

    def _branch_labels(self, commit_hash: str) -> list[str]:
        labels = [
            branch_name
            for branch_name, head_hash in self.branches.items()
            if head_hash == commit_hash
        ]
        return merge_sort(labels, key=lambda value: value)

    def format_commits(self, commit_hashes: Iterable[str]) -> str:
        """필수 메타데이터를 식별할 수 있는 형식으로 커밋을 출력한다."""

        blocks: list[str] = []
        for commit_hash in commit_hashes:
            commit = self.commits[commit_hash]
            labels = self._branch_labels(commit_hash)
            label_text = f" [{', '.join(labels)}]" if labels else ""
            timestamp = commit.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            blocks.append(
                f"commit {commit.hash} ({commit.author}, {timestamp}){label_text}\n"
                f"{commit.message}"
            )
        return "\n\n".join(blocks)

    def log(self, sort_by: str | None = None) -> str:
        hashes = self.log_hashes(sort_by)
        return self.format_commits(hashes) if hashes else "No commits."

    def _validate_commit(self, commit_hash: str) -> None:
        if commit_hash not in self.commits:
            raise MiniGitError(f"Unknown commit: {commit_hash}")

    def _adjacent(self, commit_hash: str) -> list[str]:
        neighbors = set(self.commits[commit_hash].parents)
        neighbors.update(self.children.get(commit_hash, set()))
        return merge_sort(neighbors, key=lambda value: value)

    def _distances(self, start_hash: str) -> dict[str, int]:
        """너비 우선 탐색으로 가중치 없는 최단 거리를 계산한다."""

        distances = {start_hash: 0}
        queue = deque([start_hash])
        while queue:
            commit_hash = queue.popleft()
            for neighbor_hash in self._adjacent(commit_hash):
                if neighbor_hash not in distances:
                    distances[neighbor_hash] = distances[commit_hash] + 1
                    queue.append(neighbor_hash)
        return distances

    def shortest_path(self, start_hash: str, end_hash: str) -> list[str] | None:
        """모든 무방향 최단 경로 중 사전순으로 가장 작은 경로를 찾는다."""

        self._require_initialized()
        self._validate_commit(start_hash)
        self._validate_commit(end_hash)
        if start_hash == end_hash:
            return [start_hash]

        from_start = self._distances(start_hash)
        if end_hash not in from_start:
            return None
        from_end = self._distances(end_hash)
        path_length = from_start[end_hash]
        path = [start_hash]
        current_hash = start_hash

        while current_hash != end_hash:
            candidates = [
                neighbor_hash
                for neighbor_hash in self._adjacent(current_hash)
                if from_start.get(neighbor_hash) == from_start[current_hash] + 1
                and from_start[neighbor_hash] + from_end[neighbor_hash] == path_length
            ]
            candidates = merge_sort(candidates, key=lambda value: value)
            current_hash = candidates[0]
            path.append(current_hash)
        return path

    def path(self, start_hash: str, end_hash: str) -> str:
        result = self.shortest_path(start_hash, end_hash)
        return "No path" if result is None else f"Path: {' -> '.join(result)}"

    def ancestor_hashes(self, commit_hash: str) -> list[str]:
        """자기 자신을 제외한 모든 조상을 부모 우선 순서로 반환한다."""

        self._require_initialized()
        self._validate_commit(commit_hash)
        ancestors: set[str] = set()
        stack = list(self.commits[commit_hash].parents)
        while stack:
            ancestor_hash = stack.pop()
            if ancestor_hash in ancestors:
                continue
            ancestors.add(ancestor_hash)
            stack.extend(self.commits[ancestor_hash].parents)
        return [item for item in self.topological_hashes() if item in ancestors]

    def ancestors(self, commit_hash: str) -> str:
        hashes = self.ancestor_hashes(commit_hash)
        return self.format_commits(hashes) if hashes else "No ancestors."

    def search_keyword_hashes(self, query: str) -> list[str]:
        """전체 커밋을 순회하지 않고 포스팅 목록의 교집합을 사용한다."""

        self._require_initialized()
        tokens = self._message_tokens(query)
        if not tokens:
            raise MiniGitError("Invalid args")

        postings: set[str] | None = None
        for token in tokens:
            token_hashes = self.keyword_index.get(token, set())
            postings = set(token_hashes) if postings is None else postings & token_hashes
            if not postings:
                return []
        return self._search_order(postings or set())

    def search_author_hashes(self, author: str) -> list[str]:
        """작성자의 포스팅 목록을 역색인에서 직접 읽는다."""

        self._require_initialized()
        if not author.strip():
            raise MiniGitError("Invalid args")
        return self._search_order(self.author_index.get(author, set()))

    def _search_order(self, hashes: Iterable[str]) -> list[str]:
        commits = (self.commits[commit_hash] for commit_hash in hashes)
        ordered = merge_sort(commits, key=lambda item: (item.timestamp, item.hash))
        return [commit.hash for commit in ordered]

    def format_search_results(self, hashes: list[str]) -> str:
        if not hashes:
            return "Found 0 commits."
        lines = [f"Found {len(hashes)} commit(s):", ""]
        for commit_hash in hashes:
            commit = self.commits[commit_hash]
            lines.append(f"- {commit.hash} ({commit.author}): {commit.message}")
        return "\n".join(lines)

    def search_keyword(self, query: str) -> str:
        return self.format_search_results(self.search_keyword_hashes(query))

    def search_author(self, author: str) -> str:
        return self.format_search_results(self.search_author_hashes(author))


def line_diff(file1: str, file2: str) -> str:
    """LCS 기반의 간단한 줄 단위 차이를 반환한다(선택 보너스 명령)."""

    try:
        left = Path(file1).read_text(encoding="utf-8").splitlines()
        right = Path(file2).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError, ValueError) as error:
        raise MiniGitError(f"Cannot read file: {error}") from error

    rows = len(left) + 1
    columns = len(right) + 1
    lengths = [[0] * columns for _ in range(rows)]
    for left_index in range(len(left) - 1, -1, -1):
        for right_index in range(len(right) - 1, -1, -1):
            if left[left_index] == right[right_index]:
                lengths[left_index][right_index] = lengths[left_index + 1][right_index + 1] + 1
            else:
                lengths[left_index][right_index] = max(
                    lengths[left_index + 1][right_index],
                    lengths[left_index][right_index + 1],
                )

    output: list[str] = []
    left_index = 0
    right_index = 0
    while left_index < len(left) and right_index < len(right):
        if left[left_index] == right[right_index]:
            output.append(f"  {left[left_index]}")
            left_index += 1
            right_index += 1
        elif lengths[left_index + 1][right_index] >= lengths[left_index][right_index + 1]:
            output.append(f"- {left[left_index]}")
            left_index += 1
        else:
            output.append(f"+ {right[right_index]}")
            right_index += 1
    while left_index < len(left):
        output.append(f"- {left[left_index]}")
        left_index += 1
    while right_index < len(right):
        output.append(f"+ {right[right_index]}")
        right_index += 1
    return "\n".join(output) if output else "No differences."


class MiniGitCLI:
    """명령줄을 한 줄씩 해석하여 저장소의 해당 기능을 실행한다."""

    def __init__(self, repository: MiniGitRepository | None = None) -> None:
        self.repository = repository or MiniGitRepository()

    @staticmethod
    def _invalid_args(condition: bool) -> None:
        if condition:
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
                self._invalid_args(len(arguments) != 1)
                return True, self.repository.init(arguments[0])

            if command == "branch":
                self._invalid_args(len(arguments) != 1)
                return True, self.repository.create_branch(arguments[0])

            if command == "switch":
                self._invalid_args(len(arguments) != 1)
                return True, self.repository.switch(arguments[0])

            if command == "commit":
                self._invalid_args(len(arguments) != 1)
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
                self._invalid_args(len(arguments) != 2)
                return True, self.repository.path(arguments[0], arguments[1])

            if command == "ancestors":
                self._invalid_args(len(arguments) != 1)
                return True, self.repository.ancestors(arguments[0])

            if command == "search":
                self._invalid_args(len(arguments) != 1)
                query = arguments[0]
                if query.lower().startswith("--author="):
                    author = query.split("=", 1)[1]
                    self._invalid_args(not author)
                    return True, self.repository.search_author(author)
                return True, self.repository.search_keyword(query)

            if command == "merge":
                self._invalid_args(len(arguments) != 1)
                return True, self.repository.merge(arguments[0])

            if command == "diff":
                self._invalid_args(len(arguments) != 2)
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


def main() -> None:
    """Mini Git의 읽기-평가-출력 반복문을 실행한다."""

    cli = MiniGitCLI()
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
        if output:
            if not _print_safely(output):
                break
        if not should_continue:
            break


if __name__ == "__main__":
    main()
