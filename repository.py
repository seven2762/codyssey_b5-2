"""브랜치와 커밋 그래프를 관리하는 메모리 저장소."""

from __future__ import annotations

import hashlib
import uuid
from collections import deque
from datetime import datetime
from typing import Callable, Iterable

from errors import MiniGitError
from models import Commit
from sorting import merge_sort


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
        if not branch_name.strip():
            raise MiniGitError("Invalid args")
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
        if not branch_name.strip():
            raise MiniGitError("Invalid args")
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
        return merge_sort(
            self.children.get(commit_hash, set()), key=lambda value: value
        )

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
        """지정한 순서로 정렬한 커밋 로그를 문자열로 만든다."""

        hashes = self.log_hashes(sort_by)
        return self.format_commits(hashes) if hashes else "No commits."

    def _validate_commit(self, commit_hash: str) -> None:
        if not commit_hash.strip():
            raise MiniGitError("Invalid args")
        if commit_hash not in self.commits:
            raise MiniGitError(f"Unknown commit: {commit_hash}")

    def _adjacent(self, commit_hash: str) -> set[str]:
        neighbors = set(self.commits[commit_hash].parents)
        neighbors.update(self.children.get(commit_hash, set()))
        return neighbors

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
            next_hash: str | None = None
            for neighbor_hash in self._adjacent(current_hash):
                follows_shortest_path = (
                    from_start.get(neighbor_hash) == from_start[current_hash] + 1
                    and from_start[neighbor_hash] + from_end[neighbor_hash]
                    == path_length
                )
                if follows_shortest_path and (
                    next_hash is None or neighbor_hash < next_hash
                ):
                    next_hash = neighbor_hash

            if next_hash is None:
                raise RuntimeError("Cannot reconstruct the shortest path")
            current_hash = next_hash
            path.append(current_hash)
        return path

    def path(self, start_hash: str, end_hash: str) -> str:
        """두 커밋 사이의 최단 경로를 출력 형식으로 반환한다."""

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
        """지정한 커밋의 모든 조상을 출력 형식으로 반환한다."""

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
        """검색된 커밋 해시 목록을 읽기 좋은 문자열로 만든다."""

        if not hashes:
            return "Found 0 commits."
        noun = "commit" if len(hashes) == 1 else "commits"
        lines = [f"Found {len(hashes)} {noun}:", ""]
        for commit_hash in hashes:
            commit = self.commits[commit_hash]
            lines.append(f"- {commit.hash} ({commit.author}): {commit.message}")
        return "\n".join(lines)

    def search_keyword(self, query: str) -> str:
        """메시지 키워드의 역색인을 조회해 결과를 출력한다."""

        return self.format_search_results(self.search_keyword_hashes(query))

    def search_author(self, author: str) -> str:
        """작성자 역색인을 조회해 결과를 출력한다."""

        return self.format_search_results(self.search_author_hashes(author))
