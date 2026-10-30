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
