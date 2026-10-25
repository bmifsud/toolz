#!/usr/bin/env python3
"""
doc_coverage_engine.py
Self-healing documentation-to-test coverage engine for toolz.
Automatically parses repository documentation, discovers documented scripts,
flags, and components, maps them against test suites, and updates coverage reports.
"""

import os
import re
import sys
import glob
from datetime import datetime, timezone

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

DOC_PATHS = [
    os.path.join(REPO_ROOT, "README.md"),
    os.path.join(REPO_ROOT, "backup", "README.md"),
    os.path.join(REPO_ROOT, "android-chrome-subscriptions", "README.md"),
] + glob.glob(os.path.join(REPO_ROOT, "docs", "*.md"))

TEST_PATHS = glob.glob(os.path.join(REPO_ROOT, "tests", "*.sh")) + [
    os.path.join(REPO_ROOT, "android-chrome-subscriptions", "test_suite.py")
]

COVERAGE_DOC_PATH = os.path.join(REPO_ROOT, "docs", "TEST_COVERAGE.md")

def extract_docs_metadata():
    docs_text = ""
    for p in DOC_PATHS:
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8") as f:
                docs_text += "\n" + f.read()

    script_matches = set(re.findall(r'[\w\.-]+(?:/[\w\.-]+)*\.(?:sh|py)', docs_text))
    repo_scripts = set()
    for s in script_matches:
        candidate = os.path.normpath(os.path.join(REPO_ROOT, s))
        if os.path.isfile(candidate) and not candidate.startswith(os.path.join(REPO_ROOT, "tests")):
            rel = os.path.relpath(candidate, REPO_ROOT)
            repo_scripts.add(rel)

    flags = set(re.findall(r'(--[a-zA-Z0-9_-]+)', docs_text))
    ignored_flags = {"--", "---", "--configure", "--files-only", "--min-age", "--progress", "--batch", "--yes", "--decrypt", "--symmetric", "--cipher-algo"}
    filtered_flags = {f for f in flags if f not in ignored_flags}
    filtered_flags.add("--help")

    components = [
        ("Multi-Agent Tmux Workspace (1, 2, 3 Panes)", r"start-debian|launch-ai-tmux"),
        ("Portrait / Landscape Orientation Geometry", r"portrait|landscape|even-vertical|even-horizontal"),
        ("Android Soft Keyboard Resize Handling", r"keyboard|MIN_LANDSCAPE_COLS"),
        ("Hot SQLite Online Backup & Encryption", r"sqlite|WAL|AES256|gpg"),
        ("Cline CLI State & Secrets Restoration", r"globalState|secrets\.json|restore"),
        ("Google Drive Cloud Sync & Remote Restore", r"gdrive|rclone"),
        ("Android Chrome Subscription Provider Sync", r"auto_sync_omniroute|subscriptions"),
    ]

    return {
        "scripts": sorted(repo_scripts),
        "flags": sorted(filtered_flags),
        "components": components,
    }
def analyze_test_coverage(meta):
    tests_text = ""
    for tp in TEST_PATHS:
        if os.path.isfile(tp):
            with open(tp, "r", encoding="utf-8") as f:
                tests_text += "\n" + f.read()

    script_coverage = {}
    for s in meta["scripts"]:
        basename = os.path.basename(s)
        covered = (basename in tests_text) or (s in tests_text)
        script_coverage[s] = covered

    flag_coverage = {}
    for fl in meta["flags"]:
        covered = fl in tests_text
        flag_coverage[fl] = covered

    comp_coverage = {}
    for name, pattern in meta["components"]:
        covered = bool(re.search(pattern, tests_text, re.IGNORECASE))
        comp_coverage[name] = covered

    total_items = len(script_coverage) + len(flag_coverage) + len(comp_coverage)
    covered_items = (
        sum(1 for v in script_coverage.values() if v)
        + sum(1 for v in flag_coverage.values() if v)
        + sum(1 for v in comp_coverage.values() if v)
    )

    percent = round((covered_items / total_items * 100), 1) if total_items > 0 else 100.0

    return {
        "scripts": script_coverage,
        "flags": flag_coverage,
        "components": comp_coverage,
        "total_items": total_items,
        "covered_items": covered_items,
        "percentage": percent,
    }

def generate_coverage_markdown(meta, cov):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Automated Documentation & Feature Test Coverage Report",
        "",
        "> **Self-Healing Status**: Active  ",
        f"> **Last Generated**: `{timestamp}`  ",
        f"> **Overall Documentation Coverage**: **`{cov['percentage']}%`** ({cov['covered_items']}/{cov['total_items']} items covered)",
        "",
        "This report dynamically updates whenever documentation or test suites in the repository are modified.",
        "",
        "## 1. Documented Scripts Coverage",
        "",
        "| Documented Script | In Repository | Automated Test Coverage | Status |",
        "| :--- | :---: | :---: | :---: |",
    ]

    for s, is_cov in cov["scripts"].items():
        status = "PASSED" if is_cov else "MISSING TEST"
        icon = "[PASS]" if is_cov else "[WARN]"
        lines.append(f"| `{s}` | Yes | `{icon}` | {status} |")

    lines.extend([
        "",
        "## 2. Documented CLI Options & Flags",
        "",
        "| Documented CLI Flag | Tested in Test Suite | Status |",
        "| :--- | :---: | :---: |",
    ])

    for f, is_cov in cov["flags"].items():
        status = "PASSED" if is_cov else "MISSING TEST"
        icon = "[PASS]" if is_cov else "[WARN]"
        lines.append(f"| `{f}` | `{icon}` | {status} |")

    lines.extend([
        "",
        "## 3. Core Architectural Components Coverage",
        "",
        "| Component / Feature | Tested in Test Suite | Status |",
        "| :--- | :---: | :---: |",
    ])

    for c, is_cov in cov["components"].items():
        status = "PASSED" if is_cov else "MISSING TEST"
        icon = "[PASS]" if is_cov else "[WARN]"
        lines.append(f"| {c} | `{icon}` | {status} |")

    lines.extend([
        "",
        "---",
        "### Self-Healing Guarantee",
        "When any new document is added or updated in `docs/` or `README.md`, running `./tests/run-all-tests.sh` automatically re-parses documentation, discovers new referenced scripts/flags, computes updated metrics, and self-heals this coverage document without manual maintenance.",
    ])

    return "\n".join(lines) + "\n"

def sync_readme_coverage(cov):
    readme_path = os.path.join(REPO_ROOT, "README.md")
    if not os.path.isfile(readme_path):
        return

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    section = (
        f"<!-- TEST_COVERAGE_START -->\n"
        f"### Automated Test & Documentation Coverage: **{cov['percentage']}%** ({cov['covered_items']}/{cov['total_items']} items verified)\n"
        f"Full report dynamically self-heals on doc updates: see [docs/TEST_COVERAGE.md](docs/TEST_COVERAGE.md).\n"
        f"<!-- TEST_COVERAGE_END -->"
    )

    if "<!-- TEST_COVERAGE_START -->" in content and "<!-- TEST_COVERAGE_END -->" in content:
        updated = re.sub(
            r"<!-- TEST_COVERAGE_START -->[\s\S]*?<!-- TEST_COVERAGE_END -->",
            section,
            content
        )
    else:
        updated = content + "\n\n" + section + "\n"

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(updated)

def main():
    meta = extract_docs_metadata()
    cov = analyze_test_coverage(meta)
    md = generate_coverage_markdown(meta, cov)

    os.makedirs(os.path.dirname(COVERAGE_DOC_PATH), exist_ok=True)
    with open(COVERAGE_DOC_PATH, "w", encoding="utf-8") as f:
        f.write(md)

    sync_readme_coverage(cov)

    print(f"[doc_coverage_engine] Documentation coverage generated: {cov['percentage']}% ({cov['covered_items']}/{cov['total_items']})")
    print(f"[doc_coverage_engine] Output written to {COVERAGE_DOC_PATH}")

    if cov["percentage"] < 80.0:
        print(f"[doc_coverage_engine] Error: Documentation coverage below threshold (80%): {cov['percentage']}%", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()

