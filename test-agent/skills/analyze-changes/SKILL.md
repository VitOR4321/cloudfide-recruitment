# Analyze changes

Read the base-to-head diff. Identify changed behavior, boundaries and error paths.
Read affected implementation and adjacent tests with `read_file`. Consider existing
coverage and avoid duplicating assertions. Use frontend-tests for React/TypeScript
and backend-tests for Python/FastAPI; both may apply to the same pull request.
Inspect baseline failures when supplied. Update stale tests only if the changed
behavior is intentional; do not weaken tests to hide an application defect.
Return `skip` with a concrete reason when new tests are unnecessary. Return
`propose` with a concise description of the behaviors covered otherwise.
