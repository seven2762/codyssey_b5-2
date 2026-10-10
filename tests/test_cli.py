"""REPL 종료 경로와 실제 프로세스 종료 코드의 회귀 테스트."""

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from cli import run_cli


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CLIExitTests(unittest.TestCase):
    def test_keyboard_interrupt_during_input_command_or_output(self):
        for phase in ("input", "execute", "output"):
            with self.subTest(phase=phase):
                cli = Mock()
                cli.execute.return_value = (True, "Command output")
                if phase == "execute":
                    cli.execute.side_effect = KeyboardInterrupt
                input_effect = KeyboardInterrupt if phase == "input" else None
                print_effect = [KeyboardInterrupt, None] if phase == "output" else None
                with patch("builtins.input", return_value="LOG", side_effect=input_effect), patch(
                    "builtins.print", side_effect=print_effect
                ) as output:
                    self.assertEqual(run_cli(cli), 130)
                output.assert_any_call("\nGoodbye.", flush=True)

    def test_eof_exits_without_executing_a_command(self):
        cli = Mock()
        with patch("builtins.input", side_effect=EOFError), patch("builtins.print"):
            self.assertEqual(run_cli(cli), 0)
        cli.execute.assert_not_called()

    def test_input_and_output_errors_return_failure(self):
        with patch("builtins.input", side_effect=OSError("unavailable")), patch(
            "builtins.print"
        ):
            self.assertEqual(run_cli(), 1)
        with patch("builtins.input", return_value="quit"), patch(
            "builtins.print", side_effect=OSError("unavailable")
        ):
            self.assertEqual(run_cli(), 1)

    def test_invalid_command_does_not_stop_repl(self):
        with patch("builtins.input", side_effect=["LOG", "quit"]), patch(
            "builtins.print"
        ) as output:
            self.assertEqual(run_cli(), 0)
        output.assert_any_call("Repository not initialized", flush=True)
        output.assert_any_call("Goodbye.", flush=True)

    def test_normal_exit_codes_reach_process(self):
        for data in ("", "exit\n", "quit\n"):
            with self.subTest(input=data):
                result = subprocess.run(
                    [sys.executable, "main.py"], input=data, text=True,
                    capture_output=True, cwd=PROJECT_ROOT, timeout=5,
                )
                self.assertEqual(result.returncode, 0)
                self.assertIn("Goodbye.", result.stdout)
                self.assertEqual(result.stderr, "")

    def test_interrupt_exit_code_reaches_process(self):
        result = subprocess.run(
            [sys.executable, "-c", (
                "import runpy; from unittest.mock import patch; "
                "patch('builtins.input', side_effect=KeyboardInterrupt).start(); "
                "runpy.run_path('main.py', run_name='__main__')"
            )], capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=5,
        )
        self.assertEqual(result.returncode, 130)
        self.assertIn("Goodbye.", result.stdout)
        self.assertEqual(result.stderr, "")

if __name__ == "__main__":
    unittest.main()
