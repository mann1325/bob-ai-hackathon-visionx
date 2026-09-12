# SignalTrace Design Guide

## 1. Aesthetic Target & Rationale

**"Linear meets a hospital dashboard"**

The design philosophy for SignalTrace revolves around absolute trust, data density, and clinical precision. As a pharmacovigilance tool, the UI must never distract the user with playful elements, decorative gradients, or "neon" styling often found in rapid prototypes. 

- **High Trust & Zero Playfulness**: The interface feels deterministic and professional. UI elements are flat, borders are crisp (1px solid), and shadows are practically non-existent or restricted to subtle depths for modals. All structural backgrounds are strictly flat grays or off-blacks.
- **Data Density vs AI Isolation**: Hard deterministic data (reports, PRR, ROR) should be presented as dense, tabular, or tightly grouped typography. Conversely, any AI-generated insight MUST feature generous whitespace, establishing a visual separation that subtly implies "provisional" and "requires review" rather than "undisputed fact."
- **Restrained Accent Palette**: Accent colors are strictly reserved for communicating priority or risk states. We avoid using primary branded colors (like vibrant purples or blues) for decorative purposes.

---

## 2. Component Design Guide

### Core System
- **Typography:** Inter or a similarly austere sans-serif (e.g., Roboto). Weights utilized heavily to delineate hierarchy (e.g., 400 for structural text, 600 for column headers).
- **Color System (Dark Mode First):**
  - Background: `#0B0C10` (True dark, almost black).
  - Surface/Panel: `#18181B` (Zinc-900).
  - Borders: `#27272A` (Zinc-800).
  - Text Primary: `#FAFAFA` (Zinc-50).
  - Text Secondary: `#A1A1AA` (Zinc-400).
- **Spacing Scale:** Standard 4px-based grid (4, 8, 16, 24, 32). However, AI panels receive an automatic `+16px` or `+24px` padding variance to enforce the "provisional" whitespace rule.

### Priority & Risk Colors (The only accents)
- **Critical / High Risk:** `#EF4444` (A muted clinical red, not neon).
- **High / Elevated:** `#F59E0B` (Amber).
- **Medium / Under Review:** `#3B82F6` (Clinical blue).
- **Low / Closed / Baseline:** `#64748B` (Slate).

---

### Component Treatments

#### Data Tables / Metrics Panels
- **Layout:** Dense, multi-column layouts. No padding bloat inside cells.
- **Style:** 1px `#27272A` borders separating rows/columns. Text is monospaced or tabular-nums for numeric columns (PRR, ROR, Counts).
- **Headers:** All-caps, small font (11px or 12px), tracked out (`letter-spacing: 0.05em`), `#A1A1AA`.

#### Evidence Cards (Deterministic)
- **Style:** Flat `#18181B` background, 4px border-radius (sharp, clinical), 1px solid border. 
- **Typography:** Tight line heights (`1.2` for titles, `1.4` for text). Left-aligned. Values directly next to labels.

#### AI Explanation Panel (Provisional)
- **Style:** Visually distinct from deterministic panels to force the user to shift contexts.
- **Layout:** Generous padding (`32px`), perhaps an inset background (e.g., `#121214`) to denote a "sandbox" or "synthesized" area.
- **Typography:** Slightly increased line-height (`1.6`), reading more like an editorial column than a telemetry dashboard.

#### Persistent "Human Review Required" Banner (AILabel)
- **Style:** This must replace the previous "glowing/gradient" AI badge. Instead, it should be a stark, high-contrast flat label attached to the header of the AI panel. 
- **Colors:** Minimalist black background with bordered yellow/amber text (`#FBBF24`), or a subdued amber background (`#451A03`) with stark amber text.
- **Iconography:** A sharp warning triangle, no pulsing or glowing animations. It's a static, clinical flag.

#### Document Upload / Analysis Panel
- **Upload Zone:** A dashed border (`#3F3F46`), flat background, flat typography ("Click or drag document to begin Gemini analysis"). No hover-glows. 
- **Analysis State:** Once analyzed, findings are presented in dense lists (like the Evidence Cards), but the entire section is headed by the flat "Human Review Required" banner.
