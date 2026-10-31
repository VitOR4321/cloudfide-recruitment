import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verify import verify


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / "backend").mkdir()
        (self.root / "frontend").mkdir()
        self.output = self.root / "results"

    def run_checks(self, *, tests=2, skipped=0, failures=0, backend_exit=0, reports=True):
        def run(command, *, cwd, env, **kwargs):
            for name in ("TEST_AGENT_API_KEY", "OPENAI_API_KEY", "GH_TOKEN", "GITHUB_TOKEN"):
                self.assertNotIn(name, env)
            suite = cwd.name
            is_test = suite == "backend" or "test:coverage" in command
            if reports and is_test:
                directory = cwd / "coverage"
                directory.mkdir(exist_ok=True)
                (directory / "results.xml").write_text(
                    f'<testsuites><testsuite tests="{tests}" skipped="{skipped}" '
                    f'failures="{failures}" errors="0" /></testsuites>'
                )
            return subprocess.CompletedProcess(command, backend_exit if suite == "backend" else 0, "test output <error>", "")

        with patch("verify.subprocess.run", side_effect=run), patch.dict("os.environ", {
            "TEST_AGENT_API_KEY": "fixture", "OPENAI_API_KEY": "fixture",
            "GH_TOKEN": "fixture", "GITHUB_TOKEN": "fixture",
        }), patch("builtins.print"):
            return verify(self.root, self.output)

    def test_passing_suites_produce_counts_and_strip_credentials(self):
        self.assertEqual(self.run_checks(), 0)
        result = json.loads((self.output / "results.json").read_text())
        self.assertEqual(result["tests"]["frontend"]["tests"], 2)
        self.assertEqual(result["tests"]["backend"]["tests"], 2)
        self.assertTrue((self.output / "summary.md").exists())

    def test_preserves_failing_command_status_in_report(self):
        self.assertEqual(self.run_checks(backend_exit=1), 1)
        result = json.loads((self.output / "results.json").read_text())
        backend = next(check for check in result["checks"] if check["name"] == "backend")
        self.assertEqual(backend["exit_code"], 1)
        self.assertTrue((self.output / "frontend.log").exists())
        summary = (self.output / "summary.md").read_text()
        self.assertIn("backend failure", summary)
        self.assertIn("test output &lt;error&gt;", summary)
        self.assertNotIn("test output <error>", summary)

    def test_zero_or_all_skipped_tests_do_not_count_as_verification(self):
        for tests, skipped in [(0, 0), (2, 2)]:
            with self.subTest(tests=tests, skipped=skipped):
                self.assertEqual(self.run_checks(tests=tests, skipped=skipped), 1)

    def test_reported_failures_fail_verification_even_with_zero_exit(self):
        self.assertEqual(self.run_checks(failures=1), 1)

    def test_stale_result_files_cannot_make_a_failed_run_pass(self):
        for suite in ("backend", "frontend"):
            directory = self.root / suite / "coverage"
            directory.mkdir()
            (directory / "results.xml").write_text('<testsuites><testsuite tests="5" /></testsuites>')
        self.assertEqual(self.run_checks(reports=False), 1)
        result = json.loads((self.output / "results.json").read_text())
        self.assertEqual(result["tests"], {})


if __name__ == "__main__":
    unittest.main()
