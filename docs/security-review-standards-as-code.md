# Security Review Standards as code with Qodo

Security policy often lives in documents. Qodo Review Standards make that policy operational by applying it during code review. Qodo treats explicit Rules and reusable Skills as parts of the same Review Standards system.[1]

This guide shows how to manage security rules in Git, have Qodo review the rules themselves, publish them through the Qodo CLI, and combine standards-aware code review with Qodo Security Agent.

The steady-state workflow is intentionally short:

```text
write or update a rule
  -> open a pull request
  -> Qodo reviews it in Git
  -> resolve useful findings with the Qodo resolver skill
  -> merge
  -> publish the rule with the intended repository scope
```

The sync helper rejects malformed rule files and leftover placeholders before it writes. The optional local Qodo review gives authors earlier feedback. Neither replaces the Qodo review in Git, which is the shared quality gate whether or not the author ran anything locally.

## The operating model

Use two repositories to get started:

1. **Standards repository:** stores rule definitions and the publication workflow.
2. **Test repository:** receives the first rule and gives the team a familiar place to see it in Qodo review and Security Agent.

Once the team is comfortable, the same rule can be scoped to the repositories where it belongs. Qodo supports global, Git organization, repository, and repository-path scopes.[3]

A Qodo rule has a name, enforcement content, compliant and non-compliant examples, a category, a severity, and a scope.[3]

## Prerequisites

Before starting, the skill will ask for or help prepare:

- A Git repository for the standards.
- One non-production repository for the initial walkthrough.
- Qodo connected to both repositories with a healthy connection and code review enabled.[9]
- Qodo Security Agent enabled for the walkthrough repository under **Configurations > Context**.[7]
- A Qodo workspace admin API key stored as a protected CI secret.
- A coding agent with the Qodo Skills package.
- **Optional local review:** the `qodo-review` skill.
- **Git review resolution:** invoke the installed Qodo **Review Resolver** skill. Current Qodo Skills distributions name this `qodo-review-resolver`; older installations may show `qodo-pr-resolver`.

Normal Qodo onboarding provides the Skills and CLI together. Check the local runtime before doing anything else:

```bash
qodo --version
qodo whoami --json
```

If `qodo` is not on `PATH`, try:

```bash
$HOME/.qodo/bin/qodo --version
```

If it is missing or outdated, invoke the `qodo-setup` skill in your coding agent. It verifies the runtime, guides installation without asking you to paste credentials into chat, completes browser login, and checks that the managed tools are ready. Use your organization's approved installer or login endpoint when it provides one.[8]

## Step 1: run the guided setup skill

Install the `qodo-security-standards-setup` skill from the public [qodo-rules-starter repository](https://github.com/gvago/qodo-rules-starter), then ask your coding agent to set up Qodo Security Review Standards.[6]

The skill asks for an existing standards repository or offers to create one, checks or installs the Qodo CLI and skills with approval, guides repository-specific Security Agent activation, copies the starter kit, configures publication, drives the first Qodo-reviewed pull request, and stays with the user through the walkthrough and first real rule.

The starter files copied into the standards repository are:

```text
.github/workflows/review-standards.yml
.gitignore
requirements.txt
rule-scopes.txt
rules/_template.yaml
rules/demo-shell-command-safety.yaml
scripts/sync_rules.py
scripts/test_sync_rules.py
```

The kit includes one small demonstration rule. It lets the team see the complete workflow before replacing it with its own standards.

Configure these repository settings:

Configure the protected `QODO_API_KEY` CI secret with a workspace admin API key.

The included publication workflow targets Qodo Cloud. Single-tenant and on-premises deployments should use the installer and login command supplied by their Qodo administrator.

Set the reviewed scopes in `rule-scopes.txt`. Use `/owner/repository/` format and separate multiple repositories with commas:

```text
/your-org/backend/,/your-org/frontend/,/your-org/mobile/
```

This is the complete target list for every rule in `rules/`.

Use the test repository for the first walkthrough. After that, select the real scope based on where the standard applies.

## Step 2: open the first standards pull request

Push the starter kit to a branch and open a pull request in the standards repository.

Qodo reviews the YAML rule, examples, synchronization code, and workflow in Git. This is the main quality gate and it runs whether or not the author used local review.

A rule that looks sensible at first glance can still contain a contradiction, an invalid API example, an incomplete mitigation, or wording broad enough to create noise. The Git review can identify these issues before the rule becomes part of normal development.

Use the installed Qodo Review Resolver from Codex, Claude, Cursor, or another supported coding agent to retrieve the current findings and fix the sound ones.[8]

The normal authoring loop is:

1. Open or update the pull request.
2. Let Qodo review the current commit.
3. Invoke the installed Qodo Review Resolver skill.
4. Apply the findings that improve the rule or automation.
5. Push the revision and let Qodo review it again.
6. Merge after the Qodo review and human review are ready.

You can also run `qodo review` before opening the pull request. It reviews local changes and can use context that is not yet in Git. This shortens the feedback loop, but it is optional. The Git review remains the shared record and the path every contributor can rely on.

## Step 3: publish to Qodo

After merge, the publication workflow uses the Qodo CLI to create new Review Standards and update existing ones by exact rule name. It publishes only after a pull request merges into the repository's live default branch and requires branch protection. The sync script reads the complete list from `rule-scopes.txt` and passes it to `qodo rules create` or `qodo rules update` through the `--scopes` option.

The included sync runs a preview first, then applies the same plan. It reports each rule as `CREATE`, `UPDATE`, or `UNCHANGED`. The workflow uses a version-pinned Qodo CLI artifact and verifies the SHA-256 checksum currently published by Qodo before login. The Python dependency is version-and-hash pinned.

Confirm the result in **Qodo portal > Review Standards > Rules**:

- The rule is active.
- The name and source are the expected ones.
- The scope names the intended repository.

You can also inspect it from the CLI:

```bash
qodo rules list \
  --name-contains "shell commands" \
  --scopes "/your-git-org/security-rules-test/" \
  --json
```

This verification is a quick deployment check, not a recurring burden. Once the workflow is established, unchanged rules are skipped and each merge follows the same path.

## Step 4: see the rule work

For the first walkthrough, create a temporary branch in the test repository and add one obvious example that violates the demonstration rule:

```python
import subprocess


def resolve_host(hostname: str) -> None:
    subprocess.run(f"nslookup {hostname}", shell=True, check=True)
```

Open a pull request containing that change. Qodo review should apply the Review Standard and explain the unsafe data flow. Run Qodo Security Agent on the same repository to add its specialized OWASP/CWE security analysis alongside the standard review.[7]

Then replace the example with the normal non-shell implementation:

```python
import socket


def resolve_host(hostname: str) -> None:
    socket.getaddrinfo(hostname, None)
```

This first comparison teaches the team what a useful finding looks like and what the rule considers compliant. It is an onboarding exercise, not a procedure to repeat for every rule.

Close the demonstration pull request when the walkthrough is done. Do not merge the planted issue.

## Step 5: write your first rule

Copy the template:

```bash
cp rules/_template.yaml rules/your-rule-name.yaml
```

A strong rule has one measurable goal. Qodo's public guidance recommends rules that are frequent, actionable, valuable, clear about when they apply, and supported by compliant and non-compliant examples.[2]

The fastest path is the `qodo-security-standards-setup` skill in the starter kit. It guides the initial setup and then asks for the affected languages and frameworks, expected behavior, legitimate exceptions, severity, examples, and target scope. It updates the template and shows the proposed diff.

For a manual review, ask five questions:

1. **When does it apply?** Name the affected languages, frameworks, files, operations, or data flow.
2. **What exactly fails?** A reviewer should be able to point to observable evidence in a changed file.
3. **What passes?** State the accepted behavior or mitigation, including legitimate exceptions.
4. **Do the examples agree?** The name, content, severity, good example, and bad example must describe the same requirement.
5. **Will it help?** A real unsafe change should trigger it, while normal safe code should stay quiet.

Avoid standards such as "code must be secure" or "validate all input." They do not define a useful review decision. Name the risky flow and the accepted control instead.

## Step 6: let Qodo improve the rule

The rule pull request gives Qodo a chance to identify the same kinds of problems you would care about in application code:

- Technical accuracy.
- Internal consistency.
- Complete mitigation.
- Valid examples.
- Clear applicability.
- Useful severity.

Invoke the installed Review Resolver skill to work through the findings. Review feedback is still a second opinion, so verify factual claims about APIs and frameworks before changing the rule. In practice, this loop helps turn a policy sentence into a standard that developers can act on.

If you want feedback before pushing, run a local review:

```bash
qodo review rules/your-rule-name.yaml
```

If you skip it, nothing is lost. The pull request receives the Qodo Git review, and the resolver skill handles that shared review.

## Step 7: merge and use the rule

After the rule pull request is ready, merge it. The workflow publishes the rule with the configured scope.

For the first real rule, check it once in the portal, then exercise it in the test repository using code your team already understands. You do not need to manufacture a full test matrix. The goal is to understand the resulting finding and confirm that the scope is right.

After that, use the rule normally:

- Qodo applies the Review Standard during pull request reviews according to its scope.[1][3]
- Security Agent adds specialized OWASP/CWE analysis alongside the standard review.[7]
- Coding agents can load the relevant repository-specific rules with `qodo-get-rules` before changing code.[5]
- Rule outcomes appear in Review Standards analytics so the team can adjust standards that become noisy or obsolete.[2][3]

Qodo also supports importing standards from supported repository files and inferring repository or folder scope from their location.[4] This starter uses explicit CLI publication because a dedicated standards repository often needs to target other repositories.

## Step 8: expand the scope

When the rule belongs across a Git organization, scope it at the organization level. New repositories then inherit it without a reconciliation script. Use explicit repository or path scopes only when the standard truly applies to a subset.

The Qodo portal and `qodo-manage-standards` skill both support rule lifecycle and scope changes. Scope replacement sets the complete new scope list, so review the intended list before applying it.[3]

A sensible rollout is:

1. Learn the workflow in one test repository.
2. Apply the first real rule to its intended repository or repository group.
3. Review early findings as part of normal pull request work.
4. Widen to the Git organization when the standard is genuinely universal.

This is ordinary standards maintenance. Qodo applies the rules consistently; your team owns the policy and improves it as the codebase changes.

## Optional local syntax check

The starter includes a small standard-library check:

```bash
python3 scripts/test_sync_rules.py
```

It verifies placeholder detection, scope parsing, and command construction for the sync helper. The pull request workflow and Qodo review remain the authoritative shared checks.

## Rule lifecycle notes

The starter sync treats the rule name as identity.

- Renaming a YAML rule creates a new platform rule. Deactivate the old rule deliberately.
- Deleting a YAML file does not delete or deactivate the platform rule.
- Scope replacement overwrites the complete existing scope list.
- A non-admin API key may create a pending suggestion instead of an active rule.

Use `qodo-manage-standards` or the Qodo portal for lifecycle changes. Qodo's portal can edit, activate, deactivate, delete, and bulk-rescope standards.[3]

## The short version

Write the standard in Git. Let Qodo review it in the pull request. Use the resolver skill to improve it. Merge, publish to the intended scope, and use the same standard in code review, coding agents, and Security Agent.

Start in one test repository so the team can learn the workflow. Once learned, adding a rule is just another reviewed change.

## Sources

[1]: https://docs.qodo.ai/governance/review-standards
[2]: https://docs.qodo.ai/governance/rule-enforcement/best-practices-for-setting-rules
[3]: https://docs.qodo.ai/governance/rule-enforcement/generate-and-manage-rules
[4]: https://docs.qodo.ai/governance/rule-enforcement/building-review-standards
[5]: https://docs.qodo.ai/agent-skills
[6]: https://github.com/gvago/qodo-rules-starter
[7]: https://docs.qodo.ai/install-and-configure/configuration-overview/portal-configuration
[8]: https://github.com/qodo-ai/qodo-skills
[9]: https://docs.qodo.ai/governance/repositories/manage-repositories
