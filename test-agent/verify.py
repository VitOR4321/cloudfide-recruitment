import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def verify(root: Path, output: Path, baseline: Path | None = None) -> int:
    output.mkdir(parents=True, exist_ok=True)
    for name in ("backend", "frontend"):
        for filename in ("results.xml", "coverage.json", "coverage-summary.json"):
            (root / name / "coverage" / filename).unlink(missing_ok=True)
    commands = [
        ("agent", [sys.executable, "-m", "unittest", "discover", "-s", str(Path(__file__).parent / "tests")], root),
        ("backend", [sys.executable, "-m", "pytest", "--cov=app", "--cov-report=term-missing",
                     "--cov-report=json", "--junitxml=coverage/results.xml"], root / "backend"),
        ("frontend", ["npm", "run", "test:coverage", "--", "--reporter=default",
                      "--reporter=junit", "--outputFile=coverage/results.xml"], root / "frontend"),
        ("build", ["npm", "run", "build"], root / "frontend"),
    ]
    results = []
    environment = os.environ.copy()
    for name in ("TEST_AGENT_API_KEY", "OPENAI_API_KEY", "GH_TOKEN", "GITHUB_TOKEN"):
        environment.pop(name, None)
    for name, command, cwd in commands:
        try:
            completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=300, env=environment)
            code, log = completed.returncode, completed.stdout + completed.stderr
        except subprocess.TimeoutExpired:
            code, log = 124, "Command exceeded five-minute limit.\n"
        (output / f"{name}.log").write_text(log)
        print(f"{name}: exit {code}", flush=True)
        results.append({"name": name, "command": command, "exit_code": code})
    summary = {"checks": results, "coverage": {}, "tests": {}}
    for name in ("backend", "frontend"):
        directory = root / name / "coverage"
        coverage = directory / ("coverage.json" if name == "backend" else "coverage-summary.json")
        if coverage.exists():
            data = json.loads(coverage.read_text())
            summary["coverage"][name] = data["totals"] if name == "backend" else data["total"]
        junit = directory / "results.xml"
        if junit.exists():
            suites = ET.parse(junit).getroot()
            nodes = [suites] if suites.tag == "testsuite" else list(suites.findall("testsuite"))
            summary["tests"][name] = {
                key: sum(int(node.get(key, 0)) for node in nodes)
                for key in ("tests", "failures", "errors", "skipped")
            }
    (output / "results.json").write_text(json.dumps(summary, indent=2) + "\n")
    report = ["## Test verification", "", "| Check | Exit code |", "| --- | --- |"]
    report.extend(f"| {result['name']} | {result['exit_code']} |" for result in results)
    report += ["", "| Suite | Tests | Failures | Errors | Skipped |", "| --- | --- | --- | --- | --- |"]
    for name, counts in summary["tests"].items():
        report.append(f"| {name} | {counts['tests']} | {counts['failures']} | {counts['errors']} | {counts['skipped']} |")
    previous = json.loads(baseline.read_text())["coverage"] if baseline else {}
    report += ["", "| Line coverage | Baseline | Current |", "| --- | --- | --- |"]
    for name, coverage in summary["coverage"].items():
        def percentage(data):
            if name == "backend":
                return 100 * data["covered_lines"] / data["num_statements"]
            return data["lines"]["pct"]
        before = f"{percentage(previous[name]):.2f}%" if name in previous else "—"
        report.append(f"| {name} | {before} | {percentage(coverage):.2f}% |")
    report += ["", "Full coverage and command output are available in the artifacts."]
    text = "\n".join(report) + "\n"
    (output / "summary.md").write_text(text)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as stream:
            stream.write(text)
    counts_valid = all(
        counts.get("tests", 0) > counts.get("skipped", 0)
        and counts.get("failures", 0) == 0
        and counts.get("errors", 0) == 0
        for counts in (summary["tests"].get(name, {}) for name in ("backend", "frontend"))
    )
    return 0 if counts_valid and all(result["exit_code"] == 0 for result in results) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    raise SystemExit(verify(args.root.resolve(), args.output.resolve(), args.baseline))
