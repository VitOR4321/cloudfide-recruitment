# Unit test agent

The application was imported from `cf-recruitment/taskly-app` at
`9addcc7d6279ea8fd080f069b8d5f5404ffd281c`. Backend behavior and coverage exclusions
are unchanged. The frontend now explains when status filtering hides a task and
uses a recognizable checkbox tick. Playwright is a pinned development dependency
for browser regression tests. Vite, Vitest and Storybook were updated within their
existing major versions to fix reported development-tool vulnerabilities; the
follow-up npm audit reports zero vulnerabilities. Runtime dependencies are unchanged.
The backend Dockerfile assigns copied source
to its runtime user so restrictive host file permissions do not prevent startup.
New tests cover HTTP failures and cancellation,
query caches, filtering, notification timers, CRUD, validation, database cleanup,
configuration, health and application startup.

## Design

`test-agent/agent.py` is a custom Python agent using the OpenAI Responses API.
It has one tool, `read_file`, and a structured output containing a decision,
rationale and proposed test files. It can inspect source and existing tests over
several turns. It chooses whether tests are needed and may create or update them.
There is no model-controlled shell, network tool or dependency installation.

`test-agent/AGENT.md` defines its role. The controller loads reusable instructions
from `test-agent/skills/*/SKILL.md`: analyze-changes and verify-tests always apply
to source changes; frontend-tests and backend-tests are selected by changed paths.
Each proposal records the skills used and files inspected in `decision.json`.
Documentation-only changes skip the model entirely.
Before calling the model, the controller supplies changed implementation,
neighboring tests, domain types and test helpers as bounded source context.
`context_files` records those supplied files; `reads` records additional model
tool calls. Existing mock/provider setup and tests must be retained when updating
a file. The frontend skill explicitly covers typed props, Vitest imports,
design-system providers and render cleanup.

The workflow in `.github/workflows/unit-test-agent.yml` has three jobs:

1. **baseline** runs all current tests and the frontend build.
2. **propose** reads the PR diff and baseline results, lets the agent inspect files
   and produces a patch, including updates to stale tests when appropriate.
3. **verify** applies the proposal to the exact PR head and repeats tests and build.

Controller code and skills come from the base commit. PR source is read as data
in the generation job; it is not imported or executed there. The API key exists
only in the generation step. Test execution happens in separate jobs without it.
All GitHub tokens have read-only repository permissions; checkout credentials
are not persisted. Actions are pinned to commit SHAs, jobs have timeouts and newer
PR updates cancel superseded runs. No dependency caches cross the trust boundary.

`safety.py` limits writes to frontend `*.test.ts(x)` and backend `test_*.py` files.
It rejects traversal, symlinks, configuration changes, duplicate paths and excessive
output. Application source and hidden files cannot be overwritten. Proposals are
bound to a commit and apply requires a clean checkout. Every file is validated
before any is written. The model is limited to eight turns and 24 file reads;
large PRs fail explicitly instead of silently truncating the diff.

## GitHub setup and results

Use your own public repository. Put this implementation on its default branch
before opening a feature PR, because the controller is loaded from the base.
Enable GitHub Actions and add the repository Actions secret `TEST_AGENT_API_KEY`
with access to the OpenAI Responses API. Optionally set the repository variable
`TEST_AGENT_MODEL`; the default is `gpt-4.1`. Never commit the key or place it in
an issue, PR description or workflow file.
This is an OpenAI API key from https://platform.openai.com/api-keys, not a GitHub
token or a ChatGPT subscription. OpenAI API billing is separate. Application and
unit/browser tests work without this secret; only model generation requires it.

Opening, updating or reopening a PR starts the workflow. Marking a draft ready
also starts it. Fork PRs, drafts and Dependabot PRs run baseline checks but skip
model generation. For a fork contribution, review the code first and move the
reviewed change to a branch in this repository if generation is wanted. Same-repo
contributors are trusted to modify Actions workflows; protect those files with
branch rules and review permissions.

The PR's Actions checks link to job summaries with decisions, test counts and
before/after line coverage. Download `test-proposal` for `decision.json`, the
complete `proposal.json` and `tests.patch`. Logs and machine-readable results are
in `baseline-results` and `proposal-results`. Artifacts expire after seven days.
Failing tests or builds fail the check. A missing model key fails generation for
source changes. No tests are automatically committed: after reviewing a passing
proposal, apply `tests.patch` with `git apply`, run tests and commit it to the PR.

## Local validation

Install dependencies as described in README.md, then run from the repository root:

```sh
backend/.venv/bin/python test-agent/verify.py --root . --output /tmp/taskly-results
```

For a live local agent run, securely provide `TEST_AGENT_API_KEY` in your process
environment, check out the PR head in a clean checkout and use full commit SHAs:

```sh
python3 test-agent/agent.py prepare --root . --base "$BASE_SHA" --head "$HEAD_SHA" --output /tmp/taskly-proposal
python3 test-agent/agent.py apply --root . --head "$HEAD_SHA" --proposal /tmp/taskly-proposal/proposal.json
backend/.venv/bin/python test-agent/verify.py --root . --output /tmp/taskly-results
```

Measured locally on Python 3.12 and Node 24:

| Suite | Original tests | Current tests | Original line coverage | Current line coverage |
| --- | ---: | ---: | ---: | ---: |
| Backend | 21 | 56 | 44.14% | 100% |
| Frontend | 18 | 52 | 47.68% | 86.45% |

All application tests pass, as do the production frontend build, frontend format
check and actionlint validation. Backend branch coverage is 100%; frontend branch
coverage is 82.55%. These are unit-test results under the original coverage scope,
which excludes frontend design-system code and backend models/schemas, among
other files. They do not establish PostgreSQL or browser end-to-end coverage.

The Docker stack was also built and exercised in the cloud with PostgreSQL:
frontend HTML and JavaScript, nginx API forwarding, database health, listing,
creating, reading, updating and deleting a task, and a 404 after deletion all
passed. The temporary smoke-test task was deleted. Cloud-only build overrides
mounted the session CA for package downloads without changing TLS verification;
these overrides are outside the repository. Windows startup instructions are in
README.md; this does not mean the app has been launched on the user's computer.
Five Chromium scenarios in `frontend/e2e/tasks.spec.ts` additionally pass against
the real stack. They verify completion without disappearance under All statuses,
filter explanations, failed saves, CRUD, validation, reload persistence, search
and sorting. `application-checks.yml` runs unit checks and these browser checks
on main pushes and pull requests, without model credentials.

There are also 21 controller and verification tests, run with
`python3 -m unittest discover -s test-agent/tests -v`. One integration example
creates a temporary Git repository, changes a doubling function, feeds a recorded
model-tool exchange to the real controller, loads analyze-changes, verify-tests
and backend-tests, checks the patch, applies it and executes two passing tests
for zero and negative inputs. Another verifies that a documentation change skips
the model. Other cases exercise path restrictions, commit binding, budgets,
credential removal, exit status propagation, stale results and zero/all-skipped
test runs. None of those invalid verification outcomes can produce a passing report.

The recorded model response is an offline test fixture, not evidence of a live
OpenAI-backed agent run. Separately, the real GitHub-hosted Application checks
run [41143768300](https://github.com/VitOR4321/cloudfide-recruitment/actions/runs/41143768300)
completed successfully for commit `dda8ee4`: both the unit and browser jobs passed.
The public run page confirmed this independently of the cloud checks.
The GitHub API still returns Forbidden from this machine. The first live agent
run on PR #1, [41209576969](https://github.com/VitOR4321/cloudfide-recruitment/actions/runs/41209576969),
successfully generated a proposal, which verification rejected: the model had
not read the existing tests, omitted their design-system mocks, used untyped
helper props and invented a sort value. The two generated tests failed and
TypeScript found three errors. This was a generated-test defect, not an app bug.
The controller now supplies the missing source context automatically and the
skills document the relevant conventions. The corrected regression test file
passed all eight cases and the frontend build locally. The fresh model-backed
PR run [41210834220](https://github.com/VitOR4321/cloudfide-recruitment/actions/runs/41210834220)
then completed successfully for head `ec36e96`: baseline, propose and verify all
passed in GitHub Actions. It used the corrected controller from base `1bbc3fd`.
Failed command output now appears directly in Actions logs and the summary as
well as artifacts, with command exit statuses preserved.

## Limits and production follow-up

Assignment audit:

| Requirement | Status |
| --- | --- |
| Own public GitHub repository and imported application | Done |
| Missing unit tests and better coverage on both sides | Done locally; measurements above |
| Custom agent and reusable skills used by the controller | Implemented; controller tests and live frontend PR run pass |
| Automatic PR analysis, test proposals and verification | Live PR #1 completed successfully after the context fix |
| Results available in the PR context | Check summaries and three artifact groups are attached to the successful run |
| Technical documentation and example | Includes offline backend fixture and successful live frontend PR evidence |
| Optional example feature PR and hosted demonstration | PR #1 adds Reset filters; successful run linked above |

The live model-backed example exercises the frontend; the backend generation
contract is exercised by the offline controller fixture and the backend suite
runs in every verification job. A second live PR changing backend behavior would
broaden the demonstration. The model secret works in GitHub Actions. This cloud
machine's API access remains blocked; public run pages confirmed the result,
and user-supplied artifacts enabled the original failure analysis.

The branch `example/reset-filters` adds a Reset filters button without changing
main. It resets search, status and sort order. Existing checks pass on that
branch. The demonstration is available at:
https://github.com/VitOR4321/cloudfide-recruitment/pull/1

The workflow proposes tests and validates them once; it does not automatically
repair failures or alter application code. A failed baseline test run is supplied
to the agent and remains a failed check; generation and proposal verification can
still proceed. Dependency installation failures block generation.
There is no coverage gate: reviewers inspect the measured delta and assertions.
A passing generated test is still untrusted code and needs review, especially
when it changes existing tests. Prompt instructions are guidance, not a sandbox.

For production, run tests in disposable containers with explicit egress limits,
add per-repository spend quotas and retry/backoff for transient model failures,
require approval before generating for external contributions, and add mutation
testing or changed-line coverage checks. A bounded repair loop should receive
sanitized test failures through the same separation of credentials and execution.
