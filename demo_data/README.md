# INFO-TWIN Demo Dataset

This dataset contains realistic, interconnected college/project files showcasing the complete INFO-TWIN intelligence pipeline.

## Included Documents:

1. **`01_Dean_Statutory_Notice.pdf`** (PDF format)
   - **Dean's Statutory Circular**: Mandates project deliverable deadline as **20 October 2026**.
   - Identifies responsible authority as Dr. S. K. Narayanan.
   - Requires minimum 5-day evaluation buffer before external viva.

2. **`02_Coordinator_Update_Email.txt`** (TXT format)
   - **Operational Email**: Announces revised deadline extended to **25 October 2026**.
   - **Intentional Conflict**: 20 October 2026 (Dean) vs 25 October 2026 (Coordinator).
   - **Changed Value**: Deadline revised by +5 days.
   - **Missing Field**: Completely omits submission method and portal URL link.

3. **`03_Master_Schedule.xlsx` & `03_Master_Schedule.csv`** (XLSX & CSV formats)
   - **Master Schedule Table**: Outlines milestone schedule.
   - **Impact Ripple Target**: Submission (25 Oct) -> Faculty Review (28-31 Oct) -> Evaluation (01-03 Nov) -> Viva Schedule (05 Nov).
   - Contains venue allocation (Lab 302 AI Center).

4. **`04_Department_Handbook.docx`** (DOCX format)
   - **Academic Regulations**: Contains evaluation rubric and 5-day buffer compliance rule.
   - Venue discrepancy: Mentions Seminar Hall A vs Lab 302.

## Key Demonstrations Covered:
- **Upload & Extraction**: Full parsing across all 5 formats (PDF, DOCX, TXT, CSV, XLSX).
- **Claim Extraction**: Structured claims extracted without external LLM.
- **Conflict Detection**: Flags 20 October vs 25 October with 94%+ confidence.
- **Evidence & Why**: Explains origin, document context, and timestamps for both sources.
- **Change & Missing Detection**: Flags +5 day change and missing submission method.
- **Information Ripple**: Visualizes cascading delay across downstream schedule nodes.
- **What-If Simulator**: Safely forecasts impact of shifting deadline to 30 October without DB writes.
- **Action Recommendation**: Prescribes high-priority verification memo and schedule updates.
