import re
from pathlib import Path, PurePosixPath


def safe_path(root: Path, name: str, *, test_only: bool = False) -> Path:
    parts = PurePosixPath(name).parts
    if not parts or name != PurePosixPath(name).as_posix() or ".." in parts or "\\" in name:
        raise ValueError("Invalid relative path")
    frontend = name.startswith("frontend/src/")
    backend = name.startswith("backend/tests/" if test_only else "backend/")
    if not (frontend or backend):
        raise ValueError("Path outside application directories")
    if any(part.startswith(".") or part in {"node_modules", "coverage", "__pycache__"} for part in parts):
        raise ValueError("Hidden files and generated directories are not allowed")
    path = root / name
    for parent in [path, *path.parents]:
        if parent == root:
            break
        if parent.is_symlink():
            raise ValueError("Symlinks are not allowed")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Path escapes checkout")
    if test_only:
        valid = (frontend and re.fullmatch(r".+\.test\.tsx?", name)) or (
            backend and re.fullmatch(r"test_[A-Za-z0-9_]+\.py", path.name)
        )
        if not valid:
            raise ValueError("Only unit test files may be changed")
    elif path.suffix not in {".py", ".ts", ".tsx"}:
        raise ValueError("Only source and test files may be read")
    return path


def validate_proposal(root: Path, proposal: dict) -> list[tuple[Path, str]]:
    if proposal.get("decision") not in {"skip", "propose"}:
        raise ValueError("Invalid decision")
    if not isinstance(proposal.get("reason"), str) or not proposal["reason"].strip():
        raise ValueError("A decision requires a reason")
    files = proposal.get("files")
    if not isinstance(files, list) or len(files) > 10:
        raise ValueError("Expected at most ten test files")
    if (proposal["decision"] == "skip") != (len(files) == 0):
        raise ValueError("Decision and test files disagree")
    result = []
    seen = set()
    for item in files:
        path = safe_path(root, item["path"], test_only=True)
        content = item["content"]
        if not isinstance(content, str) or not content.strip() or len(content.encode()) > 40000:
            raise ValueError("Invalid test content or file too large")
        if path in seen:
            raise ValueError("Duplicate test path")
        seen.add(path)
        result.append((path, content if content.endswith("\n") else content + "\n"))
    return result
