# INFO-TWIN: Intelligent Information Understanding & Processing

**INFO-TWIN** is a Digital Information Twin dashboard that ingests multi-format documents, extracts canonical facts and claims, cross-verifies contradictory information across sources, traces evidentiary provenance, maps cascading downstream impact, and simulates hypothetical scenarios without modifying underlying data.

---

## 🚀 Key Features

1. **Multi-Format Ingestion & Real Text Extraction**
   - **PDF**: PyMuPDF (`pymupdf`)
   - **DOCX**: `python-docx` (paragraphs & tables)
   - **TXT**: Native streaming text decoder
   - **CSV & XLSX**: `pandas` & `openpyxl` tabular processors
2. **Structured Claim Extraction**
   - Automatically identifies subjects, attributes, values, origins, and confidence scores without external LLM dependencies.
3. **Cross-Source Conflict Detection**
   - Compares claims across different documents sharing related entities/attributes and flags contradictory assertions (e.g., conflicting deadlines, overlapping room bookings, diverging policies).
4. **Evidence & Explainability ("Why Was This Flagged?")**
   - Side-by-side evidentiary comparison showing exact document excerpts, upload timestamps, and confidence without premature bias.
5. **Change & Missing Information Detection**
   - Tracks temporal value drifts (e.g., revised deadlines, amended requirements).
   - Audits completeness against mandatory milestone fields (deadline, responsible person, submission method, links, required documents).
6. **Information Ripple / Impact Analysis**
   - Computes downstream ripple chains (e.g., `Project Deadline → Submission → Faculty Review → Evaluation → Viva Schedule`).
7. **What-If Scenario Simulator**
   - Isolated sandbox that models cascading friction when hypothetical parameters change (e.g., shifting deadline to `30 October`).
   - **Guaranteed Database Immutability**: Zero write or update operations are executed on SQLite during simulation.
8. **Prescriptive Action Recommendations**
   - Automatically prioritizes action items (`HIGH — Action Required`, `MEDIUM — Review Soon`, `LOW — Monitor`) with clear operational rationales and suggested dispatches.

---

## 🛠️ System Architecture

- **Frontend**: React 18, Vite, Vanilla CSS design system (Cyberpunk / Modern Dark Glassmorphism)
- **Backend**: Python 3.12, Flask, Flask-CORS
- **Database**: SQLite (`backend/infotwin.db`)
- **Extraction Engines**: PyMuPDF, python-docx, pandas, openpyxl

---

## 📦 Prerequisites

- **Node.js**: v18.0.0 or later
- **Python**: v3.10 or later
- **Pip**: Python package manager

---

## 🏃 Quick Start Instructions

### 1. Start the Flask Backend

In a terminal window:

```bash
cd backend
pip install -r requirements.txt
python app.py
```

The backend API server will start on:
👉 **`http://localhost:5000`**

### 2. Start the React Frontend

In a separate terminal window:

```bash
npm install
npm run dev
```

The React dashboard will be accessible at:
👉 **`http://localhost:5173`**

---

## 🧪 Demo Dataset & Evaluation Workflow

A pre-packaged realistic academic dataset is available in the **`demo_data/`** directory:

| Document | Format | Scenario Role |
| :--- | :--- | :--- |
| **`01_Dean_Statutory_Notice.pdf`** | PDF | Dean's statutory circular fixing project deadline at **20 October 2026**. |
| **`02_Coordinator_Update_Email.txt`** | TXT | Coordinator circular extending deadline to **25 October 2026**; **omits submission link**. |
| **`03_Master_Schedule.xlsx` / `.csv`** | Excel / CSV | Master roster outlining review buffers, exam wings, and viva panels in **Lab 302 AI Center**. |
| **`04_Department_Handbook.docx`** | DOCX | Institutional regulations mandating a 5-day review buffer before oral defenses. |

### End-to-End Demo Workflow:

1. **Upload Documents**:
   - Navigate to the **Documents** tab in the sidebar.
   - Upload `01_Dean_Statutory_Notice.pdf` and `02_Coordinator_Update_Email.txt` (or any files from `demo_data/`).
   - Click on any document in the table to view its extracted plain text and structured claims.
2. **Detect Conflicts**:
   - Go to the **Conflicts** tab and click **"Detect Conflicts"**.
   - The system flags the intentional discrepancy:
     `Project Submission Deadline: 20 October vs 25 October` (94%+ confidence).
3. **Inspect Evidence**:
   - Click **"View Evidence"** on the flagged conflict.
   - The **Evidence Dossier** shows Source A (Dean Notice) vs Source B (Coordinator Email) with exact quotes and context.
4. **Inspect Changes & Missing Info**:
   - Navigate to the **Changes** tab.
   - Observe **Semantic Revisions**: `20 October 2026 → 25 October 2026 (+5 days)`.
   - Observe **Missing Fields**: `Submission Method & URL missing in 02_Coordinator_Update_Email.txt`.
5. **Analyze Downstream Ripple**:
   - Click the **Impact Analysis** tab.
   - Inspect the visual 4-tier ripple chain showing how deliverable extension compresses the faculty review buffer and pushes the viva schedule.
6. **Run What-If Simulation**:
   - Go to the **What-If Simulator** tab.
   - Current Value: `25 October`
   - Enter What-If Value: `30 October`
   - Click **[ SIMULATE ]**.
   - The result banner immediately displays:
     ```
     WHAT-IF RESULT
     Original: 25 October
     Scenario: 30 October
     Potential Impact: HIGH
     Affected:
     ✓ Submission
     ✓ Faculty Review
     ⚠ Evaluation
     ⚠ Viva Schedule
     ```
   - Notice confirming: *Important: The actual stored information must remain unchanged.*
7. **Review Action Recommendations**:
   - Return to the **Dashboard** overview.
   - See the top prescriptive action card:
     ```
     🔴 ACTION REQUIRED
     Verify revised project deadline and update affected schedules.
     Reason: A deadline change may affect submission and review schedules.
     ```

---

## 📡 REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | System health check and engine telemetry |
| `POST` | `/api/upload` | Multipart file upload (PDF, DOCX, TXT, CSV, XLSX) |
| `GET` | `/api/documents` | Retrieve all indexed documents from SQLite |
| `GET` | `/api/documents/<id>` | Retrieve specific document with extracted content |
| `POST` | `/api/extract/<id>` | Re-extract text content for a document |
| `POST` | `/api/analyze/<id>` | Extract structured claims from document text |
| `GET` | `/api/claims` | List all extracted claims |
| `POST` | `/api/detect-conflicts` | Execute cross-source conflict detection |
| `GET` | `/api/conflicts` | List all detected conflicts |
| `GET` | `/api/conflicts/<id>/evidence`| Retrieve complete evidence dossier & explanation |
| `POST` | `/api/detect-changes` | Run change & missing field detection |
| `GET` | `/api/changes` | List detected semantic revisions |
| `GET` | `/api/missing-info` | List missing mandatory context fields |
| `POST` | `/api/analyze-impact` | Trace downstream ripple impact graph |
| `POST` | `/api/what-if` | Run non-mutating sandbox simulation |
| `GET` | `/api/recommendations` | Get prioritized prescriptive action items |

---

## 🔒 Verification & Testing

To execute the automated end-to-end integration test suite:

```bash
python backend/test_all_flows.py
```

All 9 pipeline stages are validated with assertions including database immutability checks during What-If simulation.
