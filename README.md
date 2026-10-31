# Taskly App

React + TypeScript frontend and Python + FastAPI backend with PostgreSQL.
Based on [cf-recruitment/taskly-app](https://github.com/cf-recruitment/taskly-app)
at `9addcc7d6279ea8fd080f069b8d5f5404ffd281c`.

See [SOLUTION.md](SOLUTION.md) for the custom test agent, reusable skills and PR workflow.

## Run with Docker

Requirements: Docker with Compose. Copy `.env.example` to `.env`, then run:

```sh
docker compose up --build -d --wait
```

Application: http://localhost:8080. API documentation: http://localhost:8000/docs.
Configure ports in `.env`. Stop with `docker compose down`; database data is retained.

## Tests

Run backend, frontend and agent unit tests without installing Python or Node:

```sh
docker compose -f compose.test.yaml up --build --abort-on-container-failure
```

Results and coverage are printed in the terminal. These tests require no API key
or running database. Remove stopped test containers with
`docker compose -f compose.test.yaml down`.

For browser tests, start the application and run from `frontend` with Node installed:

```sh
npm ci
npx playwright install chromium
npm run test:e2e
```

Set `TASKLY_BASE_URL` to test a different address. Browser reports are written to
`frontend/playwright-report`. Tests create and clean up their own tasks.

## Development

Use Node 24 and Python 3.12 for native development.

Frontend, from `frontend`:

```sh
npm ci
npm run dev
```

Run `npm test` for unit tests, `npm run test:coverage` for coverage and
`npm run storybook` for the component library.

Backend: start PostgreSQL with `docker compose up -d --wait postgres`, then run
from `backend`:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --reload
```

Run `.venv/bin/python -m pytest --cov=app` from the same directory for tests and coverage.
