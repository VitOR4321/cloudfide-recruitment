# Unit test agent

## Approach

A custom Python agent uses the OpenAI Responses API to analyze PR changes and
propose missing unit tests for React/TypeScript and Python/FastAPI. Structured
output and a read-only file tool keep the integration small and reviewable.

The controller is in `test-agent/agent.py`; its role is defined in
`test-agent/AGENT.md`. Reusable skills live in `test-agent/skills/`:

- `analyze-changes`: identify behavior changes and existing coverage.
- `frontend-tests`: Vitest, Testing Library, types, mocks and providers.
- `backend-tests`: pytest, FastAPI fixtures and database boundaries.
- `verify-tests`: execution, coverage and reporting rules.

The controller loads skills according to changed paths and supplies implementation,
neighboring tests, types and helpers before calling the model. Extra files can be
read through `read_file`. Decisions, skills and inspected files are recorded in
`decision.json`. Documentation-only changes skip generation.

## Run the PR workflow

Keep the controller on the default branch and enable GitHub Actions. Add the
repository Actions secret `TEST_AGENT_API_KEY` with an OpenAI API key. Optionally
set `TEST_AGENT_MODEL`; the default is `gpt-4.1`. API billing is separate from ChatGPT.

Opening, updating or reopening a same-repository PR, or marking it ready for review,
starts `.github/workflows/unit-test-agent.yml`:

1. `baseline` runs existing tests and the frontend build.
2. `propose` analyzes the diff and produces test changes or explains a skip.
3. `verify` applies the proposal to the exact PR head and repeats tests and build.

Checks and summaries are available on the PR. Artifacts contain baseline results,
the test proposal and verification results. Download `test-proposal` for
`decision.json`, `proposal.json` and `tests.patch`. After reviewing a passing patch,
apply it with `git apply tests.patch`, rerun tests and commit it to the PR.
Artifacts are retained for seven days. Generated changes are not committed automatically.

The separate `application-checks.yml` workflow runs unit tests and Chromium
scenarios on main pushes and PRs. Developer commands are in [README.md](README.md).

## Security and reliability

Controller code and skills come from the PR base commit. The model key is available
only during generation; PR code runs in separate jobs without it. GitHub permissions
are read-only, checkout credentials are not persisted and Actions are pinned to SHAs.

`safety.py` restricts writes to unit test files and rejects traversal, symlinks,
configuration changes, duplicate paths and excessive output. Proposals are bound
to a commit and require a clean checkout. Source context, file reads and model turns
are bounded. Repository content and model output are treated as untrusted data.
Failures remain visible; zero-test or all-skipped runs cannot pass verification.

## Example and validation

[PR #1](https://github.com/VitOR4321/cloudfide-recruitment/pull/1) adds Reset filters.
The agent identified missing tests for button visibility and reset callbacks,
using analyze-changes, frontend-tests and verify-tests. Its first proposal failed
type checking and lacked the existing design-system mocks. Automatic source
context and clearer skill instructions addressed those errors.

[Run 41210834220](https://github.com/VitOR4321/cloudfide-recruitment/actions/runs/41210834220)
completed successfully: baseline, propose and verify passed with the model-backed
workflow. Backend generation also has an offline controller integration fixture;
the live example above exercises frontend generation.

Application test measurements at `dda8ee4`, before the example feature PR:

| Suite    | Tests before / after | Line coverage before / after |
| -------- | -------------------: | ---------------------------: |
| Backend  |              21 / 56 |                44.14% / 100% |
| Frontend |              18 / 52 |              47.68% / 86.45% |

Coverage uses the original exclusions, including backend models/schemas and the
frontend design system. There are also 21 controller/verification tests and five
Chromium scenarios covering CRUD, completion, filtering, errors and persistence.

## Assumptions, limitations and next steps

Same-repository contributors are trusted to change workflows. Fork PRs, drafts and
Dependabot PRs receive baseline checks but skip generation. Unit tests mock external
services; browser checks use a running application and PostgreSQL.

Generation is verified once; there is no automatic repair loop or coverage gate.
Passing proposals still need human review. The live demonstration covers the
frontend; a backend feature PR would broaden the evidence. For production, add
isolated test containers with egress limits, spend quotas, transient-error retries,
changed-line or mutation checks and a bounded repair loop that preserves the
separation between credentials and test execution.
