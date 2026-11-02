"""Offline ADLC structure and local Markdown link checks; never executes linked content."""
from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ("AGENTS.md", "docs/adlc/README.md", "docs/adlc/status.md",
            ".github/pull_request_template.md", ".github/ISSUE_TEMPLATE/adlc-change.md")

def check(root):
    errors = []
    for name in REQUIRED:
        if not (root / name).is_file():
            errors.append(f"missing {name}")
    for path in root.rglob("*.md"):
        if any(p.startswith(".") and p != ".github" for p in path.relative_to(root).parts):
            continue
        source = re.sub(r"```.*?```", "", path.read_text(), flags=re.S)
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", source):
            target = target.strip().split("#", 1)[0]
            if not target or re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                continue
            resolved = (path.parent / unquote(target)).resolve()
            if not resolved.is_relative_to(root.resolve()) or not resolved.exists():
                errors.append(f"{path.relative_to(root)}: invalid local link {target}")
    for directory in (root / "docs/adlc/changes").glob("*"):
        if directory.is_dir():
            for name in ("intent.md", "evidence.md"):
                if not (directory / name).is_file():
                    errors.append(f"{directory.name}: missing {name}")
    return errors

if __name__ == "__main__":
    failures = check(ROOT)
    print("\n".join(failures) if failures else "PASS: ADLC structure and local links")
    sys.exit(bool(failures))
