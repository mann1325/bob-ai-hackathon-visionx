# Setup Guide

# SignalTrace

## 1. Project Prerequisites

Install:

```text
Git
Python 3.11+
Node.js 20+
```

Recommended:

```text
PostgreSQL or Supabase
VS Code
IBM Bob
```

---

# 2. Repository Setup

Project materials describe a selected Machine-Geist signal-detection
repository, but its exact source and reuse are not verifiable in this
repository. The current pipeline should be treated as SignalTrace-owned until
that provenance is established.

Initial workflow:

```text
Clone Repository
      ↓
Open in IBM Bob
      ↓
Ask Mode Analysis
      ↓
Understand Existing Pipeline
      ↓
Plan Mode
      ↓
Approve Changes
      ↓
Agent Mode Implementation
```

Do not begin by immediately rewriting the repository.

---

# 3. Suggested Project Structure

```text
signaltrace/
│
├── signal_engine/
│   ├── ingestion/
│   ├── processing/
│   ├── metrics/
│   └── ranking/
│
├── backend/
│   ├── api/
│   ├── services/
│   ├── rules/
│   ├── ai/
│   └── database/
│
├── frontend/
│
├── data/
│   ├── raw/
│   └── processed/
│
├── docs/
│   ├── problem-statement.md
│   ├── solution-overview.md
│   ├── architecture.md
│   ├── setup-guide.md
│   └── PRD.md
│
└── README.md
```

The exact structure should respect useful existing repository architecture.

---

# 4. FDA Quarterly Data Setup

The primary signal engine uses official FDA FAERS quarterly data.

Recommended workflow:

```text
Quarterly Data Download
        ↓
Store Raw Files
        ↓
Parse / Normalize
        ↓
Load into Database
        ↓
Create Drug–Event Dataset
        ↓
Run Signal Detection
```

Keep metadata about:

- Dataset release.
- Quarter.
- Import date.
- Processing version.

This helps reproducibility.

---

# 5. Signal Engine Setup

The original Machine-Geist source is not verifiable from this repository; do
not claim a specific upstream source or code reuse without external evidence.

Before changing signal logic:

## Step 1 — Ask Mode

Example:

> Analyze this repository and explain the complete FAERS data pipeline, important modules, data models, signal-detection calculations, inputs, outputs, and reusable components. Do not modify code.

## Step 2 — Plan Mode

Example:

> We are extending this repository into SignalTrace. Keep the existing signal-detection foundation where appropriate. Create a phased plan for adding a web application, evidence investigation, case-quality analysis, potential duplicate triage, Groq explanation, regulatory rules, Gemini document analysis, and optional openFDA search. Identify every file likely to change. Do not modify code.

## Step 3 — Team Review

Review:

- Reusable code.
- Data assumptions.
- Planned changes.
- Risks.
- File ownership.

## Step 4 — Agent Mode

Implement only the approved feature.

---

# 6. Backend Setup

Recommended:

```text
FastAPI
Python
```

Typical setup:

```bash
cd backend
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

macOS/Linux:

```bash
source venv/bin/activate
```

Install:

```bash
pip install -r requirements.txt
```

Run:

```bash
uvicorn app.main:app --reload
```

---

# 7. Frontend Setup

Recommended:

```text
Next.js
React
TypeScript
```

Typical setup:

```bash
cd frontend
npm install
npm run dev
```

---

# 8. Environment Variables

Example:

```env
DATABASE_URL=your_database_connection

GROQ_API_KEY=your_groq_key

GEMINI_API_KEY=your_gemini_key

OPENFDA_API_BASE_URL=https://api.fda.gov
OPENFDA_API_KEY=
```

openFDA credentials are optional for the primary signal engine.

Never commit `.env`.

---

# 9. Development Phases

## Phase 1 — Repository Understanding

Use IBM Bob Ask Mode.

Output:

- Architecture map.
- Signal pipeline understanding.
- Reusable components.
- Risk list.

## Phase 2 — Dataset Pipeline

Set up:

```text
FDA Quarterly Data
       ↓
Import
       ↓
Normalization
       ↓
Database / Processed Dataset
```

## Phase 3 — Signal Engine

Validate:

```text
Drug–Event Pairs
PRR
ROR
Counts
Trends
Ranking
```

## Phase 4 — SignalTrace API

Expose:

- Drug search.
- Candidate signals.
- Signal details.
- Evidence data.

## Phase 5 — Frontend

Build:

- Dashboard.
- Signal table.
- Signal detail view.

## Phase 6 — Investigation Features

Add:

- Case quality.
- Potential duplicate triage.

## Phase 7 — Groq

Add AI explanation using backend-generated facts.

## Phase 8 — Regulatory Rules

Add deterministic signal-to-document mapping.

## Phase 9 — Gemini

Add document upload and analysis.

## Phase 10 — Optional openFDA

Add as a separate live/search feature.

---

# 10. Team Collaboration Rules

- One owner per major feature.
- Do not edit the same file simultaneously.
- Shared schemas must be agreed before changing.
- Do not silently modify API contracts.
- Use branches.
- Review before merging.
- Keep commits small and logical.

---

# 11. Testing Checklist

## Quarterly Data

```text
[ ] Dataset imports correctly
[ ] Quarter metadata is stored
[ ] Data normalization works
```

## Signal Engine

```text
[ ] Drug-event pairs work
[ ] PRR is correct
[ ] ROR is correct where implemented
[ ] Counts are correct
[ ] Ranking works
```

## Investigation

```text
[ ] Quality issues are identified
[ ] Potential duplicates are explainable
[ ] No reports are automatically deleted
```

## AI

```text
[ ] Groq receives structured facts
[ ] Groq does not calculate core metrics
[ ] Gemini identifies relevant content
[ ] AI output is clearly labelled as assistance
```

## openFDA

```text
[ ] Optional search works
[ ] API failure does not break core signal engine
```

---

# 12. Final Demo Flow

```text
1. Select a Drug
        ↓
2. Show Historical FDA Quarterly Data Basis
        ↓
3. Show Candidate Signal
        ↓
4. Show PRR / ROR / Counts / Trend
        ↓
5. Show Case Quality and Duplicate Triage
        ↓
6. Groq Explains Evidence
        ↓
7. Regulatory Rule Engine Maps Review Areas
        ↓
8. Upload Regulatory / Safety Document
        ↓
9. Gemini Finds Relevant Content
        ↓
10. Show Potential Coverage Gap
        ↓
11. HUMAN REVIEW REQUIRED
```

Optional demonstration:

```text
User Search
      ↓
openFDA
      ↓
Live / Quick Data Exploration
```
