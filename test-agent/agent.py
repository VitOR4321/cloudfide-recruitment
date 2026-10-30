import argparse
import difflib
import html
import json
import os
import re
import subprocess
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from safety import safe_path, validate_proposal

HERE = Path(__file__).resolve().parent
SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["skip", "propose"]},
        "reason": {"type": "string"},
        "files": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["decision", "reason", "files"],
    "additionalProperties": False,
}
READ_TOOL = {
    "type": "function", "name": "read_file",
    "description": "Read an application source or unit test file. Never executes code.",
    "strict": True,
    "parameters": {
        "type": "object", "properties": {"path": {"type": "string"}},
        "required": ["path"], "additionalProperties": False,
    },
}


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True,
        timeout=30,
    ).stdout.strip()


def source_file(name: str) -> bool:
    return (name.startswith("backend/app/") and name.endswith(".py")) or (
        name.startswith("frontend/src/") and name.endswith((".ts", ".tsx"))
        and ".test." not in name and ".stories." not in name
        and not name.startswith("frontend/src/test/")
    )


def request_model(messages: list, instructions: str, model: str) -> dict:
    body = {
        "model": model, "instructions": instructions, "input": messages,
        "tools": [READ_TOOL], "max_output_tokens": 12000, "store": False,
        "text": {"format": {"type": "json_schema", "name": "test_proposal",
                            "strict": True, "schema": SCHEMA}},
    }
    request = Request(
        "https://api.openai.com/v1/responses", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {os.environ['TEST_AGENT_API_KEY']}",
                 "Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=120) as response:
            result = json.load(response)
    except HTTPError as error:
        raise RuntimeError(f"Model API failed with HTTP {error.code}") from None
    if result.get("status") != "completed":
        raise RuntimeError("Model response did not complete")
    return result


def generate(root: Path, changed: list[str], diff: str, model: str, baseline: dict | None = None) -> tuple[dict, list[str], list[str]]:
    skills = ["analyze-changes", "verify-tests"]
    if any(name.startswith("frontend/") for name in changed):
        skills.append("frontend-tests")
    if any(name.startswith("backend/") for name in changed):
        skills.append("backend-tests")
    instructions = (HERE / "AGENT.md").read_text()
    for skill in skills:
        instructions += "\n\n" + (HERE / "skills" / skill / "SKILL.md").read_text()
    available = sorted(
        name for name in git(root, "ls-files").splitlines()
        if name.startswith(("frontend/src/", "backend/app/", "backend/tests/"))
        and name.endswith((".ts", ".tsx", ".py"))
    )
    messages = [{"role": "user", "content": json.dumps({
        "changed_files": changed, "available_files": available, "untrusted_diff": diff,
        "untrusted_baseline": baseline,
    })}]
    reads = []
    for _ in range(8):
        response = request_model(messages, instructions, model)
        output = response["output"]
        messages.extend(output)
        calls = [item for item in output if item["type"] == "function_call"]
        if not calls:
            texts = [part["text"] for item in output if item["type"] == "message"
                     for part in item["content"] if part["type"] == "output_text"]
            if len(texts) != 1:
                raise ValueError("Expected one structured proposal")
            proposal = json.loads(texts[0])
            validate_proposal(root, proposal)
            return proposal, skills, reads
        for call in calls:
            if call["name"] != "read_file" or len(reads) >= 24:
                raise ValueError("Tool budget exceeded or unknown tool")
            name = json.loads(call["arguments"])["path"]
            reads.append(name)
            try:
                path = safe_path(root, name)
                if path.stat().st_size > 40000:
                    raise ValueError("File exceeds read limit")
                value = path.read_text()
            except (ValueError, OSError) as error:
                value = f"Cannot read file: {type(error).__name__}"
            messages.append({"type": "function_call_output", "call_id": call["call_id"],
                             "output": value})
    raise ValueError("Model turn budget exceeded")


def prepare(root: Path, base: str, head: str, output: Path, model: str, baseline: Path | None = None) -> dict:
    for sha in (base, head):
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise ValueError("Expected full commit SHAs")
    if git(root, "rev-parse", "HEAD") != head:
        raise ValueError("Checkout does not match PR head")
    changed = git(root, "diff", "--name-only", "--diff-filter=ACMR", f"{base}...{head}").splitlines()
    changed = [name for name in changed if source_file(name)]
    proposal = {"decision": "skip", "reason": "No changed application source files.", "files": []}
    skills, reads = [], []
    if changed:
        if not os.environ.get("TEST_AGENT_API_KEY"):
            raise RuntimeError("TEST_AGENT_API_KEY is required for source changes")
        diff = git(root, "diff", "--no-ext-diff", "--no-textconv", f"{base}...{head}", "--", *changed)
        if len(diff.encode()) > 120000 or len(changed) > 40:
            raise ValueError("PR exceeds agent limits; split the change")
        evidence = None
        if baseline:
            evidence = {"results": json.loads((baseline / "results.json").read_text())}
            evidence["logs"] = {
                name: (baseline / f"{name}.log").read_text()[-12000:]
                for name in ("backend", "frontend", "build")
            }
        proposal, skills, reads = generate(root, changed, diff, model, evidence)
    proposal.update({"base": base, "head": head, "model": model,
                     "skills": skills, "reads": reads, "changed_files": changed})
    output.mkdir(parents=True, exist_ok=True)
    (output / "proposal.json").write_text(json.dumps(proposal, indent=2) + "\n")
    patch = []
    for path, content in validate_proposal(root, proposal):
        name = path.relative_to(root).as_posix()
        previous = path.read_text() if path.exists() else ""
        patch.extend(difflib.unified_diff(
            previous.splitlines(keepends=True), content.splitlines(keepends=True),
            fromfile=f"a/{name}" if path.exists() else "/dev/null", tofile=f"b/{name}",
        ))
    (output / "tests.patch").write_text("".join(patch))
    report = {key: value for key, value in proposal.items() if key != "files"}
    report["test_files"] = [item["path"] for item in proposal["files"]]
    (output / "decision.json").write_text(json.dumps(report, indent=2) + "\n")
    summary = "\n".join([
        "## Unit test agent", "", f"Decision: **{proposal['decision']}**", "",
        html.escape(proposal["reason"]), "",
        "Skills: " + ", ".join(skills), "",
        f"Proposed test files: {len(proposal['files'])}. See the proposal artifact for the patch and inspection trace.",
    ]) + "\n"
    (output / "summary.md").write_text(summary)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as stream:
            stream.write(summary)
    return proposal


def apply(root: Path, proposal: dict, expected_head: str) -> None:
    if proposal["head"] != expected_head or git(root, "rev-parse", "HEAD") != expected_head:
        raise ValueError("Proposal does not match the expected PR head")
    files = validate_proposal(root, proposal)
    if git(root, "status", "--porcelain", "--untracked-files=normal"):
        raise ValueError("Apply requires a clean checkout to preserve local work")
    for path, content in files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["prepare", "apply"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--base")
    parser.add_argument("--output", type=Path, default=Path("agent-output"))
    parser.add_argument("--proposal", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--model", default=os.getenv("TEST_AGENT_MODEL", "gpt-4.1"))
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.root.resolve(), args.base, args.head, args.output, args.model, args.baseline)
    else:
        apply(args.root.resolve(), json.loads(args.proposal.read_text()), args.head)


if __name__ == "__main__":
    main()
