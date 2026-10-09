"""
INFO-TWIN Demo Data Generator
Creates realistic college/project demo documents covering all 5 formats (PDF, DOCX, TXT, CSV, XLSX).
Designed with:
1. Intentional deadline conflict: 20 October (Dean Notice) vs 25 October (Coordinator Email)
2. Changed value: Deadline revised from 20 October to 25 October
3. Missing field: Coordinator Email omits submission method / portal link
4. Related schedule information for impact ripple analysis (Faculty Review -> Evaluation -> Viva)
"""

import os
import pymupdf
import docx
import pandas as pd

DEMO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'demo_data')
os.makedirs(DEMO_DIR, exist_ok=True)

def generate_dean_notice_pdf():
    pdf_path = os.path.join(DEMO_DIR, '01_Dean_Statutory_Notice.pdf')
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842) # A4
    
    text = (
        "OFFICE OF THE DEAN, ACADEMIC AFFAIRS\n"
        "CIRCULAR REF: ACAD/NOT/2026/104\n"
        "DATE: 02 OCTOBER 2026\n\n"
        "SUBJECT: STATUTORY SCHEDULE FOR FINAL YEAR CAPSTONE PROJECT SUBMISSIONS\n\n"
        "1. EXECUTIVE DIRECTIVE\n"
        "This notification establishes the statutory timeline for all undergraduate and postgraduate "
        "final year capstone projects across all engineering and technology departments.\n\n"
        "2. MILESTONE CALENDAR & DEADLINE (CRITICAL)\n"
        "2.1 Deliverable Submission Deadline: Strictly fixed at 20 October 2026, 23:59 IST.\n"
        "2.2 Strict zero-tolerance late submission policy applies. The upload portal will lock automatically.\n"
        "2.3 Issuing Authority: Dr. S. K. Narayanan, Dean of Academic Affairs.\n\n"
        "3. EVALUATION TIMELINE & BUFFER MANDATE\n"
        "3.1 Initial screening and faculty peer reviews shall commence following deliverable cutoff.\n"
        "3.2 External Viva Voce oral defense is tentatively scheduled for 05 November 2026 in Seminar Hall A.\n"
        "3.3 In accordance with Article 7.2 of the Academic Policy Handbook, a mandatory 5-day review buffer "
        "must be maintained between final deliverable close and external examiner viva sessions."
    )
    
    # Insert text into page
    rect = pymupdf.Rect(50, 50, 545, 792)
    page.insert_textbox(rect, text, fontsize=11, fontname="helv", color=(0.1, 0.1, 0.15))
    doc.save(pdf_path)
    doc.close()
    print(f"Generated {pdf_path}")

def generate_coordinator_email_txt():
    txt_path = os.path.join(DEMO_DIR, '02_Coordinator_Update_Email.txt')
    content = (
        "From: Prof. Ramesh Verma <ramesh.verma@college.edu>\n"
        "To: All-Final-Year-Capstone-Students <capstone-2026@college.edu>\n"
        "Date: 04 October 2026 14:32:18 +0530\n"
        "Subject: URGENT: Capstone Project Submission Deadline Extension & Lab Access\n\n"
        "Dear Students and Project Guides,\n\n"
        "Following student representations regarding festive recess and limited hardware GPU lab availability,\n"
        "the final project submission deadline has been officially extended:\n\n"
        "REVISED SUBMISSION DEADLINE: 25 OCTOBER 2026, 23:59 IST\n\n"
        "Please note this change supersedes previous dates. All student project teams must submit their complete code\n"
        "and technical report by 25 October 2026.\n\n"
        "(Note: Submission method, online portal link, and required bundle guidelines will be issued in a subsequent addendum.)\n\n"
        "Best regards,\n"
        "Prof. Ramesh Verma\n"
        "Capstone Project Coordinator\n"
        "Department of Computer Science & Engineering"
    )
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Generated {txt_path}")

def generate_master_schedule_xlsx_and_csv():
    xlsx_path = os.path.join(DEMO_DIR, '03_Master_Schedule.xlsx')
    csv_path = os.path.join(DEMO_DIR, '03_Master_Schedule.csv')

    data = {
        'Milestone_ID': ['M101', 'M102', 'M103', 'M104', 'M105'],
        'Process_Stage': [
            'Project Deliverable Submission',
            'Initial Screener & Compliance',
            'Faculty Peer Review',
            'Score Compilation & Evaluation',
            'Final External Viva Voce Defense'
        ],
        'Start_Date': ['2026-10-10', '2026-10-26', '2026-10-28', '2026-11-01', '2026-11-05'],
        'End_Date': ['2026-10-25', '2026-10-27', '2026-10-31', '2026-11-03', '2026-11-08'],
        'Assigned_Venue': ['Online Portal', 'Dept Office', 'Virtual Panels', 'Exam Wing', 'Lab 302 AI Center'],
        'Responsible_Lead': ['Prof. Ramesh Verma', 'Dr. S. K. Narayanan', 'Review Committee', 'Academic Registrar', 'External Examiners'],
        'Status': ['Active (Cutoff 25 Oct)', 'Pending', 'Ripple Impacted', 'Senate Overlap Risk', 'Defense Bottleneck']
    }
    df = pd.DataFrame(data)
    
    # Save CSV
    df.to_csv(csv_path, index=False)
    print(f"Generated {csv_path}")

    # Save XLSX
    with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Master_Schedule', index=False)
    print(f"Generated {xlsx_path}")

def generate_department_handbook_docx():
    docx_path = os.path.join(DEMO_DIR, '04_Department_Handbook.docx')
    doc = docx.Document()
    
    doc.add_heading('INSTITUTIONAL ACADEMIC POLICY & EVALUATION HANDBOOK', level=0)
    doc.add_heading('Article 7: Capstone Project Governance & Assessment Rules', level=1)
    
    doc.add_paragraph(
        "7.1 Mandatory Buffer Directive: A statutory buffer of no fewer than five (5) working days "
        "shall be enforced between deliverable cutoff and external viva defense to allow thorough faculty review."
    )
    doc.add_paragraph(
        "7.2 Conflicting Directives: Formal circulars issued by the Dean of Academic Affairs shall govern "
        "and supersede unratified committee communications."
    )
    doc.add_paragraph(
        "7.3 Logistics & Examination Venue: All capstone final defenses shall be hosted in Seminar Hall A "
        "unless reallocated by formal deanery notification to Lab 302 AI Center."
    )
    
    table = doc.add_table(rows=1, cols=3)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Assessment Component'
    hdr_cells[1].text = 'Weightage'
    hdr_cells[2].text = 'Evaluating Body'
    
    components = [
        ('Internal Faculty Review', '30%', 'Department Committee'),
        ('Technical Implementation & Code', '30%', 'Internal Mentors'),
        ('External Viva Voce Defense', '40%', 'External University Panel')
    ]
    for comp, weight, body in components:
        row_cells = table.add_row().cells
        row_cells[0].text = comp
        row_cells[1].text = weight
        row_cells[2].text = body
        
    doc.save(docx_path)
    print(f"Generated {docx_path}")

def generate_demo_readme():
    readme_path = os.path.join(DEMO_DIR, 'README.md')
    content = (
        "# INFO-TWIN Demo Dataset\n\n"
        "This dataset contains realistic, interconnected college/project files showcasing the complete INFO-TWIN intelligence pipeline.\n\n"
        "## Included Documents:\n\n"
        "1. **`01_Dean_Statutory_Notice.pdf`** (PDF format)\n"
        "   - **Dean's Statutory Circular**: Mandates project deliverable deadline as **20 October 2026**.\n"
        "   - Identifies responsible authority as Dr. S. K. Narayanan.\n"
        "   - Requires minimum 5-day evaluation buffer before external viva.\n\n"
        "2. **`02_Coordinator_Update_Email.txt`** (TXT format)\n"
        "   - **Operational Email**: Announces revised deadline extended to **25 October 2026**.\n"
        "   - **Intentional Conflict**: 20 October 2026 (Dean) vs 25 October 2026 (Coordinator).\n"
        "   - **Changed Value**: Deadline revised by +5 days.\n"
        "   - **Missing Field**: Completely omits submission method and portal URL link.\n\n"
        "3. **`03_Master_Schedule.xlsx` & `03_Master_Schedule.csv`** (XLSX & CSV formats)\n"
        "   - **Master Schedule Table**: Outlines milestone schedule.\n"
        "   - **Impact Ripple Target**: Submission (25 Oct) -> Faculty Review (28-31 Oct) -> Evaluation (01-03 Nov) -> Viva Schedule (05 Nov).\n"
        "   - Contains venue allocation (Lab 302 AI Center).\n\n"
        "4. **`04_Department_Handbook.docx`** (DOCX format)\n"
        "   - **Academic Regulations**: Contains evaluation rubric and 5-day buffer compliance rule.\n"
        "   - Venue discrepancy: Mentions Seminar Hall A vs Lab 302.\n\n"
        "## Key Demonstrations Covered:\n"
        "- **Upload & Extraction**: Full parsing across all 5 formats (PDF, DOCX, TXT, CSV, XLSX).\n"
        "- **Claim Extraction**: Structured claims extracted without external LLM.\n"
        "- **Conflict Detection**: Flags 20 October vs 25 October with 94%+ confidence.\n"
        "- **Evidence & Why**: Explains origin, document context, and timestamps for both sources.\n"
        "- **Change & Missing Detection**: Flags +5 day change and missing submission method.\n"
        "- **Information Ripple**: Visualizes cascading delay across downstream schedule nodes.\n"
        "- **What-If Simulator**: Safely forecasts impact of shifting deadline to 30 October without DB writes.\n"
        "- **Action Recommendation**: Prescribes high-priority verification memo and schedule updates.\n"
    )
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Generated {readme_path}")

if __name__ == '__main__':
    generate_dean_notice_pdf()
    generate_coordinator_email_txt()
    generate_master_schedule_xlsx_and_csv()
    generate_department_handbook_docx()
    generate_demo_readme()
    print("All demo files successfully generated in demo_data/ folder!")
