# SignalTrace Setup Guide

This guide matches the current repository layout and runtime configuration.

## Prerequisites

- Git
- Python 3.11 or newer
- Node.js suitable for the Next.js 16 project
- PostgreSQL-compatible database for the populated application, such as Neon/PostgreSQL
- API keys for Groq and Gemini if those integrations are to be used

The automated backend tests use an in-memory SQLite database. Production and populated local deployments use the configured `DATABASE_URL`.

## Repository Layout

```text
src/
  backend/       FastAPI application
  frontend/      Next.js application
  data_pipeline/ FAERS ingestion and signal-detection pipeline
  ml/            scoring, enrichment, and import utilities
  shared/        shared schemas
  data/          local data/database artifacts

docs/
  architecture.md
  problem-statement.md
  setup-guide.md
  solution-overview.md
```

## Backend Installation

From the repository root:

```powershell
cd src/backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

On macOS/Linux:

```bash
cd src/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The backend requirements include FastAPI, Uvicorn, Pydantic Settings, SQLAlchemy, PostgreSQL support, Alembic, multipart upload support, PDF/DOCX extraction, and pytest tooling.

## Backend Environment

The backend reads its environment file from `src/.env`.

Example:

```env
APP_ENV=development
APP_PORT=8000
APP_NAME=SignalTrace API
DATABASE_URL=postgresql://user:password@host:5432/database
GROQ_API_KEY=
GEMINI_API_KEY=
OPENFDA_API_BASE_URL=https://api.fda.gov
OPENFDA_API_KEY=
UPLOAD_DIR=data/uploads
MAX_UPLOAD_SIZE_BYTES=10485760
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

`DATABASE_URL` is required for a populated PostgreSQL/Neon deployment. `GROQ_API_KEY`, `GEMINI_API_KEY`, and the optional openFDA key are only required for their respective integrations. Do not commit credentials.

## Database Migrations

From `src/backend`, run migrations against the configured PostgreSQL-compatible database:

```powershell
alembic upgrade head
```

The application does not run `create_all()` on startup. Alembic owns production schema changes.

## Start the Backend

```powershell
cd src/backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Useful endpoints:

- API docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/api/v1/health`
- Signal list: `http://127.0.0.1:8000/api/v1/signals`

## Frontend Installation

In a second terminal:

```powershell
cd src/frontend
npm install
```

The frontend uses Next.js 16.3.5, React 19.2.8, TypeScript, and ESLint. No additional UI framework is required.

## Frontend Environment

The current local frontend configuration is:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCKS=false
```

`NEXT_PUBLIC_USE_MOCKS=false` selects the real FastAPI adapter. If it is not exactly `false`, the frontend defaults to its typed `MockAdapter`, which is useful for the `/dev/*` isolation routes.

Start the frontend:

```powershell
cd src/frontend
npm run dev
```

Open `http://localhost:3000`.

Other available scripts:

```powershell
npm run lint
npm run build
npm run start
```

## Data Pipeline

The primary pipeline consumes the official FDA FAERS quarterly ASCII files. From `src`, with the required quarter files available:

```powershell
python -m data_pipeline.run_pipeline --data-dir <faers-quarter-directory> --output-dir <pipeline-output> --quarter 2026Q1
```

The runner produces normalized reports, drug-event pairs, signal metrics, candidate signals, quality output, and a provenance manifest. Database import utilities in `src/ml` reuse the backend models.

The current populated database dataset is **2026Q1**. Historical **2025Q4** values used for the demonstrated trend calculation were extracted from the official FDA archive for that use case; do not treat them as a full `processed_reports` import.

## Tests

Backend tests:

```powershell
cd src/backend
pytest -q
```

Frontend checks:

```powershell
cd src/frontend
npm run lint
npm run build
```

## Common Local Issues

- If the frontend shows no live signals, confirm the backend is running, `NEXT_PUBLIC_API_URL` points to it, CORS includes the frontend origin, and `NEXT_PUBLIC_USE_MOCKS=false` is loaded by the Next.js process.
- Restart the frontend after changing `NEXT_PUBLIC_*` variables because they are embedded by Next.js at build/dev-server startup.
- If AI actions are unavailable, check the corresponding Groq or Gemini key; the deterministic signal and review APIs do not require those AI calls.
