# Taskly App

React + TypeScript, FastAPI and PostgreSQL. Based on
[cf-recruitment/taskly-app](https://github.com/cf-recruitment/taskly-app)
at `9addcc7d6279ea8fd080f069b8d5f5404ffd281c`.
See [SOLUTION.md](SOLUTION.md) for the test agent and PR workflow.

## Run

Install Docker with Compose and copy `.env.example` to `.env`.

```sh
docker compose up --build -d --wait
```

Application: http://localhost:8080. API: http://localhost:8000/docs.
Ports are configured in `.env`. Stop with `docker compose down`.

## Unit tests

```sh
docker compose -f compose.test.yaml up --build --abort-on-container-failure
```

Runs backend, frontend and agent tests. Results and coverage appear in the
terminal. No API key or application database is required.

## Browser tests

Start the application, then run from `frontend` using Node 24:

```sh
npm ci
npx playwright install chromium
npm run test:e2e
```

Set `TASKLY_BASE_URL` for a different application address. Reports are written
to `frontend/playwright-report`. Test-created tasks are cleaned up afterwards.
