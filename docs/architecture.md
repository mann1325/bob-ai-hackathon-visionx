# Architecture

# SignalTrace System Architecture

## 1. Complete Architecture

```text
══════════════════════════════════════════════
             PRIMARY SIGNAL ENGINE
══════════════════════════════════════════════

Official FDA FAERS Quarterly Data
                │
                ▼
      Data Import / Processing
                │
                ▼
     Machine-Geist Foundation
                │
                ▼
       Signal Detection Engine
                │
       ┌────────┼─────────┐
       ▼        ▼         ▼
      PRR      ROR      Trends
                │
                ▼
       Candidate Signal Store


══════════════════════════════════════════════
            SIGNALTRACE PLATFORM
══════════════════════════════════════════════

                Candidate Signal
                       │
                       ▼
                Evidence Dashboard
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   Case Quality   Duplicate Triage   Signal Metrics
        │              │              │
        └──────────────┼──────────────┘
                       ▼
                Structured Evidence
                       │
                       ▼
                    Groq AI
                       │
                       ▼
              Evidence Explanation
                       │
                       ▼
          Regulatory Rule Engine
                       │
                       ▼
        Potential Documents for Review
                       │
                       ▼
              Gemini Document AI
                       │
                       ▼
            Potential Coverage Gap
                       │
                       ▼
                  HUMAN REVIEW


══════════════════════════════════════════════
          OPTIONAL LIVE / SEARCH LAYER
══════════════════════════════════════════════

                  User Search
                       │
                       ▼
                   openFDA API
                       │
                       ▼
          Quick / Live Data Exploration
```

---

# 2. Primary Signal Engine

## Data Source

The primary source is official FDA FAERS quarterly data.

```text
Quarterly Dataset
       ↓
ETL / Processing
       ↓
Normalized Data
       ↓
Drug–Event Pairs
       ↓
Signal Calculations
```

The system should support reproducible analysis against a defined dataset release.

---

## Machine-Geist Foundation (provenance unverified)

Project materials describe Machine-Geist as the starting repository/foundation,
but the exact repository, version, reused components, and attribution could not
be verified. The current signal-detection implementation is SignalTrace-owned.

Before modifications:

1. Analyze the repository.
2. Identify the FAERS ingestion pipeline.
3. Identify signal calculation modules.
4. Identify reusable data models.
5. Preserve validated logic where possible.

---

# 3. Signal Engine

The deterministic signal engine is responsible for:

- Drug-event pair generation.
- Contingency-table generation.
- PRR.
- ROR where implemented.
- Supporting report counts.
- Trend calculations.
- Candidate signal ranking.

Core principle:

```text
Historical Data
       +
Deterministic Code
       ↓
Verifiable Metrics
       ↓
Candidate Signal
```

AI does not generate the statistical facts.

---

# 4. SignalTrace Application Layer

## Frontend

Recommended:

```text
Next.js
React
TypeScript
```

Features:

- Drug search.
- Signal dashboard.
- Signal detail page.
- Evidence visualization.
- AI investigation panel.
- Regulatory impact panel.
- Document upload.
- Document analysis results.

---

## Backend

Recommended:

```text
FastAPI
Python
```

Responsibilities:

- Serve processed signal data.
- Manage candidate signals.
- Run investigation logic.
- Perform case-quality checks.
- Perform duplicate triage.
- Apply regulatory rules.
- Call Groq.
- Call Gemini.
- Optionally call openFDA.

---

# 5. Database

Recommended:

```text
PostgreSQL
```

Hackathon option:

```text
Supabase PostgreSQL
```

Suggested tables:

```text
faers_quarterly_metadata
processed_reports
drug_event_pairs
signals
signal_metrics
case_quality
duplicate_candidates
regulatory_rules
document_uploads
document_analysis
ai_summaries
```

---

# 6. Optional openFDA Layer

openFDA is intentionally separated from the primary signal engine.

```text
Frontend Search
       ↓
Backend
       ↓
openFDA API
       ↓
Quick / Live Lookup
```

Possible uses:

- Drug search.
- Quick exploration.
- Demonstration of live API integration.
- Additional recent information.

The primary PRR/ROR pipeline should not depend on openFDA availability.

---

# 7. Groq Layer

Input:

```text
Structured Signal Facts
```

Output:

```text
Evidence Explanation
Investigation Summary
Limitations
Suggested Questions
```

---

# 8. Regulatory Rule Engine

```text
Candidate Signal
       ↓
Signal Characteristics
       ↓
Deterministic Rules
       ↓
Potential Review Areas
       ↓
Explainable Result
```

Rules remain separate from AI prompts.

---

# 9. Gemini Document Intelligence

```text
Document Upload
       +
Candidate Signal Context
       ↓
Document Processing
       ↓
Gemini Analysis
       ↓
Relevant Sections
Existing Coverage
Potential Gap
       ↓
Human Review
```

---

# 10. IBM Bob Development Architecture

IBM Bob exists on the development side only.

```text
OUR DEVELOPMENT TEAM
         │
         ▼
      IBM BOB
         │
   ┌─────┼─────┐
   ▼     ▼     ▼
 Ask    Plan  Agent
   │     │     │
   └─────┼─────┘
         ▼
      Testing
         ▼
      Review
         ▼
    SignalTrace
```
