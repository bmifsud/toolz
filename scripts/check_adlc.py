"""Offline ADLC structure and local Markdown link checks; never executes linked content."""
from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ("AGENTS.md", "docs/adlc/README.md", "docs/adlc/status.md",
            "docs/verification.md", "docs/adlc/templates/intent.md",
            "docs/adlc/templates/evidence.md", "docs/adlc/templates/ai-components.md",
            ".github/workflows/adlc.yml", ".github/pull_request_template.md",
            ".github/ISSUE_TEMPLATE/adlc-change.md", "scripts/check_adlc.py",
            "scripts/ci_receipt.py", "tests/run-all-tests.sh",
            "tests/test_adlc.py", "tests/test_ci_receipt.py")
CHANGE_FILES = ("intent.md", "evidence.md")


def _markdown_has_content(path):
    """Reject empty records while allowing headings, lists and table entries."""
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"<!--.*?(?:-->|\Z)", "", text, flags=re.S)
    text = re.sub(r"[#>*_`|\s-]", "", text)
    return bool(text)

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
            for name in CHANGE_FILES:
                if not (directory / name).is_file():
                    errors.append(f"{directory.name}: missing {name}")
                elif not _markdown_has_content(directory / name):
                    errors.append(f"{directory.name}: empty {name}")
    return errors

if __name__ == "__main__":
    failures = check(ROOT)
    print("\n".join(failures) if failures else "PASS: ADLC structure and local links")
    sys.exit(bool(failures))
