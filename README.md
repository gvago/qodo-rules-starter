# Qodo repo-scoped security rules: starter

A minimal, self-contained example of enforcing an organization's security rules
on every pull request, **without** using a central rules platform.

The rules live in one file at the repository root:

```
pr_compliance_checklist.yaml
```

Qodo reads that file automatically on every PR review. There is nothing to
configure centrally, and nothing outside this repository to maintain.

## Contents

| Path | What it is |
|---|---|
| `pr_compliance_checklist.yaml` | The five security rules, enforced on every PR |
| `app/loan_service.py` | Clean baseline service (passes the rules) |
| `app/payments.py` | **Deliberately violating** code, used to demonstrate the findings |
| `docs/audit-log-queries.md` | How to find the enforcement events in your logs |
| `docs/central-rules-repo.md` | Applying one rule set across many repositories |
| `docs/security-review-standards-as-code.md` | Guided workflow for managing Review Standards in Git |
| `tools/sync_rule_scopes.py` | Keeps that mapping current as repositories are added |
| `starter-kit/` | Copyable YAML, CI, Qodo CLI sync, checks, and guided setup skill |

## Guided setup: start here

Do not work through the sections below by hand unless you want to. Use the
included skill for the easy path.

1. Clone this repository and open it in Codex, Claude Code, Cursor, or another
   skill-compatible coding agent.
2. Install or copy
   [`starter-kit/skills/qodo-security-standards-setup/`](starter-kit/skills/qodo-security-standards-setup/)
   into that agent's project skill directory. For example, with Claude Code:

   ```bash
   mkdir -p .claude/skills
   cp -R starter-kit/skills/qodo-security-standards-setup .claude/skills/
   ```

3. Start a fresh agent session, then say:

   > Set up Qodo Security Review Standards for my repositories.

The agent asks for an existing standards repository or offers to create one,
then guides Qodo setup, repository-specific Security Agent activation, starter
installation, the Qodo-reviewed pull request, publication, walkthrough, and
first real rule.

If your agent does not discover it automatically, explicitly ask it to run
`qodo-security-standards-setup`.

## Manual reference

1. Clone this repository into your environment.
2. Copy `pr_compliance_checklist.yaml` to the root of any repository you want
   the rules enforced on. That is the entire installation step.
3. Open a pull request that changes code. The Qodo review comment on the PR
   lists every rule violation, each one carrying its compliance ID, the
   evidence, and a link back to the rule.

To reproduce the demonstration in this repository, open a pull request that
adds `app/payments.py` to the baseline. That file violates four of the five
rules on purpose.

## The rules

| ID | Rule |
|---|---|
| SEC-1 | Authentication & authorization on sensitive actions |
| SEC-2 | Injection prevention (SQL, OS, template, LDAP, XPath, HTML, JS) |
| SEC-3 | SSRF prevention |
| SEC-4 | No test/debug/mock code reachable in production |
| SEC-5 | No hardcoded secrets, tokens, keys, or connection strings |

Edit the YAML to change wording, add rules, or remove them. Each entry needs a
`title`, `compliance_label: true`, and the `objective` / `success_criteria` /
`failure_criteria` fields.

## Where the developer sees it

The findings are posted on the pull request itself, so the developer who opened
the PR sees the rule, why it failed, and the exact lines, before merge. The same
findings are recorded in the platform and in the audit log, so a security team
can review enforcement independently of the developer's own thread.

## Applying the rules to more than one repository

Copying the file into every repository works, and for a handful of repositories
it is the right answer. Beyond that, keep the rules in one place and point them
at the repositories they govern.

[`docs/central-rules-repo.md`](docs/central-rules-repo.md) covers that:

- a central rules repository, with one file per language or concern
- mapping each rule set to its target repositories, in the portal or with the
  `qodo` CLI
- keeping the mapping current as repositories are added, with
  [`tools/sync_rule_scopes.py`](tools/sync_rule_scopes.py) on a schedule
- which mechanism suits which class of rule

## Standards-as-code workflow

[`docs/security-review-standards-as-code.md`](docs/security-review-standards-as-code.md)
shows the normal Git-first flow: write a standard, let Qodo review it in the
pull request, resolve useful findings with the Qodo resolver skill, merge, and
publish it with the intended scope.

Use the guided setup skill above to walk through the setup end to end. The
starter also includes placeholder YAML, a reviewed-branch Qodo CLI sync, and an
optional local helper check. Begin with one non-production repository so the
team can see the workflow, then move directly to normal repository or
Git-organization scope.

## Audit trail

Every enforcement event is logged.
[`docs/audit-log-queries.md`](docs/audit-log-queries.md) has the exact queries
for the two questions security teams ask most:

- Which pull requests were merged while rule violations were still open?
- Who changed a rule, and when?

## References

- Rule enforcement without a rules platform:
  https://docs.qodo.ai/governance/rule-enforcement/without-rule-system
- Custom compliance file format:
  https://docs.qodo.ai/v1/features/custom-compliance
