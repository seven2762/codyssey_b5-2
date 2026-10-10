"""따옴표 입력과 브랜치 이름 정규화의 회귀 테스트."""

import unittest
import shutil
import subprocess

from cli import MiniGitCLI
from errors import MiniGitError
from repository import MiniGitRepository


class ParsingTests(unittest.TestCase):
    def setUp(self):
        self.cli = MiniGitCLI()
        self.cli.execute("INIT Alice")

    def test_blank_line_is_empty(self):
        for line in ("", "   ", "\t"):
            with self.subTest(line=line):
                self.assertEqual(self.cli.execute(line), (True, ""))

    def test_empty_argument_is_rejected_without_mutation(self):
        for command in ("BRANCH", "SWITCH", "COMMIT", "INIT", "SEARCH"):
            for argument in ('""', "''", '"   "', "''\"\"''"):
                with self.subTest(command=command, argument=argument):
                    self.assertEqual(
                        self.cli.execute(f"{command} {argument}"), (True, "Invalid args")
                    )
        self.assertEqual(self.cli.repository.branches, {"main": None})
        self.assertEqual(self.cli.repository.commits, {})
        self.assertEqual(self.cli.repository.user, "Alice")

    def test_quotes_in_real_content_are_preserved(self):
        for line, message in (
            ('COMMIT "don\'t remove quotes"', "don't remove quotes"),
            ("COMMIT '\"hello\"'", '"hello"'),
            ('COMMIT "hello "\'world\'', "hello world"),
        ):
            with self.subTest(line=line):
                self.cli.execute(line)
                head = self.cli.repository.branches["main"]
                self.assertEqual(self.cli.repository.commits[head].message, message)

    def test_unclosed_quote_with_text_is_rejected(self):
        self.assertEqual(self.cli.execute('COMMIT "unclosed'), (True, "Invalid args"))
        self.assertEqual(self.cli.repository.commits, {})

    def test_mixed_quotes_follow_shell_rules(self):
        self.assertEqual(
            self.cli.execute("\"'''\"''\"''\"'"), (True, "Invalid args")
        )
        self.assertEqual(
            self.cli.execute('BRANCH "\'\'\'"'), (True, "Created branch: '''")
        )

    def test_long_options_accept_equals_or_separate_value(self):
        self.cli.execute('COMMIT "--author=Alice test"')
        self.assertEqual(
            self.cli.execute("LOG --sort-by=date"), self.cli.execute("LOG --sort-by date")
        )
        self.assertEqual(
            self.cli.execute("SEARCH --author=Alice"), self.cli.execute("SEARCH --author Alice")
        )
        self.assertIn("Found 1 commit:", self.cli.execute("SEARCH -- --author=Alice")[1])
        self.assertEqual(self.cli.execute("SEARCH --author=Alice extra"), (True, "Invalid args"))
        self.assertEqual(self.cli.execute("LOG -- --sort-by=date"), (True, "Invalid args"))
        self.assertEqual(self.cli.execute("SEARCH --author"), (True, "Invalid args"))

    def test_control_characters_do_not_turn_into_valid_commands(self):
        self.assertEqual(self.cli.execute('COM\x00MIT "test"'), (True, "Invalid args"))
        self.assertEqual(self.cli.repository.commits, {})

    def test_trimmed_branch_can_be_created_switched_and_detected_as_duplicate(self):
        self.assertEqual(
            self.cli.execute('BRANCH " feature "'), (True, "Created branch: feature")
        )
        self.assertEqual(
            self.cli.execute('BRANCH feature'), (True, "Branch already exists: feature")
        )
        self.assertEqual(
            self.cli.execute('SWITCH " feature "'), (True, "Switched to branch: feature")
        )
        self.assertEqual(self.cli.repository.current_branch, "feature")
        self.cli.execute('COMMIT "test"')
        self.assertIsNotNone(self.cli.repository.branches["feature"])
        self.assertNotIn(" feature ", self.cli.repository.branches)

    def test_repository_api_also_normalizes_branch_names(self):
        repo = MiniGitRepository()
        repo.init("Alice")
        self.assertEqual(repo.create_branch("\t feature \n"), "Created branch: feature")
        self.assertEqual(repo.switch(" feature "), "Switched to branch: feature")
        for name in (" ", "feature name", "feature\tname"):
            for operation in (repo.create_branch, repo.switch):
                with self.subTest(name=name, operation=operation.__name__):
                    with self.assertRaises(MiniGitError):
                        operation(name)
        self.assertEqual(set(repo.branches), {"main", "feature"})

    @unittest.skipUnless(shutil.which("git"), "Git을 사용할 수 없음")
    def test_branch_validation_matches_git_after_requested_trim(self):
        names = (
            "feature", " feature ", "feature/login", "한글", "@", "'''", '"',
            "", " ", "HEAD", "-feature", "feature name", "feature\tname", ".hidden",
            "feature.lock", "feature.lock/topic", "a..b", "a@{b", "a//b", "a/", "/a",
            "a.", "a\\b", "a~b", "a^b", "a:b", "a?b", "a*b", "a[b", "a\x7fb",
        )
        for name in names:
            with self.subTest(name=name):
                result = subprocess.run(
                    ["git", "check-ref-format", "--branch", name.strip()],
                    capture_output=True, timeout=5,
                )
                if result.returncode == 0:
                    self.assertEqual(MiniGitRepository._normalize_branch_name(name), name.strip())
                else:
                    with self.assertRaises(MiniGitError):
                        MiniGitRepository._normalize_branch_name(name)


if __name__ == "__main__":
    unittest.main()
