# Get missing-test feedback in Qodo pull request reviews

**Yes, Qodo can comment on missing tests.** Give it a review skill that inspects changed behavior and existing assertions. Add CI branch coverage when you want recommendations grounded in what the test run actually executed.

This starter connects those pieces for **Python projects using pytest on GitHub Actions, with same-repository PRs**. It includes the workflows, evidence collector, publisher and review skill. Your Qodo installation must support Review Skills and the `/agentic_review` command.

## 1. Copy the starter

From a local clone of this repository, copy the files into your application's repository:

```sh
mkdir -p /path/to/application/.github/workflows /path/to/application/scripts /path/to/application/skills
cp test-review-starter/.github/workflows/*.yml /path/to/application/.github/workflows/
cp test-review-starter/scripts/test_evidence.py /path/to/application/scripts/
cp -R test-review-starter/skills/test-impact /path/to/application/skills/
```

Add the dependencies from [`requirements-test.txt`](../test-review-starter/requirements-test.txt) to your existing test dependency file. If you use a different filename, update the install step in `test-evidence.yml`.

The workflow assumes source under `src` and tests under `tests`. Change both the pytest `--cov` path and the collector's `--source` argument to match your project. Include your normal dependency and service setup before the test step. Set `PYTHONPATH=src` if your project isn't installed as a package.

Commit the workflows, script and skill to the default branch. The publishing workflow runs trusted default-branch code, so it must be present there before you open the first test PR.

## 2. Activate the review skill

In Qodo Review Standards, import your repository, activate `test-impact`, select steering mode and scope it to your application repository. Reimport after editing the skill.

For installations using repository TOML, merge these settings into `.pr_agent.toml`:

```toml
[review_agent]
enabled = true
enable_skills_agent = true
enable_deduplication = true
```

Keep your existing general-review agents. Deduplication combines overlapping skill and general-review findings into one recommendation. Have CI request the evidence-backed review after tests finish; if you currently trigger `/agentic_review` on PR open, remove that automatic command from `[github_app].pr_commands` to avoid a separate pre-CI review. Setting `pr_commands = []` leaves the CI publisher responsible for requesting review. Preserve any unrelated commands your team needs.

## 3. Let CI deliver the evidence

The two workflows have separate responsibilities:

1. **Test evidence** checks out the PR HEAD without stored Git credentials, installs test dependencies, runs pytest with branch coverage and creates a compact JSON artifact. Its token has read-only repository permissions.
2. **Qodo test review** runs from the default branch after the first workflow finishes. It reads the run metadata and artifact, validates the evidence and requests Qodo review with the compact coverage data.

The publisher never executes downloaded artifacts or checks out PR code. It rejects failed runs, mismatched HEAD/base revisions, empty suites, missing measurements, unsafe paths and oversized payloads. It supports same-repository PRs; fork PRs need a separately approved untrusted-contribution workflow.

The publisher uses the workflow's GitHub token to post the review request. Enable Actions and allow the workflow its declared pull-request write permission. Confirm that your Qodo installation processes that request in the first validation PR. Keep branch protection on the test workflow, not the review comment.

## 4. Check a missing case, then fix it

For a function that applies a discount at 100, start with only a test at 20. Open a non-draft PR adding the discount. The review should explain that the discount branch was not executed and recommend boundary tests:

| Input | Expected result |
|---|---|
| 99 | 99 |
| 100 | 90 |
| 101 | 91 |

Add those assertions and push again. CI generates new evidence for the new commit, and the measured gap disappears. Qodo can still identify a separate assertion weakness even when all measured branches execute.

The starter's [`example`](../test-review-starter/example) supplies a minimal baseline. To run the local copy-and-measure check from this repository:

```sh
python -m pip install -r test-review-starter/requirements-test.txt
python test-review-starter/scripts/smoke_test.py
python -m unittest discover -s test-review-starter/scripts -v
```

## 5. Read findings and enforce tests

A useful finding names the changed behavior, existing tests inspected, missing scenario and expected assertion. Coverage-backed findings cite the matching CI run and branch locations. Source-based findings explain weaknesses in the assertions themselves.

Keep required test checks in CI. This starter requests review for successful, nonempty test runs, including runs with missing branch outcomes; it does not impose a blanket zero-missing-branches merge policy. Configure that policy in your coverage gate if your team requires it.

Failed or empty suites do not produce a coverage-backed request. Fix the test job and rerun. A stale result is rejected: rerun tests after the base changes or push a new commit to trigger a fresh run.

## Troubleshooting

- **No review request:** inspect the `Qodo test review` job. It reports the failed admission check or links the posted request.
- **Request posted but no review:** confirm Qodo is installed on the target repo and accepts `/agentic_review` requests from the publishing identity.
- **Skill absent from review context:** check import, active state, steering mode and repository scope.
- **Missing file measurement:** align `--cov` and `--source` with the application layout. Don't replace missing measurement with an empty branch list.
- **Passing coverage but a test recommendation remains:** inspect whether the test asserts the result, not just whether it executes the code.
