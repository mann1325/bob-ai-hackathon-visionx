# SignalTrace Problem Statement

## The Pharmacovigilance Problem

Pharmacovigilance teams use large collections of adverse-event reports to identify drug-event combinations that deserve investigation. Official FDA FAERS quarterly data provides an important historical source, but a statistical candidate signal is not a conclusion. It is a starting point for expert review.

After detection, reviewers need to answer several connected questions:

- Why was this drug-event pair flagged?
- How strong are the PRR, ROR, and chi-square results?
- How many supporting reports are available?
- Are the cases complete enough to interpret?
- Are there potential duplicate candidates?
- What reporting behavior is visible across available quarters?
- Which regulatory documents may warrant review?
- Does an uploaded document already contain relevant safety information?
- What conclusion should a qualified reviewer record?

In practice, these steps may be spread across data exports, scripts, spreadsheets, case review tools, and document repositories. That fragmentation makes it harder to preserve provenance and maintain a clear investigation trail.

## The Core Gap

```text
FAERS data
   |
   v
Candidate signal
   |
   v
Fragmented evidence and document investigation
   |
   v
Manual regulatory handoff and human conclusion
```

The gap is not simply signal detection. It is the transition from a transparent candidate signal to a structured, reviewable evidence package and a disciplined human decision workflow.

## SignalTrace's Solution

SignalTrace connects the investigation steps in one workspace:

```text
Official FDA FAERS data
        |
        v
Deterministic candidate signal detection
(PRR, ROR, chi-square, counts, trend data)
        |
        v
Signal Queue
        |
        v
Overview and Investigation Summary
        |
        +--> Supporting reports and report detail
        +--> Case Quality
        +--> Potential Duplicate Triage
        +--> Reporting Trend
        +--> Groq evidence explanation
        +--> Deterministic regulatory Potential Review Areas
        +--> Gemini document intelligence
        |
        v
Human Review and conclusion
```

The application uses deterministic backend calculations for statistical facts, rule-based logic for Potential Review Areas, Groq for grounded explanation, and Gemini for uploaded-document analysis. Each layer is labeled according to its role and remains subject to human validation.

## Dataset Scope

The current imported database dataset is **2026Q1**. For the demonstrated reporting-trend use case, historical **2025Q4** values were extracted from the official FDA archive. That historical trend input is not a claim that the full 2025Q4 report-level data has been imported into `processed_reports`.

## Safety Boundary

SignalTrace does not:

- Establish causality between a drug and an event.
- Establish incidence or prove that a medicine is unsafe.
- Diagnose or treat patients.
- Replace qualified pharmacovigilance or regulatory professionals.
- Make final regulatory decisions.
- Automatically delete potential duplicates.
- Automatically modify or submit regulatory documents.

FAERS spontaneous reports are subject to reporting bias and other limitations. Candidate signals, potential duplicate candidates, AI explanations, regulatory Potential Review Areas, and document coverage gaps all require professional review.
