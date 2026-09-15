# SignalTrace — Product Requirements Document (PRD)

**Version:** 3.0
**Project Type:** Hackathon MVP
**Status:** Development Ready

---

# 1. Product Overview

## Product Name

**SignalTrace**

## One-Line Description

**SignalTrace is an AI-assisted pharmacovigilance decision-support platform that uses official FDA FAERS quarterly data and a Machine-Geist signal-detection foundation to identify candidate drug safety signals, investigate supporting evidence, and assess potential regulatory document impact.**

---

# 2. Product Strategy

SignalTrace uses a two-layer data strategy.

## Primary Layer — Signal Engine

```text
Official FDA FAERS Quarterly Data
              +
Machine-Geist Foundation
              ↓
Deterministic Signal Detection
              ↓
Candidate Safety Signals
```

This is the primary analytical foundation.

## Optional Layer — openFDA

```text
User Search
     ↓
openFDA API
     ↓
Quick / Live Data Lookup
```

openFDA is optional and does not power the core PRR/ROR calculations.

---

# 3. Problem

Signal detection can identify candidate safety concerns, but the investigation and regulatory handoff after detection can remain fragmented.

SignalTrace addresses:

```text
Signal Detection
       ↓
Evidence Understanding
       ↓
AI-Assisted Investigation
       ↓
Potential Regulatory Mapping
       ↓
Document Intelligence
       ↓
Human Review
```

---

# 4. Goals

The MVP must:

1. Process official FDA quarterly FAERS data.
2. Reuse and extend a Machine-Geist signal-detection foundation.
3. Detect candidate drug-event signals.
4. Display transparent supporting metrics.
5. Highlight data-quality concerns.
6. Identify potential duplicate candidates.
7. Use Groq to explain evidence.
8. Use deterministic rules for regulatory impact mapping.
9. Use Gemini to analyze uploaded documents.
10. Keep human review at the center.

---

# 5. Non-Goals

SignalTrace does not:

- Prove causality.
- Diagnose patients.
- Confirm that a drug is unsafe.
- Replace professional safety review.
- Automatically modify documents.
- Automatically submit regulatory information.
- Make final regulatory decisions.

---

# 6. Primary Data Requirements

## FR-1: FDA Quarterly Dataset

The system must support official FDA FAERS quarterly data as the primary dataset.

The system should record:

- Dataset release.
- Quarter.
- Import date.
- Processing version.

---

# 7. Signal Engine Requirements

## FR-2: Machine-Geist Foundation

The selected Machine-Geist repository should be analyzed and reused where appropriate.

The team must:

- Understand existing data flow.
- Identify signal logic.
- Preserve useful validated components.
- Avoid unnecessary rewrites.

## FR-3: Deterministic Signal Metrics

The engine should support:

- Drug-event pairs.
- Supporting report counts.
- PRR.
- ROR where implemented.
- Trend information.
- Candidate ranking.

AI must not generate the core statistical metrics.

---

# 8. Investigation Requirements

## FR-4: Signal Evidence

A selected signal should display:

- Drug.
- Event.
- Report count.
- PRR.
- ROR where available.
- Trend.
- Relevant evidence.
- Known limitations.

## FR-5: Case Quality

The system should identify incomplete information and provide explainable quality indicators.

## FR-6: Potential Duplicate Triage

The system should identify potential duplicate candidates.

Potential duplicate ≠ confirmed duplicate.

No automatic deletion is allowed.

---

# 9. Groq Requirements

## FR-7: AI Evidence Explanation

Groq may:

- Explain why a signal was flagged.
- Summarize structured evidence.
- Highlight limitations.
- Suggest investigation questions.

Required flow:

```text
Backend Facts
      ↓
Groq
      ↓
Explanation
```

---

# 10. Regulatory Rule Requirements

## FR-8: Signal-to-Document Mapping

A deterministic rule engine maps signal characteristics to potential review areas.

Possible outputs:

- Product Label.
- Reference Safety Information.
- PSUR/PBRER.
- Risk Management Plan.
- Relevant CTD safety content.

Rules must be traceable and separate from AI prompts.

---

# 11. Gemini Requirements

## FR-9: Document Intelligence

The system should support document upload.

Gemini may identify:

- Relevant sections.
- Existing related information.
- Possible inconsistencies.
- Potential coverage gaps.

Output must be presented as assistance requiring human review.

---

# 12. Optional openFDA Requirements

## FR-10: Live / Search Layer

openFDA may support:

- Drug lookup.
- Quick search.
- Live data exploration.
- Additional demonstration features.

Failure of openFDA must not break the core signal engine.

---

# 13. System Architecture

```text
FDA Quarterly Data
       +
Machine-Geist
       ↓
Primary Signal Engine
       ↓
Candidate Signal Database
       ↓
SignalTrace Platform
       ├── Evidence Dashboard
       ├── Case Quality
       ├── Duplicate Triage
       ├── Groq
       ├── Regulatory Rules
       └── Gemini
              ↓
          Human Review

Optional:
openFDA → Search / Live Data
```

---

# 14. Technology Stack

Recommended:

## Frontend

```text
Next.js
React
TypeScript
```

## Backend

```text
FastAPI
Python
```

## Database

```text
PostgreSQL / Supabase
```

## AI

```text
Groq API
Gemini API
```

## Data

```text
Official FDA FAERS Quarterly Data
openFDA Optional API
```

---

# 15. Development Approach

IBM Bob is a development-side tool.

It is not part of the production application.

Required workflow:

```text
Ask Mode
   ↓
Understand Repository
   ↓
Plan Mode
   ↓
Review Plan
   ↓
Agent Mode
   ↓
Implement Feature
   ↓
Test
   ↓
Review
   ↓
Commit
```

---

# 16. MVP Acceptance Criteria

```text
[ ] FDA quarterly data is processed
[ ] Machine-Geist signal pipeline is understood and integrated
[ ] Candidate signals are produced
[ ] Core metrics are visible
[ ] Case-quality concerns are visible
[ ] Potential duplicates are explainable
[ ] Groq explains structured evidence
[ ] Regulatory rules map review areas
[ ] Gemini analyzes uploaded documents
[ ] Human review warning is visible
[ ] openFDA works independently as optional search
```

---

# 17. Final Product Statement

> **SignalTrace extends traditional pharmacovigilance signal detection into a connected decision-support workflow. Using official FDA FAERS quarterly data and a Machine-Geist analytical foundation for reproducible candidate signal detection, it adds evidence investigation, AI-assisted explanation, regulatory rule mapping, and document intelligence to help human experts evaluate potential safety and regulatory impact.**
