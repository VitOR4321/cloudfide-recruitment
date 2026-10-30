import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import apply, generate, prepare
from safety import safe_path, validate_proposal


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.proposal = {
            "decision": "propose", "reason": "Cover missing task responses.",
            "files": [{"path": "backend/tests/test_missing.py", "content": "def test_missing():\n    assert True\n"}],
        }

    def test_rejects_production_and_configuration_writes(self):
        for name in ("backend/app/main.py", "backend/tests/conftest.py", ".github/workflows/ci.yml",
                     "frontend/package.json", "frontend/src/App.tsx", "/tmp/test_escape.py",
                     "backend/tests/../../test_escape.py", "backend/tests//test_escape.py",
                     "backend/tests/test_escape.py\\extra"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                safe_path(self.root, name, test_only=True)

    def test_rejects_symlinked_files_and_directories(self):
        target = self.root / "backend/tests"
        target.parent.mkdir()
        target.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            safe_path(self.root, "backend/tests/test_escape.py", test_only=True)

    def test_rejects_secret_and_generated_file_reads(self):
        for name in ("backend/.env", "backend/.venv/secrets.py", "frontend/src/.secret.ts",
                     "frontend/src/node_modules/package/index.ts", "backend/requirements.txt"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                safe_path(self.root, name)

    def test_validates_entire_proposal_before_writing(self):
        self.proposal["head"] = "a" * 40
        self.proposal["files"].append({"path": "backend/app/main.py", "content": "bad"})
        with patch("agent.git", return_value="a" * 40), self.assertRaises(ValueError):
            apply(self.root, self.proposal, "a" * 40)
        self.assertFalse((self.root / "backend/tests/test_missing.py").exists())

    def test_rejects_duplicate_files_and_excessive_output(self):
        self.proposal["files"] *= 2
        with self.assertRaises(ValueError):
            validate_proposal(self.root, self.proposal)
        self.proposal["files"] = [{"path": "frontend/src/App.test.tsx", "content": "x" * 40001}]
        with self.assertRaises(ValueError):
            validate_proposal(self.root, self.proposal)

    def test_skip_requires_reason_and_no_files(self):
        self.proposal["decision"] = "skip"
        with self.assertRaises(ValueError):
            validate_proposal(self.root, self.proposal)

        self.proposal["files"] = []
        self.assertEqual(validate_proposal(self.root, self.proposal), [])
        self.proposal["reason"] = ""
        with self.assertRaises(ValueError):
            validate_proposal(self.root, self.proposal)

    def test_normalizes_final_newline_for_a_valid_patch(self):
        self.proposal["files"][0]["content"] = "def test_value():\n    assert 2 + 2 == 4"
        files = validate_proposal(self.root, self.proposal)
        self.assertTrue(files[0][1].endswith("\n"))

    def test_proposal_cannot_be_applied_to_different_commit(self):
        self.proposal["head"] = "a" * 40
        with patch("agent.git", return_value="b" * 40), self.assertRaises(ValueError):
            apply(self.root, self.proposal, "a" * 40)

    def test_tool_loop_reads_source_and_loads_both_language_skills(self):
        path = self.root / "backend/app/example.py"
        path.parent.mkdir(parents=True)
        path.write_text("def value():\n    return 7\n")
        responses = [
            {"output": [{"type": "function_call", "name": "read_file", "call_id": "read-1",
                         "arguments": json.dumps({"path": "backend/app/example.py"})}]},
            {"output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(self.proposal)}]}]},
        ]
        with patch("agent.git", return_value="backend/app/example.py"), \
             patch("agent.request_model", side_effect=responses) as model:
            proposal, skills, reads = generate(self.root, ["backend/app/example.py", "frontend/src/App.tsx"], "diff", "model")
        self.assertEqual(proposal, self.proposal)
        self.assertEqual(set(skills), {"analyze-changes", "verify-tests", "backend-tests", "frontend-tests"})
        self.assertEqual(reads, ["backend/app/example.py"])
        self.assertIn("return 7", model.call_args.args[0][-2]["output"])

    def test_unknown_tools_are_never_executed(self):
        response = {"output": [{"type": "function_call", "name": "shell", "arguments": "{}"}]}
        with patch("agent.git", return_value=""), patch("agent.request_model", return_value=response):
            with self.assertRaises(ValueError):
                generate(self.root, [], "diff", "model")

    def test_model_budget_is_bounded(self):
        response = {"output": [{"type": "function_call", "name": "read_file", "call_id": "read-1",
                                "arguments": json.dumps({"path": "backend/app/missing.py"})}]}
        with patch("agent.git", return_value=""), patch("agent.request_model", return_value=response) as model:
            with self.assertRaisesRegex(ValueError, "turn budget"):
                generate(self.root, [], "diff", "model")
        self.assertEqual(model.call_count, 8)

    def test_documentation_change_skips_model_in_real_git_repository(self):
        def git(*args):
            return subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True, text=True).stdout.strip()

        git("init")
        git("config", "user.email", "agent-test@example.com")
        git("config", "user.name", "Agent Test")
        (self.root / "README.md").write_text("Initial\n")
        git("add", ".")
        git("commit", "-m", "Initial")
        base = git("rev-parse", "HEAD")
        (self.root / "README.md").write_text("Updated\n")
        git("commit", "-am", "Update documentation")
        head = git("rev-parse", "HEAD")
        output = self.root / "output"
        with patch("agent.request_model") as model:
            proposal = prepare(self.root, base, head, output, "model")
        model.assert_not_called()
        self.assertEqual(proposal["decision"], "skip")
        self.assertEqual((output / "tests.patch").read_text(), "")

    def test_proposes_applies_and_executes_tests_for_a_real_change(self):
        def git(*args):
            return subprocess.run(
                ["git", "-C", str(self.root), *args], check=True,
                capture_output=True, text=True,
            ).stdout.strip()

        git("init")
        git("config", "user.email", "agent-test@example.com")
        git("config", "user.name", "Agent Test")
        source = self.root / "backend/app/calculations.py"
        source.parent.mkdir(parents=True)
        source.write_text("def double(value):\n    return value\n")
        git("add", ".")
        git("commit", "-m", "Initial")
        base = git("rev-parse", "HEAD")
        source.write_text("def double(value):\n    return value * 2\n")
        git("commit", "-am", "Double values")
        head = git("rev-parse", "HEAD")
        proposal = {
            "decision": "propose", "reason": "Cover zero and negative values.",
            "files": [{"path": "backend/tests/test_calculations.py", "content": (
                "import unittest\nfrom app.calculations import double\n\n"
                "class DoubleTests(unittest.TestCase):\n"
                "    def test_negative(self):\n        self.assertEqual(double(-2), -4)\n"
                "    def test_zero(self):\n        self.assertEqual(double(0), 0)\n"
            )}],
        }
        responses = [
            {"output": [{"type": "function_call", "name": "read_file", "call_id": "source",
                         "arguments": json.dumps({"path": "backend/app/calculations.py"})}]},
            {"output": [{"type": "message", "content": [
                {"type": "output_text", "text": json.dumps(proposal)},
            ]}]},
        ]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            with patch.dict("os.environ", {"TEST_AGENT_API_KEY": "offline-fixture"}), \
                 patch("agent.request_model", side_effect=responses):
                saved = prepare(self.root, base, head, output, "offline-fixture")
            git("apply", "--check", str(output / "tests.patch"))
            apply(self.root, saved, head)
            result = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                cwd=self.root / "backend", capture_output=True, text=True, timeout=15,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Ran 2 tests", result.stderr)
        self.assertEqual(saved["skills"], ["analyze-changes", "verify-tests", "backend-tests"])


if __name__ == "__main__":
    unittest.main()
