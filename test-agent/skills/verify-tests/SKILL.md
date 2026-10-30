# Verify tests

Only propose executable tests with meaningful assertions. The controller validates
the response and writes a proposal artifact without executing it. A separate job
without the model key applies it to the exact PR head, runs the complete backend
and frontend suites, checks TypeScript and builds the frontend. Compare coverage
with the baseline run. Failures remain failures; do not suppress exit codes or
describe skipped generation as success. Publish decisions, executed commands,
test counts, coverage and a reviewable patch in the workflow artifacts and summary.
