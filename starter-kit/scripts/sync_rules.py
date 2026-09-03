#!/usr/bin/env python3
"""Create or update YAML Review Standards through the Qodo CLI."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = ROOT / "rules"
PLACEHOLDER = re.compile(r"\{\{[^}]+\}\}")
REQUIRED = ("name", "category", "severity", "content", "good_examples", "bad_examples")
SEVERITIES = {"error", "warning", "recommendation"}


def load_rule(path: Path) -> dict[str, str]:
    doc = yaml.safe_load(path.read_text())
    if not isinstance(doc, dict):
        raise ValueError(f"{path}: expected a YAML mapping")
    invalid = [field for field in REQUIRED if not isinstance(doc.get(field), str)]
    if invalid:
        raise ValueError(f"{path}: fields must be strings: {invalid}")
    missing = [field for field in REQUIRED if not doc[field].strip()]
    if missing:
        raise ValueError(f"{path}: missing fields: {missing}")
    rule = {field: str(doc[field]).strip() for field in REQUIRED}
    if any(PLACEHOLDER.search(value) for value in rule.values()):
        raise ValueError(f"{path}: replace every template placeholder")
    if rule["severity"] not in SEVERITIES:
        raise ValueError(f"{path}: invalid severity {rule['severity']!r}")
    return rule


def load_rules() -> list[dict[str, str]]:
    rules = [
        load_rule(path)
        for path in sorted(RULES_DIR.glob("*.yaml"))
        if not path.name.startswith("_")
    ]
    if not rules:
        raise ValueError(f"{RULES_DIR}: no rule files found")
    names = [rule["name"] for rule in rules]
    if len(names) != len(set(names)):
        raise ValueError("rule names must be unique")
    return rules


def parse_scopes(raw: str) -> list[str]:
    scopes = sorted({scope.strip() for scope in raw.split(",") if scope.strip()})
    if not scopes:
        raise ValueError("at least one Qodo rule scope is required")
    if len(scopes) > 25:
        raise ValueError("Qodo accepts at most 25 scopes per rule")
    for scope in scopes:
        if not (scope.startswith("/") and scope.endswith("/")):
            raise ValueError(f"invalid scope {scope!r}; scope paths start and end with /")
    return scopes


def qodo_bin() -> str:
    configured = os.environ.get("QODO_BIN")
    if configured:
        return configured
    fallback = Path.home() / ".qodo" / "bin" / "qodo"
    if fallback.is_file():
        return str(fallback)
    found = shutil.which("qodo")
    if found:
        return found
    raise RuntimeError("Qodo CLI not found; invoke the qodo-setup skill")


def run_qodo(*args: str) -> dict:
    try:
        proc = subprocess.run(
            [qodo_bin(), *args, "--json"], capture_output=True, text=True, timeout=120, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"qodo command timed out after {exc.timeout} seconds") from exc
    start = proc.stdout.find("{")
    if start < 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "qodo returned no JSON")
    try:
        payload, _ = json.JSONDecoder(strict=False).raw_decode(proc.stdout[start:])
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"could not parse qodo output: {exc}") from exc
    if proc.returncode != 0 or "error" in payload:
        error = payload.get("error")
        message = error.get("message") if isinstance(error, dict) else str(error or "")
        raise RuntimeError(message or proc.stderr.strip() or "qodo command failed")
    return payload


def find_existing(name: str) -> dict | None:
    matches = []
    page_number = 1
    while True:
        page = run_qodo(
            "rules",
            "list",
            "--name-contains",
            name,
            "--page",
            str(page_number),
            "--page-size",
            "100",
        )
        matches.extend(rule for rule in page.get("rules", []) if rule.get("name") == name)
        if page_number * 100 >= int(page.get("totalCount", 0)):
            break
        page_number += 1
    if len(matches) > 1:
        raise RuntimeError(f"multiple Qodo rules have the exact name {name!r}")
    return matches[0] if matches else None


def rule_args(rule: dict[str, str], scopes: list[str]) -> list[str]:
    return [
        "--category", rule["category"],
        "--severity", rule["severity"],
        "--content", rule["content"],
        "--good-examples", rule["good_examples"],
        "--bad-examples", rule["bad_examples"],
        "--scopes", ",".join(scopes),
    ]


def is_unchanged(rule: dict[str, str], existing: dict, scopes: list[str]) -> bool:
    return (
        existing.get("category") == rule["category"]
        and existing.get("severity") == rule["severity"]
        and existing.get("content", "").strip() == rule["content"]
        and existing.get("goodExamples", "").strip() == rule["good_examples"]
        and existing.get("badExamples", "").strip() == rule["bad_examples"]
        and sorted(existing.get("scopes") or []) == scopes
        and existing.get("state") == "active"
    )


def require_active(response: dict, name: str) -> None:
    if response.get("state") != "active":
        state = response.get("state", "unknown")
        raise RuntimeError(f"{name!r} returned state {state!r}; expected 'active'")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scopes", default=os.environ.get("RULE_SCOPES", ""))
    parser.add_argument("--apply", action="store_true", help="write the displayed plan to Qodo")
    args = parser.parse_args()

    try:
        rules = load_rules()
        scopes = parse_scopes(args.scopes)
        changes: list[tuple[str, dict[str, str], dict | None]] = []
        print(f"target scopes: {', '.join(scopes)}")
        for rule in rules:
            existing = find_existing(rule["name"])
            action = (
                "UNCHANGED" if existing and is_unchanged(rule, existing, scopes)
                else "UPDATE" if existing
                else "CREATE"
            )
            changes.append((action, rule, existing))
            suffix = f" (rule {existing['ruleId']})" if existing else ""
            print(f"{action:6} {rule['name']}{suffix}")

        if not args.apply:
            print("preview only; pass --apply in approved publication automation")
            return 0

        if os.environ.get("CI") != "true":
            raise ValueError("--apply is restricted to approved CI automation")

        completed = []
        for action, rule, existing in changes:
            if action == "UNCHANGED":
                continue
            try:
                if existing:
                    response = run_qodo(
                        "rules", "update",
                        "--rule-id", str(existing["ruleId"]),
                        *rule_args(rule, scopes),
                    )
                    require_active(response, rule["name"])
                    print(f"updated: {rule['name']}")
                else:
                    response = run_qodo(
                        "rules", "create",
                        "--name", rule["name"],
                        *rule_args(rule, scopes),
                    )
                    require_active(response, rule["name"])
                    print(f"created: {rule['name']}")
                completed.append(rule["name"])
            except RuntimeError as exc:
                done = ", ".join(completed) or "none"
                raise RuntimeError(
                    f"sync stopped after: {done}; failed on {rule['name']!r}: {exc}"
                ) from exc
        return 0
    except (RuntimeError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
