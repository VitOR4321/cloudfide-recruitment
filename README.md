# Taskly App

Imported from [cf-recruitment/taskly-app](https://github.com/cf-recruitment/taskly-app)
at `9addcc7d6279ea8fd080f069b8d5f5404ffd281c`.
See [SOLUTION.md](SOLUTION.md) for the unit test agent, reusable skills and PR workflow.

## Setup

### Windows (drive F)

Install Git and Docker Desktop, start Docker Desktop with Linux containers, then
run in PowerShell. Use a new destination folder; cloning will not overwrite an
existing project.

```powershell
git clone https://github.com/VitOR4321/cloudfide-recruitment.git F:\cloudfide-recruitment
if ($LASTEXITCODE -ne 0) { throw 'Repository clone failed.' }
Set-Location F:\cloudfide-recruitment
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build -d --wait
if ($LASTEXITCODE -ne 0) { throw 'Application startup failed. Run docker compose logs.' }
Start-Process 'http://localhost:8080'
```

The code is in `F:\cloudfide-recruitment`: `frontend/src` contains the interface,
`backend/app` the API, `test-agent` the agent and skills, and `.github/workflows`
the PR automation. Additional backend tests are in `backend/tests`; frontend
tests are beside their source files. Open this folder in your editor to review
the code. No host Python or Node installation is needed for the Docker setup.

The API documentation is available at http://localhost:8000/docs. To stop the
application, run `docker compose down` from the project folder. This preserves
the database volume.

### Native development

```sh
cp .env.example .env
```

## Docker

```sh
docker compose up --build -d --wait
```

Application: http://localhost:8080. API: http://localhost:8000/docs.

```sh
docker compose down
```

## Tests with Docker

From the project root, run all backend, frontend and agent unit tests:

```sh
docker compose -f compose.test.yaml up --build --abort-on-container-failure
```

This uses separate test images and prints results and coverage in the terminal.
It needs no host Python or Node installation, API key or application database.
The test project publishes no ports, so your local `WEB_PORT` is unaffected.
The command exits with a failure code if a test container fails. To remove the
stopped test containers, run `docker compose -f compose.test.yaml down`.

For one suite only:

```sh
docker compose -f compose.test.yaml run --build --rm backend-tests
docker compose -f compose.test.yaml run --build --rm frontend-tests
docker compose -f compose.test.yaml run --build --rm agent-tests
```

The production images contain the built application, not the test sources.

## Browser tests

Start the application first. With Node installed, run from `frontend`:

```sh
npm ci
npx playwright install chromium
npm run test:e2e
```

The default target is `http://127.0.0.1:8080`. For a custom local port in
PowerShell, set the URL before running the tests:

```powershell
$env:TASKLY_BASE_URL = 'http://localhost:8082'
npm run test:e2e
```

Tests cover completion and reopening, filters, failed saves, validation, creation,
editing, deletion, persistence after reload, searching and sorting. They create
uniquely named tasks and delete only those tasks at the end. Reports are written
to `frontend/playwright-report`; failure traces go to `frontend/test-results`.
The Application checks workflow runs the same scenarios against a fresh CI stack.

Completing a task keeps it visible under **All statuses**. Under **To do**, it
leaves the current view because it is completed; choose All statuses or Completed
to see it. The interface now explains this and uses a visible check mark.

## Frontend

Installation:

```sh
cd frontend
npm ci
```

Development — http://localhost:5173:

```sh
npm run dev
```

Storybook — http://localhost:6006:

```sh
npm run storybook
```

Tests:

```sh
npm test
```

Coverage — `frontend/coverage/index.html`:

```sh
npm run test:coverage
```

## Backend

Installation (from the repository root):

```sh
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -r backend/requirements.txt
```

Development — http://localhost:8000/docs:

```sh
docker compose up -d --wait postgres
cd backend
python -m uvicorn app.main:app --reload
```

Tests (in `backend`, with `.venv` activated):

```sh
python -m pytest
```

Coverage — `backend/coverage/html/index.html`:

```sh
python -m pytest --cov=app --cov-report=term-missing --cov-report=html
```
