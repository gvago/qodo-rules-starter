#!/usr/bin/env python3
"""Fail if skills/security-review/SKILL.md drifts from pr_compliance_checklist.yaml.

Every rule title, objective, success_criteria, and failure_criteria in the
checklist must appear verbatim (modulo line wrapping) in the skill.
Run from the repository root: python3 tools/check_skill_sync.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKLIST = ROOT / "pr_compliance_checklist.yaml"
SKILL = ROOT / "skills" / "security-review" / "SKILL.md"


def norm(text: str) -> str:
    return " ".join(text.split())


def checklist_blocks() -> list[tuple[str, str]]:
    """(label, text) for every title and folded criteria block in the YAML."""
    # ponytail: indentation-based scrape, not a YAML parser; enough for this
    # file's fixed shape. Swap in PyYAML if the checklist format ever changes.
    blocks, lines = [], CHECKLIST.read_text().splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r'\s*-\s*title:\s*"(.+)"', line)
        if m:
            blocks.append(("title", m.group(1)))
        m = re.match(r"\s*(objective|success_criteria|failure_criteria):\s*>", line)
        if m:
            key, body = m.group(1), []
            i += 1
            while i < len(lines) and (lines[i].startswith("      ") or not lines[i].strip()):
                body.append(lines[i])
                i += 1
            blocks.append((key, " ".join(body)))
            continue
        i += 1
    return blocks


def main() -> int:
    skill = norm(SKILL.read_text())
    missing = [
        (label, text)
        for label, text in checklist_blocks()
        if norm(text) not in skill
    ]
    for label, text in missing:
        print(f"MISSING {label}: {norm(text)[:100]}...")
    if missing:
        print(f"\n{len(missing)} checklist block(s) not found verbatim in {SKILL.relative_to(ROOT)}")
        return 1
    print(f"OK: skill mirrors all {len(checklist_blocks())} checklist blocks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
