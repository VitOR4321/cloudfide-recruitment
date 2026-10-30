# Backend tests

Use pytest, existing fixtures and unittest.mock. Place tests under `backend/tests`
as `test_*.py`. Check successful operations, missing records, validation errors and
cleanup after failures. Mock external services and database boundaries for unit
tests. Use dependency overrides for FastAPI routes and ensure resources close.
Do not require PostgreSQL for unit tests or change production code. Verification:
`python -m pytest --cov=app --cov-report=term-missing --cov-report=json` from
`backend` with its requirements installed.
