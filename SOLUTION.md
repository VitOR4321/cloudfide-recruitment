# Unit test agent

## Design

`test-agent/agent.py` is a custom Python agent using the OpenAI Responses API.
Its role is defined in `test-agent/AGENT.md`. It analyzes PR changes, receives
source, neighboring tests, types and helpers, and can inspect additional files
through a read-only tool. Structured output contains a decision, reason and test files.

Reusable skills in `test-agent/skills/` cover change analysis, frontend tests,
backend tests and verification. Skills are selected by changed paths and loaded
into the agent's instructions. Decisions and inspected files are recorded in
`decision.json`. The small controller keeps model actions bounded and reviewable.

## Workflow and prerequisites

Enable GitHub Actions and add the repository secret `TEST_AGENT_API_KEY` with an
OpenAI API key. Set `TEST_AGENT_MODEL` optionally; the default is `gpt-4.1`.
Keep the controller on the default branch before opening feature PRs.

`.github/workflows/unit-test-agent.yml` runs automatically for same-repository PRs:

1. `baseline`: execute existing tests and build.
2. `propose`: analyze changes and create/update tests, or explain a skip.
3. `verify`: apply the proposal to the exact PR head, run tests and build again.

PR checks expose decisions, test counts and coverage. Artifacts contain logs,
`proposal.json`, `decision.json` and `tests.patch` and are retained for seven days.
Review a passing patch before applying and committing it. Application and test
commands are in [README.md](README.md); ordinary tests need no model key.

## Security

Controller code comes from the PR base. The model key exists only during
generation; test execution uses a separate job without it. Repository permissions
are read-only and Actions are pinned. Path validation permits only unit test
writes and rejects traversal, symlinks and configuration changes. Context, turns
and reads are limited. Repository content and model responses are untrusted data.
Failed checks, zero-test and all-skipped runs do not pass verification.

## Example run

Pending validation in the target repository. Before submission, record a real PR
and Actions run here: the changed behavior, the agent's decision, skills used,
proposed test files, executed tests and coverage results. The backend controller
also has an offline integration fixture; distinguish offline checks from live runs.

## Assumptions, limitations and production changes

Same-repository contributors are trusted. Forks, drafts and Dependabot receive
baseline checks but skip generation. Unit tests mock external services; browser
tests need the application and PostgreSQL. Coverage excludes models/schemas and
the frontend design system according to the existing configuration.

Proposals require human review and are not committed automatically. There is no
automatic repair loop or coverage gate. Production extensions would include
isolated test execution with egress limits, spend quotas, transient-error retries,
changed-line or mutation checks and a bounded repair loop.
