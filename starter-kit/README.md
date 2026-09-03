# Qodo Review Standards starter kit

This directory is a copyable GitHub starting point for managing Qodo Review Standards in Git and publishing them with repository scope.

Start with one non-production GitHub repository so the team can see the workflow once. After that, use the same reviewed process for the repositories where each standard belongs.

## Guided setup: start here

Do not perform the setup below manually unless you want to. The included skill guides the full process.

1. Clone or download this public repository.
2. Install or copy [`skills/qodo-security-standards-setup/`](skills/qodo-security-standards-setup/) into your coding agent's project skill directory. For example, with Claude Code:

   ```bash
   mkdir -p .claude/skills
   cp -R skills/qodo-security-standards-setup .claude/skills/
   ```

3. Keep this checkout available so the agent can copy `starter-kit/`.
4. Start a fresh agent session and say:

   > Set up Qodo Security Review Standards for my repositories.

The skill asks for an existing standards repository or offers to create one. It then walks through Qodo CLI and skills setup, portal readiness for the named repository, starter installation, Git review, Review Resolver, publication, the first walkthrough, and the first real rule.

If the agent does not discover it automatically, explicitly ask it to run `qodo-security-standards-setup`. Full setup prompts have been tested in fresh Claude Code sessions; this explicit form avoids overlap with broader Qodo onboarding skills.

## What the skill copies

Copy the contents of `starter-kit/` into the root of a new standards repository:

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

## Manual setup reference

The guided skill handles this section. These details remain here for users who want to inspect or perform the steps manually.

### Check Qodo

Normal Qodo onboarding provides the Skills and CLI together. Check the runtime:

```bash
qodo --version
qodo whoami --json
```

If `qodo` is not on `PATH`, try `$HOME/.qodo/bin/qodo`. If it is missing or outdated, invoke the `qodo-setup` skill in your coding agent. It verifies the runtime, guides installation, completes login, and checks the managed tools without asking you to paste credentials into chat. Current Qodo Skills distributions name the Git finding workflow `qodo-review-resolver`; older installations may show `qodo-pr-resolver`.

Use your organization's approved installer and login endpoint when it provides one.

### Configure the first scope

Create these GitHub settings:

This starter's publication workflow targets Qodo Cloud. For single-tenant or on-premises deployments, use the installer and login command supplied by your Qodo administrator instead of adding a configurable endpoint to the workflow.

Protect the `qodo-sync` environment so only the default branch can access it. Store `QODO_API_KEY` there as the Qodo workspace admin API key. Never commit credentials.

Set the initial scope in `rule-scopes.txt`, such as `/acme/security-rules-test/`. Scope changes use the same reviewed pull-request path as rule changes.

The workflow publishes only after a pull request merges into the repository's live default branch. Keep branch protection enabled so publication always follows a reviewed pull request.

The workflow uses a version-pinned Qodo CLI artifact and verifies the SHA-256 checksum currently published by Qodo before login. Its Python dependency is also version-and-hash pinned. Update the Qodo version and checksum together from Qodo's `version.json` when upgrading the starter.

## The normal workflow

The standard path is Git-first:

1. Create or update a YAML rule.
2. Open a pull request.
3. Qodo reviews the rule and sync code in Git.
4. Invoke the installed Qodo Review Resolver skill to handle the findings.
5. Merge after the review and human approval are ready.
6. The workflow publishes the rule with the reviewed `rule-scopes.txt` value.

You can optionally run a local review before pushing:

```bash
qodo review rules/your-rule-name.yaml
```

That gives faster feedback while editing. If you skip it, Qodo still reviews the pull request in Git, and the resolver skill handles the shared review.

## First walkthrough

1. Open a pull request containing the demo rule and starter automation.
2. Let Qodo review it in Git.
3. Invoke the installed Qodo Review Resolver skill to fix useful findings.
4. Merge after Qodo and a human reviewer are ready.
5. Confirm the demo rule is active and scoped to the test repository.
6. In a temporary branch there, add the small planted shell-command issue from the article.
7. Run Qodo review and Security Agent.
8. Replace it with the safe implementation and see the different result.
9. Close the demonstration pull request. Do not merge the planted issue.

This is an onboarding exercise. You do not need to repeat it for every rule.

## Add a rule

```bash
cp rules/_template.yaml rules/your-rule-name.yaml
```

Fill it manually or invoke the guided setup skill above. Open a pull request and let Qodo review the standard. After merge, confirm its intended scope and use it normally.

## Optional helper check

```bash
python3 scripts/test_sync_rules.py
```

This checks the sync helper's placeholder handling, scope parsing, and Qodo command construction. Qodo review in the pull request remains the shared quality gate.

## Lifecycle behavior

- Rule names are identities. Renaming creates a new rule.
- Removing a YAML file does not deactivate its live Qodo rule.
- Updating scopes replaces the full scope list.
- The CI sync requires an admin identity.
- The workflow serializes publication runs and reports partial progress if a later rule fails, so the next run reconciles from the actual live state.
- Start with a test repository to learn the workflow, then use the intended repository or Git-organization scope.
