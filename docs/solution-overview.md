# SignalTrace Solution Overview

## One-Line Description

SignalTrace is an AI-assisted pharmacovigilance decision-support platform that connects deterministic FDA FAERS candidate-signal analysis with structured evidence investigation, potential regulatory review, document intelligence, and human review.

## Implemented Solution

SignalTrace is organized around a reviewer workflow rather than a single score:

```text
Signal Queue
    |
    v
Investigation Overview
    |
    +--> Evidence Explorer
    +--> Case Quality
    +--> Potential Duplicate Triage
    +--> Reporting Trend
    +--> Groq Evidence Explanation
    +--> Regulatory Review
    +--> Gemini Document Intelligence
    |
    v
Human Review
```

The current database contains the imported **2026Q1** dataset. The demonstrated trend use case includes historical **2025Q4** values extracted from the official FDA archive; those values should not be described as a full report-level 2025Q4 import into `processed_reports`.

## Investigation Workflow

### 1. Signal Queue

The queue presents candidate drug-event signals with search, priority and review-status filtering, sorting, pagination, responsive cards, and an explicit investigation action.

### 2. Overview and Investigation Summary

The overview keeps the selected drug, event, signal ID, priority, review status, release, report count, PRR, ROR, chi-square, and available trend score in context. Investigation Summary adds the why-flagged explanation, provenance, limitations, and progressively disclosed technical sections.

### 3. Evidence Explorer

Evidence Explorer lists supporting processed FAERS reports. Users can inspect report ID, drug, reactions, seriousness, date, quarter, and source. Detail opens in a desktop drawer or mobile sheet. Seriousness is based on official FAERS outcome evidence where available.

### 4. Case Quality

Case Quality reports completeness and data limitations, including quality score, missing age, missing sex, missing event date, quality flags, and indicators.

### 5. Potential Duplicate Triage

Duplicate Triage presents potential duplicate candidates for human assessment. Results include candidate status, similarity, matched fields, report pair, date proximity, and rationale. The system does not automatically delete or merge reports.

### 6. Reporting Trend

The shared trend scorer evaluates valid quarterly count points. It requires at least two valid points and returns a normalized slope-based score; otherwise the score is unavailable. The score describes reporting behavior, not disease incidence or causality.

### 7. Grounded AI Evidence Explanation

The Groq explanation service builds a structured fact map from backend evidence, including statistical metrics, trend data, quality information, potential duplicate counts, limitations, and regulatory matches. Groq returns:

- Why the candidate was flagged.
- Evidence summary.
- Limitations.
- Suggested investigation questions.

The AI does not calculate PRR, ROR, chi-square, report counts, or final risk decisions. Its output is advisory and requires human validation.

### 8. Regulatory Review

The deterministic rule engine evaluates signal facts and returns Potential Review Areas and rule matches. Supported results may include Product Label, Reference Safety Information, Risk Management Plan, and other areas represented by the active rules. These results are triage guidance, not confirmed regulatory deficiencies or final decisions.

### 9. Document Intelligence

Users can upload PDF, DOCX, or TXT safety/regulatory documents. The backend extracts text and Gemini analyzes the document against signal context to identify relevant sections, existing related content, and potential coverage gaps. Results require professional human review. The current dossier-append action is not available.

### 10. Human Review

Human Review provides:

- Review status: not started, in review, or reviewed.
- Six-item evidence checklist.
- Reviewer notes.
- Human-authored conclusion.
- Save feedback and timestamp.
- Confirmation before marking a signal reviewed.

## Round 2 Improvements

The implemented Round 2 frontend improves the investigation workflow without replacing the SignalTrace visual identity:

- Bounded investigation workspace for large screens.
- Responsive Signal Queue table/cards.
- Persistent investigation context header.
- Investigation tabs with preserved component state during switching.
- Progressive disclosure for dense summary content.
- Evidence report drawer and mobile sheet behavior.
- Compact document upload and AI empty states.
- Quality/duplicate layout that collapses at narrower widths.
- Human-review progress and save-state visibility.
- Original light SignalTrace theme, navy/royal-blue branding, pastel surfaces, and medicine splash preserved.

## Technology Stack

| Layer | Implementation |
|---|---|
| Data ingestion | Python FAERS ASCII loaders, normalization, case processing, pair generation |
| Signal computation | Python deterministic metrics and candidate detection; PRR, ROR, chi-square, counts, trend |
| Database | SQLAlchemy and Alembic with PostgreSQL-compatible deployment |
| API | FastAPI, Pydantic schemas, Uvicorn |
| Frontend | Next.js 16, React 19, TypeScript |
| AI | Groq evidence explanation; Gemini document analysis |
| Auxiliary lookup | openFDA API |
| Verification | pytest backend suite, ESLint, Next.js production build |

## Evidence and Safeguards

SignalTrace intentionally separates:

```text
Deterministic backend facts
            |
            +--> Human-readable UI evidence
            +--> Groq advisory explanation
            +--> Deterministic regulatory rules
            +--> Gemini document assistance
            |
            v
Qualified human review
```

The system does not claim causality, does not declare a medicine unsafe, does not diagnose patients, does not make automatic regulatory submissions, and does not automatically resolve duplicate candidates. Human review remains the final control point.

## Current Status

The current repository contains the implemented end-to-end investigation workspace, FastAPI APIs, deterministic pipeline and scoring utilities, PostgreSQL-compatible persistence, Groq/Gemini integration paths, openFDA lookup, responsive frontend, developer isolation routes, and automated tests. The populated application dataset is 2026Q1; 2025Q4 is limited to the demonstrated historical trend use case described above.
