# SignalTrace Backend

FastAPI backend for the SignalTrace pharmacovigilance decision-support platform.

## Responsibilities

- Serve deterministic signal data from the Data/ML pipeline (Member 1 & 2)
- Investigation APIs (case quality, duplicate triage)
- Groq evidence explanation (structured facts → explanation)
- Deterministic regulatory rule engine
- Document upload and Gemini analysis
- Optional openFDA live search

## Quick Start

```bash
cd src/backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
cp ../.env.example ../.env
# Edit ../.env with your values

uvicorn app.main:app --reload --port 8000
```

OpenAPI docs: http://localhost:8000/docs

Health check: http://localhost:8000/api/v1/health

## Database Migrations

Production schema changes are managed with Alembic. From `src/backend`, set
`DATABASE_URL` to the target PostgreSQL database and run:

```bash
alembic upgrade head
```

The application does not run `create_all()` on startup. The existing SQLite
development and test workflows remain unchanged.

## Environment Variables

See `src/.env.example`. Key variables:

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Phase 2+ | PostgreSQL / Supabase connection |
| `GROQ_API_KEY` | Phase 6+ | Groq evidence explanation |
| `GEMINI_API_KEY` | Phase 9+ | Document analysis |
| `OPENFDA_API_BASE_URL` | Optional | openFDA base URL |
| `OPENFDA_API_KEY` | Optional | openFDA API key |
| `CORS_ORIGINS` | Optional | Comma-separated frontend origins |

## Project Layout

```text
backend/
├── app/           # FastAPI application factory, config
├── api/v1/        # Versioned route handlers
├── services/      # Business logic
├── rules/         # Deterministic regulatory rule engine
├── ai/            # Groq and Gemini clients
├── database/      # DB connection and repositories
└── tests/         # pytest suite
```

Shared API schemas live in `src/shared/schemas/` (team-owned — propose changes, do not modify unilaterally).

## Running Tests

```bash
cd src/backend
pytest -v
```

## Ownership

This directory is owned by **Member 3 (Backend & NLP)**. Do not modify Member 1 (data), Member 2 (ML), or Member 4 (frontend) code from here.
