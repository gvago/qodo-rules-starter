---
name: security-review
description: Enforce the five SEC security rules from pr_compliance_checklist.yaml on every code change, with full per-rule coverage reporting.
---

# Security review skill

You are reviewing a pull request in a repository governed by five security
rules. The authoritative wording lives in `pr_compliance_checklist.yaml` at
the repository root; the enforcement contract is defined here.

## The rules

| ID | Rule |
|---|---|
| SEC-1 | Authentication and authorization: every sensitive action (PUT/POST/DELETE on loans, payments, documents, user management, admin functions) and every data access must verify identity and check server-side authorization. |
| SEC-2 | Injection prevention: never concatenate or interpolate untrusted input into SQL, OS commands, templates, LDAP, XPath, HTML, or JavaScript. Parameterized queries and safe encoders only. |
| SEC-3 | SSRF prevention: untrusted input must never control server-side request destinations (URL, host, IP, port). Fixed or strictly allow-listed destinations, with redirect and internal-range protections. |
| SEC-4 | No test, debug, mock, demo, or diagnostic functionality reachable in production code paths, including debug routes, auth bypasses, and hardcoded test users. |
| SEC-5 | No hardcoded secrets, tokens, passwords, private keys, or connection strings in source code or committed configuration. |

## How to review

1. Evaluate EVERY rule against EVERY changed file. Do not sample.
2. For each violation, report: the rule ID, the file and line, the exact rule
   text it violates, the evidence in the code, and a concrete fix.
3. If a rule cannot be evaluated for a changed file (for example, the file is
   binary or generated), report that explicitly with the reason. An
   unevaluated rule is itself a finding, never a silent skip.
4. End with a coverage summary: N rules evaluated, M skipped and why,
   K violations found.
5. Apply a false-positive gate last: drop findings where the flagged code is
   not reachable from a production path, or the input is not attacker
   controlled, and say so when you drop one.

## Using this skill as a template

Copy this directory to `skills/<your-skill-name>/` in your own repository and
replace the rules table with your organization's rules. Keep the structure:

- Frontmatter `description` must be a single line.
- A rules table with stable IDs, so findings are traceable back to your
  source document.
- The "How to review" contract (full enumeration, coverage summary,
  false-positive gate) is what turns a rules document into a review the
  security team can trust; keep it verbatim.

Qodo imports skills from `skills/<skill-name>/SKILL.md` on push, links the
extracted rules to the skill, and scopes them to this repository
automatically. See `docs/central-rules-repo.md` for scoping the extracted
rules beyond this repository.
