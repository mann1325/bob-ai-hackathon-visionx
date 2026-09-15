# 🚀 SignalTrace

> AI-assisted pharmacovigilance decision-support platform — from candidate safety signal to potential regulatory impact.

---

## 👥 Team

| Field | Value |
|---|---|
| **Team Name** | VisionX |
| **Track** | AI |
| **Team Lead** | Sharanam Katwala — 24aiml063@charusat.edu.in |
| **Members** | Mann Shah — 24dce128@charusat.edu.in, Jiya Sadaria — 24aiml054@charusat.edu.in, Harshil Thakkar — 24aiml068@charusat.edu.in |

---

## 🎯 Problem Statement

Pharmacovigilance teams can detect candidate drug safety signals from FDA FAERS adverse-event data, but the work doesn't stop there — reviewers still need to check case quality, screen for duplicates, understand the statistical evidence, and figure out which regulatory documents (labels, PSUR/PBRER, RMP, CTD content) might need attention. Today that investigation and handoff to regulatory teams happens manually across spreadsheets, exports, and separate systems, which is slow and easy to lose track of.

---

## 💡 Solution

SignalTrace uses official FDA FAERS quarterly data and a deterministic SignalTrace-owned signal-detection pipeline to produce candidate drug-event signals with transparent PRR/ROR/trend metrics. Project materials describe a Machine-Geist foundation, but the exact source and code reuse are not verifiable; see the provenance audit. From there, it builds a structured evidence package — case quality, potential duplicate triage, temporal relationship, dechallenge/rechallenge — and uses Groq to explain that evidence in plain language, strictly from backend-computed facts (AI never generates the core statistics). A deterministic rule engine then maps each signal to the regulatory documents it may affect, and Gemini analyzes uploaded documents to flag relevant sections, inconsistencies, and coverage gaps. Every output is explicitly framed as decision support requiring human review — the system never claims causality, confirms a drug is unsafe, or auto-modifies/submits regulatory documents.

---

## ✨ Key Features

- **Deterministic signal detection:** PRR/ROR/trend calculation on official FDA FAERS quarterly data; Machine-Geist provenance is documented as unverified
- **Case quality analysis:** flags missing information (event date, concomitant meds, narrative) with an explainable quality score
- **Potential duplicate triage:** both case-version deduplication and cross-case duplicate clustering — flagged for human review, never auto-deleted
- **Groq-powered evidence explanation:** summarizes why a signal was flagged and highlights limitations, grounded entirely in backend-generated facts
- **Signal-to-regulatory impact bridge + Gemini document intelligence:** deterministic mapping from a signal to potentially affected documents (Product Label, RSI, PSUR/PBRER, RMP, CTD content), plus Gemini analysis of uploaded documents for relevant sections and coverage gaps

---

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| **Languages** | Python, TypeScript |
| **Frameworks** | FastAPI, Next.js, React |
| **IBM Technologies** | IBM Bob |
| **Databases** | PostgreSQL / Supabase |
| **Other** | Groq API, Gemini API, FDA FAERS Quarterly Data, openFDA API (optional) |

---

## 📁 Repository Structure

```
├── src/                  # All source code
├── docs/                 # Written documentation
│   ├── problem-statement.md
│   ├── solution-overview.md
│   ├── architecture.md
│   └── setup-guide.md
├── demo/                 # Demo artifacts
│   ├── screenshots/      # App screenshots
│   └── demo-video-link.txt  # Link to demo video
├── presentation/         # Slide deck
└── submission.yaml       # Structured submission metadata
```

---

## ⚡ How to Run

> Copied from [`docs/setup-guide.md`](docs/setup-guide.md) — confirm these match your final `src/` layout before submitting.

```bash
# 1. Clone the repo
git clone https://github.com/mann1325/bob-ai-hackathon-visionx.git
cd bob-ai-hackathon-visionx

# 2. Backend setup
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Fill in: DATABASE_URL, GROQ_API_KEY, GEMINI_API_KEY, OPENFDA_API_BASE_URL (optional)

# 4. Run the backend
uvicorn app.main:app --reload

# 5. Frontend setup (separate terminal)
cd frontend
npm install
npm run dev
```

---

## 🖥️ Demo

| Artifact | Link |
|---|---|
| 📹 Demo Video | https://www.loom.com/share/a1b2c3d4e5f6 |
| 🌐 Live Demo | NOT DEPLOYED |
| 🖼️ Screenshots | [See demo/screenshots/](demo/screenshots/) |
| 📊 Presentation | [See presentation/slides.pdf](presentation/) |

---

## ⚠️ Known Limitations

SignalTrace is a decision-support system by design, not a replacement for expert judgment. As such, it does not:

- Prove causality between a drug and an adverse event
- Diagnose patients
- Declare that a medicine is unsafe
- Replace pharmacovigilance or regulatory professionals
- Make final regulatory decisions
- Automatically modify or submit regulatory documents

AI components (Groq, Gemini) are used strictly for explanation and document analysis — never for computing core statistical metrics (PRR/ROR) or determining regulatory impact, which is fully deterministic and rule-based. All flagged signals, potential duplicates, and document gaps require qualified human review before any action is taken.

---

## 🏅 What We're Most Proud Of

The **Signal-to-Regulatory Impact Bridge** — a deterministic engine that connects a detected safety signal directly to the specific regulatory documents (label, RSI, PSUR/PBRER, RMP, CTD sections) that may need review. This closes a gap that today is handled manually between pharmacovigilance and regulatory teams, and is what differentiates SignalTrace from existing FAERS signal-detection dashboards.

---

## 🤖 How IBM Bob Was Used (Frontend Architecture)

During this Hackathon, the **IBM Bob AI Coding Assistant** was leveraged specifically by the frontend engineering team to orchestrate, refine, and bulletproof the React GUI layer of SignalTrace. 

**Key Code Execution by Bob:**
*   **Component Refactoring**: Automatically decomposed a monolithic dashboard block into six highly isolated, visually uniform React components (utilizing a Consumer Health UI mapping of Native CSS Flex/Grids).
*   **API Isolation Pattern**: Stripped inline `fetch()` and `axios` network logic directly out of UI components, orchestrating all data flow through a unified `ApiClient` interface.
*   **Interactive Simulation**: Constructed a fully decoupled, type-safe `MockAdapter` capable of injecting synthetic delays and E2E placeholder data for live demonstration safety. 
*   **Resiliency & Defenses**: Bob methodically audited UI component life cycles to paint SVG `pulse` skeletal loaders, parse empty data states, and trap arbitrary HTTP crashes within beautifully styled Red graphical banners—ensuring zero unexpected white screens.
*   **Strict UI Validation**: Iteratively verified against the `tsc --noEmit` and `<NextJS Build>` pipelines, cleaning up lingering React TS prop conflicts for a strict 0-error code freeze.

*(Note: IBM Bob’s actions were severely constrained solely to the presentation, styling, and networking boundaries of the TSX UI layers. All native core backend processing, openFDA queries, LLM integration logics, and PRR metric statistics were externally facilitated by backend/data engineers.)*
