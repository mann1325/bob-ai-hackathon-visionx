# SignalTrace

SignalTrace is an AI-assisted pharmacovigilance decision-support workspace that takes candidate drug-event signals from official FDA FAERS data through evidence investigation, potential regulatory review, document intelligence, and qualified human review.

## Problem

Pharmacovigilance teams can detect unusual drug-event associations, but detection is only the beginning. Reviewers must understand the statistical evidence, inspect supporting reports, assess case completeness, triage possible duplicates, examine reporting behavior over time, identify potential regulatory review areas, and record a defensible human assessment. These tasks are often spread across datasets, scripts, spreadsheets, reports, and document review tools.

SignalTrace connects those steps without turning an AI output into a safety or regulatory decision.

## Solution Workflow

```text
Official FDA FAERS quarterly data
            |
            v
Deterministic ingestion and signal detection
(PRR, ROR, chi-square, report counts, trend data)
            |
            v
Candidate Signal Queue
            |
            v
Investigation workspace
  Overview | Evidence | Quality / Duplicates
  Regulatory | Documents | Human Review
            |
            v
Human-authored review and conclusion
```

The current demonstrated dataset imported into the Neon/PostgreSQL-compatible database is **2026Q1**. Historical **2025Q4** values used for the demonstrated reporting-trend calculation were extracted from the official FDA archive for that trend use case; they are not represented as a full 2025Q4 report-level import in `processed_reports`.

## Key Features

- **Signal detection:** deterministic drug-event analysis with PRR, ROR, chi-square, supporting report counts, ranking, and reporting-trend data.
- **Signal Queue:** searchable, filterable, sortable candidate signal list with priority, review status, pagination, and investigation entry points.
- **Investigation Summary:** compact signal context, why the signal was flagged, provenance, limitations, and progressively disclosed supporting details.
- **Evidence Explorer:** paginated supporting FAERS reports with seriousness derived from official outcome codes and report detail inspection.
- **Case Quality:** completeness score, missing age/sex/event-date counts, quality flags, and indicators.
- **Duplicate Triage:** potential duplicate candidates with similarity, matched fields, date proximity, rationale, and human-review status. No automatic deletion occurs.
- **Reporting Trend:** computed trend score when at least two valid trend points are available; otherwise the value remains unavailable.
- **Grounded AI Evidence Explanation:** Groq receives backend-computed evidence facts and returns an advisory explanation, limitations, and suggested investigation questions.
- **Regulatory Review:** deterministic rules return Potential Review Areas and rule matches for documents such as Product Label, RSI, and RMP where supported by the data. These are not confirmed deficiencies.
- **Document Intelligence:** PDF, DOCX, and TXT upload, text extraction, and Gemini-assisted relevant-section and potential-coverage-gap analysis.
- **Human Review:** reviewer status, six evidence checklist items, notes, human-authored conclusion, save feedback, and audit timestamps.
- **Auxiliary openFDA search:** a separate live lookup utility; it is not part of the primary signal-detection calculation.

## Architecture

```mermaid
graph TD
  A[FDA FAERS quarterly files] --> B[src/data_pipeline]
  B --> C[Normalized reports and candidate signal artifacts]
  C --> D[src/ml enrichment and import utilities]
  D --> E[(PostgreSQL / Neon-compatible database)]
  E --> F[FastAPI /api/v1]
  F --> G[Next.js React investigation workspace]
  F --> H[Groq grounded explanation]
  F --> I[Deterministic regulatory rules]
  F --> J[Gemini document analysis]
  G --> K[Human review]
```

### Repository structure

```text
src/
  backend/       FastAPI app, services, rules, AI clients, database, tests
  data_pipeline/ FAERS loading, normalization, metrics, signal detection
  ml/            trend/risk/ranking/enrichment and database import utilities
  frontend/      Next.js App Router UI and API adapters
  shared/        shared schemas and API contracts

docs/            Project documentation
data/            Local database and data artifacts
demo/            Demo links and screenshots
presentation/    Presentation materials
```

### API and frontend boundaries

The backend owns data access, deterministic calculations, investigation services, AI calls, document processing, regulatory rules, and review persistence. The frontend uses a typed `ApiClient` with a real adapter for FastAPI and a mock adapter for isolated demonstrations. No frontend calculation replaces backend signal logic.

## Tech Stack

| Area | Current implementation |
|---|---|
| Backend | Python, FastAPI, Uvicorn, Pydantic Settings |
| Frontend | Next.js 16, React 19, TypeScript |
| Database | SQLAlchemy, Alembic, PostgreSQL-compatible deployment; SQLite is used by tests/development paths where configured |
| Signal/data pipeline | Python, pandas, official FDA FAERS quarterly ASCII files |
| AI services | Groq for grounded evidence explanation; Gemini for document analysis |
| Auxiliary data | openFDA API live lookup |
| Testing | pytest, pytest-asyncio, frontend ESLint and Next.js build |

## Data and Statistical Evidence

The pipeline reads official FDA FAERS quarterly ASCII tables, normalizes cases and drug-event pairs, computes deterministic metrics, and exports/imports candidate signals and supporting metrics.

- **PRR:** proportional reporting ratio.
- **ROR:** reporting odds ratio where available.
- **Chi-square:** contingency-table signal-strength statistic.
- **Trend score:** a normalized slope over valid quarterly counts, calculated by the shared `compute_trend_score()` implementation. Fewer than two valid points produce `null`/`--`.

Spontaneous FAERS reports are useful for signal detection but do not establish causality, incidence, or drug safety.

## Setup

### Prerequisites

- Git
- Python 3.11 or newer
- Node.js compatible with the Next.js 16 project
- PostgreSQL-compatible database for the populated application, such as Neon/PostgreSQL
- API keys only for the optional Groq, Gemini, and openFDA-backed capabilities

### Backend

```powershell
cd src/backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `src/.env` with the settings needed by the current backend:

```env
APP_ENV=development
APP_PORT=8000
DATABASE_URL=postgresql://user:password@host:5432/database
GROQ_API_KEY=
GEMINI_API_KEY=
OPENFDA_API_BASE_URL=https://api.fda.gov
OPENFDA_API_KEY=
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
UPLOAD_DIR=data/uploads
MAX_UPLOAD_SIZE_BYTES=10485760
```

Run migrations against the configured PostgreSQL database:

```powershell
cd src/backend
alembic upgrade head
```

Start the API:

```powershell
cd src/backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API documentation: `http://127.0.0.1:8000/docs`  
Health check: `http://127.0.0.1:8000/api/v1/health`

### Frontend

In a second terminal:

```powershell
cd src/frontend
npm install
```

The current frontend environment uses:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCKS=false
```

`NEXT_PUBLIC_USE_MOCKS=false` selects the real FastAPI adapter. When the variable is not set to `false`, the frontend defaults to its typed mock adapter for isolated demonstrations.

Start the frontend:

```powershell
cd src/frontend
npm run dev
```

Open `http://localhost:3000`.

### Data pipeline

The deterministic pipeline can be run from the `src` directory when the official quarterly input files are available:

```powershell
cd src
python -m data_pipeline.run_pipeline --data-dir <faers-quarter-directory> --output-dir <pipeline-output> --quarter 2026Q1
```

The pipeline writes normalized reports, drug-event pairs, signal metrics, candidate signals, quality information, and a provenance manifest. Database import utilities in `src/ml` reuse the backend SQLAlchemy models and do not replace the backend API.

## Round 2 Improvements

The current Round 2 frontend includes:

- A reviewer-oriented Signal Queue with search, priority/review filters, sorting, pagination, and responsive cards.
- A persistent investigation header with drug, event, signal ID, priority, review status, release, and report count.
- Tabbed Overview, Evidence, Quality / Duplicates, Regulatory, Documents, and Human Review sections.
- Progressive disclosure for dense investigation details.
- Evidence report drawer behavior with mobile sheet layout, close controls, and Escape handling.
- Compact, bounded investigation layouts that avoid desktop stretching and mobile overflow.
- A persistent medicine-themed SignalTrace startup animation without the previous forced multi-second wait.
- Human-review progress, save state, and confirmation before marking a signal reviewed.

## Safety & Limitations

SignalTrace is decision support, not an autonomous safety or regulatory system.

- Candidate signals require qualified professional pharmacovigilance review.
- FAERS spontaneous reports do not establish causality, incidence, or proof that a medicine is unsafe.
- PRR, ROR, chi-square, counts, and trend values are deterministic backend outputs; they are not generated by AI.
- Groq explanations are grounded in backend-computed facts, advisory, and require validation.
- Gemini document results identify relevant sections and potential coverage gaps; they are not confirmed deficiencies.
- Regulatory rule matches are Potential Review Areas, not final regulatory decisions.
- Potential duplicate results are candidates for human triage; reports are never automatically deleted.
- The dossier-append action is not available in the current version.
- The system does not diagnose patients, establish causality, make final regulatory decisions, modify documents automatically, or submit information to regulators.

## Current Project Status

The implemented application includes the end-to-end candidate-signal investigation workflow described above. The imported database dataset is 2026Q1. The demonstrated 2025Q4 historical trend input is limited to trend use and is not a full report-level import. Backend tests, frontend lint, and the frontend production build are part of the current verification workflow.

## Related Documentation

- [Architecture](docs/architecture.md)
- [Problem statement](docs/problem-statement.md)
- [Setup guide](docs/setup-guide.md)
- [Solution overview](docs/solution-overview.md)
- [API contract](src/backend/shared-schemas/api-contract.yaml)
