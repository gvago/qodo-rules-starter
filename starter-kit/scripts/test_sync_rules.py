#!/usr/bin/env python3
"""Small checks for sync_rules.py. Run: python3 scripts/test_sync_rules.py"""

import importlib.util
import pathlib
import tempfile
from unittest import mock

SCRIPT = pathlib.Path(__file__).with_name("sync_rules.py")
spec = importlib.util.spec_from_file_location("sync_rules", SCRIPT)
assert spec and spec.loader
sync_rules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_rules)

VALID = """\
name: "Require parameterized queries"
category: Security
severity: error
content: "Use parameterized queries when untrusted input reaches a database query."
good_examples: "cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))"
bad_examples: "cursor.execute(f'SELECT * FROM users WHERE id = {user_id}')"
"""

with tempfile.TemporaryDirectory() as tmp:
    path = pathlib.Path(tmp) / "parameterized-queries.yaml"
    path.write_text(VALID)
    rule = sync_rules.load_rule(path)
    assert rule == {
        "name": "Require parameterized queries",
        "category": "Security",
        "severity": "error",
        "content": "Use parameterized queries when untrusted input reaches a database query.",
        "good_examples": "cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))",
        "bad_examples": "cursor.execute(f'SELECT * FROM users WHERE id = {user_id}')",
    }

    path.write_text(VALID.replace("Require parameterized queries", "{{RULE_NAME}}"))
    try:
        sync_rules.load_rule(path)
    except ValueError as exc:
        assert "placeholder" in str(exc)
    else:
        raise AssertionError("template placeholders must be rejected")

    path.write_text(VALID.replace('"Require parameterized queries"', "[invalid]"))
    try:
        sync_rules.load_rule(path)
    except ValueError as exc:
        assert "must be strings" in str(exc)
    else:
        raise AssertionError("non-string rule fields must be rejected")

    path.write_text(VALID.replace("Require parameterized queries", "-unsafe-name"))
    try:
        sync_rules.load_rule(path)
    except ValueError as exc:
        assert "must not start" in str(exc)
    else:
        raise AssertionError("CLI-like rule values must be rejected")

assert sync_rules.parse_scopes("/acme/security-test/") == [
    "/acme/security-test/"
]
assert sync_rules.parse_scopes("/acme/") == ["/acme/"]

try:
    sync_rules.parse_scopes("")
except ValueError:
    pass
else:
    raise AssertionError("empty scope must be rejected")

args = sync_rules.rule_args(
    {
        "category": "Security",
        "severity": "warning",
        "content": "Check the control.",
        "good_examples": "safe()",
        "bad_examples": "unsafe()",
    },
    ["/acme/security-test/"],
)
assert args[-2:] == ["--scopes", "/acme/security-test/"]

local = {
    "category": "Security",
    "severity": "warning",
    "content": "Check the control.",
    "good_examples": "safe()",
    "bad_examples": "unsafe()",
}
remote = {
    "category": "Security",
    "severity": "warning",
    "content": "Check the control.",
    "goodExamples": "safe()",
    "badExamples": "unsafe()",
    "scopes": ["/acme/security-test/"],
    "state": "active",
}
assert sync_rules.is_unchanged(local, remote, ["/acme/security-test/"])
assert not sync_rules.is_unchanged(
    local, {**remote, "severity": "error"}, ["/acme/security-test/"]
)

remote_with_null_scopes = {**remote, "scopes": None}
assert not sync_rules.is_unchanged(
    local, remote_with_null_scopes, ["/acme/security-test/"]
)
assert not sync_rules.is_unchanged(
    local, {**remote, "content": None}, ["/acme/security-test/"]
)

pages = [
    {"page": 1, "totalCount": 101, "rules": []},
    {"page": 2, "totalCount": 101, "rules": [{"name": "wanted", "ruleId": 7}]},
]
with mock.patch.object(sync_rules, "run_qodo", side_effect=pages) as run:
    assert sync_rules.find_existing("wanted")["ruleId"] == 7
    assert run.call_count == 2

try:
    sync_rules.require_active({"state": "pending"}, "test rule")
except RuntimeError as exc:
    assert "expected 'active'" in str(exc)
else:
    raise AssertionError("non-active writes must fail publication")

with tempfile.TemporaryDirectory() as tmp:
    with mock.patch.object(sync_rules, "SCOPES_FILE", pathlib.Path(tmp) / "scopes.txt"):
        sync_rules.SCOPES_FILE.write_text("/acme/security-test/\n")
        assert sync_rules.load_scopes() == ["/acme/security-test/"]

        sync_rules.SCOPES_FILE.write_text("{{QODO_RULE_SCOPE}}\n")
        try:
            sync_rules.load_scopes()
        except ValueError as exc:
            assert "placeholder" in str(exc)
        else:
            raise AssertionError("scope placeholders must be rejected")

print("all checks passed")
