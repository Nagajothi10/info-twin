import sqlite3
import os
import time
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'infotwin.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Documents table (backward-compatible core table with version lineage columns)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT,
            version_id TEXT,
            parent_file_id TEXT,
            version_number INTEGER DEFAULT 1,
            uploader TEXT DEFAULT 'Person A',
            checksum TEXT DEFAULT '',
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            size TEXT NOT NULL,
            file_path TEXT NOT NULL,
            uploaded TEXT NOT NULL,
            status TEXT DEFAULT 'Uploaded',
            status_type TEXT DEFAULT 'info',
            summary TEXT,
            extracted_claim TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Ensure all version columns exist on documents if upgraded from older schema
    cursor.execute('PRAGMA table_info(documents)')
    doc_cols = [col['name'] for col in cursor.fetchall()]
    migration_cols = [
        ('file_id', 'TEXT'),
        ('version_id', 'TEXT'),
        ('parent_file_id', 'TEXT'),
        ('version_number', 'INTEGER DEFAULT 1'),
        ('uploader', "TEXT DEFAULT 'Person A'"),
        ('checksum', "TEXT DEFAULT ''")
    ]
    for col_name, col_type in migration_cols:
        if col_name not in doc_cols:
            cursor.execute(f'ALTER TABLE documents ADD COLUMN {col_name} {col_type}')

    # Claims table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            version_id TEXT,
            subject TEXT NOT NULL,
            attribute TEXT NOT NULL,
            value TEXT NOT NULL,
            source TEXT NOT NULL,
            confidence REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('PRAGMA table_info(claims)')
    claim_cols = [col['name'] for col in cursor.fetchall()]
    if 'version_id' not in claim_cols:
        cursor.execute('ALTER TABLE claims ADD COLUMN version_id TEXT')

    # Conflicts table matching user specifications:
    cursor.execute('PRAGMA table_info(conflicts)')
    conflict_cols = [col['name'] for col in cursor.fetchall()]
    if conflict_cols and 'claim_id_1' not in conflict_cols:
        cursor.execute('DROP TABLE IF EXISTS conflicts')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conflicts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id_1 INTEGER,
            claim_id_2 INTEGER,
            reason TEXT NOT NULL,
            confidence TEXT NOT NULL,
            status TEXT DEFAULT 'Conflict Detected',
            subject TEXT,
            attribute TEXT,
            source_a_name TEXT,
            source_a_claim TEXT,
            source_b_name TEXT,
            source_b_claim TEXT,
            discrepancy TEXT,
            severity TEXT DEFAULT 'High',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Step 7: Changes Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            attribute TEXT,
            title TEXT NOT NULL,
            change_type TEXT NOT NULL,
            category TEXT DEFAULT 'Timeline',
            old_value TEXT NOT NULL,
            new_value TEXT NOT NULL,
            old_source TEXT,
            new_source TEXT,
            source TEXT NOT NULL,
            source_delta TEXT,
            date TEXT NOT NULL,
            timestamp TEXT,
            impact TEXT,
            is_conflict INTEGER DEFAULT 0,
            claim_id_old INTEGER,
            claim_id_new INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Step 7: Missing Information Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS missing_information (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            source_document TEXT NOT NULL,
            related_subject TEXT NOT NULL,
            missing_field TEXT NOT NULL,
            field_key TEXT NOT NULL,
            status TEXT DEFAULT 'Missing Information',
            severity TEXT DEFAULT 'Medium',
            impact TEXT,
            present_context TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ================= DOCUMENT VERSIONING TABLES =================

    # Immutable Document Versions Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS document_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version_id TEXT UNIQUE NOT NULL,
            file_id TEXT NOT NULL,
            parent_version_id TEXT,
            parent_file_id TEXT,
            version_number INTEGER NOT NULL,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            size TEXT NOT NULL,
            file_path TEXT NOT NULL,
            checksum TEXT NOT NULL,
            uploader TEXT NOT NULL,
            upload_date TEXT NOT NULL,
            upload_time TEXT NOT NULL,
            status TEXT DEFAULT 'Active',
            status_type TEXT DEFAULT 'info',
            summary TEXT,
            extracted_claim TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_versions_file_id ON document_versions(file_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_versions_checksum ON document_versions(checksum)')

    # Version Field Changes Table (Delta between versions)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS version_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version_id TEXT NOT NULL,
            file_id TEXT NOT NULL,
            field_name TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            change_type TEXT DEFAULT 'Modified',
            modified_by TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_changes_v_id ON version_changes(version_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_changes_f_id ON version_changes(file_id)')

    # Version Conflicts Table (Concurrent conflicting edits between versions)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS version_conflicts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT NOT NULL,
            version_id_a TEXT NOT NULL,
            version_id_b TEXT NOT NULL,
            field_name TEXT NOT NULL,
            value_a TEXT NOT NULL,
            value_b TEXT NOT NULL,
            uploader_a TEXT NOT NULL,
            uploader_b TEXT NOT NULL,
            status TEXT DEFAULT 'Conflict Detected',
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Migrate legacy documents to document_versions if needed
    cursor.execute('SELECT * FROM documents WHERE file_id IS NULL OR file_id = ""')
    unmigrated = cursor.fetchall()
    for row in unmigrated:
        d_id = row['id']
        f_id = f'DOC-{d_id:03d}'
        v_id = f'VER-{d_id:03d}-1'
        up = row['uploader'] or 'Person A'
        cursor.execute('''
            UPDATE documents 
            SET file_id = ?, version_id = ?, parent_file_id = ?, version_number = 1, uploader = ?
            WHERE id = ?
        ''', (f_id, v_id, f_id, up, d_id))

        cursor.execute('SELECT COUNT(*) as c FROM document_versions WHERE version_id = ?', (v_id,))
        if cursor.fetchone()['c'] == 0:
            cursor.execute('''
                INSERT INTO document_versions (
                    version_id, file_id, parent_version_id, parent_file_id, version_number,
                    filename, file_type, size, file_path, checksum, uploader,
                    upload_date, upload_time, status, status_type, summary, extracted_claim, content
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                v_id, f_id, None, f_id, 1,
                row['name'], row['type'], row['size'], row['file_path'], row['checksum'] or '', up,
                row['uploaded'], row['uploaded'] + ' 09:00', row['status'], row['status_type'],
                row['summary'], row['extracted_claim'], row['content']
            ))

            cursor.execute('''
                INSERT INTO version_changes (
                    version_id, file_id, field_name, old_value, new_value,
                    change_type, modified_by, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                v_id, f_id, 'Document', 'None', 'Original Document Uploaded',
                'Initial Version', up, row['uploaded']
            ))

        conn.commit()
    conn.close()

def seed_canonical_demo_corpus():
    """
    Seeds the canonical collegiate demo documents and claims into SQLite.
    Only executed when explicitly requested (e.g. via /api/seed-demo).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM documents')
    cursor.execute('DELETE FROM claims')
    cursor.execute('DELETE FROM conflicts')
    cursor.execute('DELETE FROM changes')
    cursor.execute('DELETE FROM missing_information')
    cursor.execute('DELETE FROM document_versions')
    cursor.execute('DELETE FROM version_changes')
    cursor.execute('DELETE FROM version_conflicts')

    # Seed base initial documents if empty
    cursor.execute('SELECT COUNT(*) as count FROM documents')
    if cursor.fetchone()['count'] == 0:
        initial_docs = [
            (
                'DOC-001', 'VER-001-1', 'DOC-001', 1, 'Person A', '',
                'notice.pdf', 'pdf', '2.4 MB', 'uploads/notice.pdf', '02 Oct 2026',
                'Conflict Flagged', 'danger',
                "Dean's Office Statutory Circular: Project Deadline set to 20 October 2026.",
                'Section 4.2: Deliverable deadline strictly fixed at 20 October 2026, 23:59 IST.',
                '''OFFICE OF THE DEAN, ACADEMIC AFFAIRS
CIRCULAR REF: ACAD/NOT/2026/089
DATE: 02 OCTOBER 2026

SUBJECT: FINAL CAPSTONE PROJECT SUBMISSION & EVALUATION SCHEDULE

1. PURPOSE & SCOPE
This notification establishes the statutory timeline for all undergraduate and postgraduate final year capstone project submissions across all engineering and computing departments.

2. MILESTONE CALENDAR & DEADLINE (CRITICAL)
2.1 The final portal upload window opens on 10 October 2026.
2.2 All deliverables must be uploaded to the official evaluation portal no later than 20 October 2026 at 23:59 IST.
2.3 Strict zero-tolerance late policy applies. Portal locks automatically at 23:59:01 IST.

3. EVALUATION VENUE & GOVERNANCE
Oral defenses and examinations will be held in Seminar Hall A supervised by the Office of the Dean.'''
            ),
            (
                'DOC-002', 'VER-002-1', 'DOC-002', 1, 'Person A', '',
                'email.txt', 'txt', '18 KB', 'uploads/email.txt', '04 Oct 2026',
                'Conflict Flagged', 'danger',
                'Department Coordinator Update: Milestone extended to 25 October 2026.',
                'Operational email stating project deadline extended to 25 October 2026.',
                '''From: Prof. Ramesh Verma <ramesh.verma@university.edu>
To: All-Capstone-Students <capstone-2026@university.edu>
Date: Fri, 04 Oct 2026 14:32:18 +0530
Subject: Re: Capstone Project Timetable Extension & Lab Access

Dear Students and Mentors,
Following representations regarding the festive recess and limited hardware lab availability, the final deadline for project submission has been officially extended to:

REVISED DEADLINE: 25 OCTOBER 2026, 23:59 IST

Peer review slots commence on 28 October 2026. Viva sessions begin on 05 November 2026 in Lab 302.

Best regards,
Prof. Ramesh Verma
Capstone Project Coordinator'''
            ),
            (
                'DOC-003', 'VER-003-1', 'DOC-003', 1, 'Person A', '',
                'schedule.xlsx', 'xlsx', '540 KB', 'uploads/schedule.xlsx', '28 Sep 2026',
                'Ripple Impacted', 'warning',
                'Academic Operations Master Roster: Reviewer allocations and viva panels.',
                'Viva dates set for 05 November based on 25 October deliverable cutoff.',
                '''=== Sheet: Master_Schedule (12 rows) ===
Slot_ID | Event | Start_Date | End_Date | Venue | Coordinator | Status
S101 | Deliverable Portal | 2026-10-10 | 2026-10-25 | Online Portal | Dr. Verma | Active
S102 | Initial Screening | 2026-10-26 | 2026-10-27 | Dept Office | Dr. Verma | Pending
S103 | Faculty Peer Review | 2026-10-28 | 2026-10-31 | Virtual Panels | Committee | Affected
S104 | Score Compilation | 2026-11-01 | 2026-11-03 | Exam Wing | Registrar | At Risk
S105 | Final External Viva | 2026-11-05 | 2026-11-08 | Lab 302 AI Center | External Panel | Conflict Risk'''
            ),
            (
                'DOC-004', 'VER-004-1', 'DOC-004', 1, 'Person A', '',
                'policy.pdf', 'pdf', '4.1 MB', 'uploads/policy.pdf', '15 Aug 2026',
                'Verified Base', 'success',
                'Institutional Academic Handbook: Evaluation criteria, late penalties, viva rules.',
                'Mandates minimum 5-day review period before external viva.',
                '''UNIVERSITY ACADEMIC POLICY HANDBOOK
ARTICLE 7: UNDERGRADUATE & GRADUATE CAPSTONE ASSESSMENT POLICY

7.1 GOVERNING MANDATE
All capstone projects shall be evaluated across three canonical tiers:
- Tier I: Continuous Mentor Evaluation (30%)
- Tier II: Blind Peer Faculty Review (30%)
- Tier III: External Oral Defense & Viva Voce (40%)

7.2 TIMELINESS & REVIEW BUFFER RULES
a) A minimum mandatory buffer of five (5) working days shall be observed between final deliverable close and external viva sessions.
b) Statutory circulars issued by the Dean of Academic Affairs supersede operational emails.'''
            )
        ]
        cursor.executemany('''
            INSERT INTO documents (file_id, version_id, parent_file_id, version_number, uploader, checksum, name, type, size, file_path, uploaded, status, status_type, summary, extracted_claim, content)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', initial_docs)

        # Mirror into document_versions and baseline version_changes
        for d in initial_docs:
            cursor.execute('''
                INSERT INTO document_versions (
                    version_id, file_id, parent_version_id, parent_file_id, version_number,
                    filename, file_type, size, file_path, checksum, uploader,
                    upload_date, upload_time, status, status_type, summary, extracted_claim, content
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                d[1], d[0], None, d[2], d[3],
                d[6], d[7], d[8], d[9], d[5], d[4],
                d[10], d[10] + ' 09:00', d[11], d[12],
                d[13], d[14], d[15]
            ))
            cursor.execute('''
                INSERT INTO version_changes (
                    version_id, file_id, field_name, old_value, new_value,
                    change_type, modified_by, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                d[1], d[0], 'Document', 'None', 'Original Baseline Document',
                'Initial Upload', d[4], d[10]
            ))

    # Seed base claims if empty
    cursor.execute('SELECT COUNT(*) as count FROM claims')
    if cursor.fetchone()['count'] == 0:
        initial_claims = [
            (1, 'VER-001-1', 'Project Submission', 'Submission Deadline', '20 October 2026 at 23:59 IST', 'notice.pdf', 0.95),
            (1, 'VER-001-1', 'Academic Personnel', 'Issuing Official', 'Office of the Dean, Academic Affairs', 'notice.pdf', 0.92),
            (1, 'VER-001-1', 'Submission Regulation', 'Late Policy', 'Strict zero-tolerance late policy applies', 'notice.pdf', 0.94),
            (1, 'VER-001-1', 'Event Logistics', 'Assigned Venue', 'Seminar Hall A', 'notice.pdf', 0.90),
            (2, 'VER-002-1', 'Project Submission', 'Submission Deadline', '25 October 2026, 23:59 IST', 'email.txt', 0.98),
            (2, 'VER-002-1', 'Academic Personnel', 'Coordinator', 'Prof. Ramesh Verma', 'email.txt', 0.94),
            (2, 'VER-002-1', 'Viva Defense', 'Scheduled Date', '05 November 2026', 'email.txt', 0.92),
            (2, 'VER-002-1', 'Event Logistics', 'Assigned Venue', 'Lab 302', 'email.txt', 0.91),
            (3, 'VER-003-1', 'Viva Defense', 'Scheduled Window', '2026-11-05 to 2026-11-08', 'schedule.xlsx', 0.90),
            (3, 'VER-003-1', 'Event Logistics', 'Assigned Venue', 'Lab 302 AI Center', 'schedule.xlsx', 0.93),
            (4, 'VER-004-1', 'Policy Buffer', 'Duration Window', '5 working days', 'policy.pdf', 0.92),
            (4, 'VER-004-1', 'Evaluation Rubric', 'Grading Weightage', '40% External Oral Defense', 'policy.pdf', 0.89)
        ]
        cursor.executemany('''
            INSERT INTO claims (document_id, version_id, subject, attribute, value, source, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', initial_claims)

    # Seed base conflicts if empty
    cursor.execute('SELECT COUNT(*) as count FROM conflicts')
    if cursor.fetchone()['count'] == 0:
        initial_conflicts = [
            (
                1, 5,
                "Contradictory values asserted for 'Project Submission' (Submission Deadline): '20 October 2026 at 23:59 IST' in notice.pdf vs '25 October 2026, 23:59 IST' in email.txt.",
                '94%', 'Conflict Detected',
                'Project Submission', 'Submission Deadline',
                'notice.pdf', '20 October',
                'email.txt', '25 October',
                '20 October vs 25 October', 'High'
            ),
            (
                4, 8,
                "Contradictory values asserted for 'Event Logistics' (Assigned Venue): 'Seminar Hall A' in notice.pdf vs 'Lab 302' in email.txt.",
                '89%', 'Conflict Detected',
                'Event Logistics', 'Assigned Venue',
                'notice.pdf', 'Seminar Hall A',
                'email.txt', 'Lab 302',
                'Seminar Hall A vs Lab 302', 'Medium'
            ),
            (
                3, 11,
                "Contradictory values asserted for 'Policy Buffer' (Late Policy): 'Strict zero-tolerance' in notice.pdf vs '5 working days' in policy.pdf.",
                '82%', 'Conflict Detected',
                'Policy Compliance', 'Late Policy',
                'policy.pdf', '5 working days buffer',
                'notice.pdf', 'Strict zero-tolerance',
                '5 days buffer vs zero-tolerance', 'Low'
            )
        ]
        cursor.executemany('''
            INSERT INTO conflicts (
                claim_id_1, claim_id_2, reason, confidence, status,
                subject, attribute, source_a_name, source_a_claim, source_b_name, source_b_claim,
                discrepancy, severity
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', initial_conflicts)
    conn.commit()
    conn.close()
    sync_dependent_data_after_change()
    return {'success': True, 'message': 'Canonical demo dataset loaded successfully.'}

# ================= DOCUMENT & VERSION OPERATIONS =================

def format_doc_dict(d, changes=None):
    if not d:
        return None
    d = dict(d)
    v_num = d.get('version_number') or 1
    uploader = d.get('uploader') or 'Person A'
    f_id = d.get('file_id') or f"DOC-{d.get('id', 1):03d}"
    v_id = d.get('version_id') or f"VER-{d.get('id', 1):03d}-{v_num}"
    uploaded_val = d.get('uploaded') or d.get('upload_date') or datetime.now().strftime('%d %b %Y')

    return {
        'id': d.get('id'),
        'file_id': f_id,
        'version_id': v_id,
        'parent_file_id': d.get('parent_file_id') or f_id,
        'parent_version_id': d.get('parent_version_id'),
        'version': v_num,
        'version_number': v_num,
        'uploader': uploader,
        'uploaded_by': uploader,
        'checksum': d.get('checksum') or '',
        'name': d.get('name') or d.get('filename') or 'Document',
        'filename': d.get('filename') or d.get('name') or 'Document',
        'type': d.get('type') or d.get('file_type') or 'pdf',
        'file_type': d.get('file_type') or d.get('type') or 'pdf',
        'size': d.get('size') or '0 KB',
        'file_path': d.get('file_path') or '',
        'uploaded': uploaded_val,
        'upload_date': uploaded_val,
        'upload_time': d.get('upload_time') or f"{uploaded_val} 09:00",
        'status': d.get('status') or 'Active',
        'status_type': d.get('status_type') or 'info',
        'summary': d.get('summary') or '',
        'extracted_claim': d.get('extracted_claim') or '',
        'content': d.get('content') or '',
        'extracted_content': d.get('content') or '',
        'created_at': d.get('created_at') or '',
        'changes': changes or []
    }

def add_document_version(
    file_id, version_id, parent_version_id, version_number,
    filename, doc_type, size, file_path, checksum, uploader,
    summary, extracted_claim, content="", changes=None, status="Active", status_type="info"
):
    """
    Adds a new immutable document version to SQLite.
    Guaranteed: NEVER overwrites or deletes earlier versions.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_dt = datetime.now()
    uploaded_date = now_dt.strftime('%d %b %Y')
    uploaded_time = now_dt.strftime('%d %b %Y %H:%M')

    # 1. Insert into document_versions
    cursor.execute('''
        INSERT INTO document_versions (
            version_id, file_id, parent_version_id, parent_file_id, version_number,
            filename, file_type, size, file_path, checksum, uploader,
            upload_date, upload_time, status, status_type, summary, extracted_claim, content
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        version_id, file_id, parent_version_id, file_id, version_number,
        filename, doc_type, size, file_path, checksum, uploader,
        uploaded_date, uploaded_time, status, status_type, summary, extracted_claim, content
    ))
    version_row_id = cursor.lastrowid

    # 2. Insert into documents for backward compatibility
    cursor.execute('''
        INSERT INTO documents (
            file_id, version_id, parent_file_id, version_number, uploader, checksum,
            name, type, size, file_path, uploaded, status, status_type, summary, extracted_claim, content
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        file_id, version_id, file_id, version_number, uploader, checksum,
        filename, doc_type, size, file_path, uploaded_date, status, status_type, summary, extracted_claim, content
    ))
    doc_row_id = cursor.lastrowid

    # 3. Insert version changes if any
    saved_changes = []
    if changes:
        for ch in changes:
            cursor.execute('''
                INSERT INTO version_changes (
                    version_id, file_id, field_name, old_value, new_value,
                    change_type, modified_by, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                version_id, file_id,
                ch.get('field_name', 'Field'),
                ch.get('old_value', ''),
                ch.get('new_value', ''),
                ch.get('change_type', 'Modified'),
                uploader,
                uploaded_time
            ))
            saved_changes.append({
                'id': cursor.lastrowid,
                'version_id': version_id,
                'file_id': file_id,
                'field_name': ch.get('field_name', 'Field'),
                'old_value': ch.get('old_value', ''),
                'new_value': ch.get('new_value', ''),
                'change_type': ch.get('change_type', 'Modified'),
                'modified_by': uploader,
                'timestamp': uploaded_time
            })
    else:
        # Default baseline change for v1
        ch_type = 'Initial Version' if version_number == 1 else 'Updated Version'
        ch_desc = 'Original Document Uploaded' if version_number == 1 else f'Version {version_number} uploaded'
        cursor.execute('''
            INSERT INTO version_changes (
                version_id, file_id, field_name, old_value, new_value,
                change_type, modified_by, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            version_id, file_id, 'Document', 'None' if version_number == 1 else f'Version {version_number - 1}',
            ch_desc, ch_type, uploader, uploaded_time
        ))

    conn.commit()

    cursor.execute('SELECT * FROM documents WHERE id = ?', (doc_row_id,))
    doc_row = cursor.fetchone()
    conn.close()

    return format_doc_dict(doc_row, saved_changes)

def add_document(name, doc_type, size, file_path, summary, extracted_claim, content=""):
    """Legacy add_document helper for backward compatibility."""
    parent_info = find_parent_file_by_name(name)
    now_ms = int(time.time() * 1000)
    if parent_info:
        file_id = parent_info['file_id']
        version_number = parent_info['latest_version'] + 1
        uploader = f"Person {chr(65 + (version_number - 1) % 26)}"
        parent_v_id = parent_info['latest_version_id']
    else:
        file_id = f"DOC-{now_ms % 100000:05d}"
        version_number = 1
        uploader = 'Person A'
        parent_v_id = None

    version_id = f"VER-{file_id}-{version_number}"
    return add_document_version(
        file_id=file_id,
        version_id=version_id,
        parent_version_id=parent_v_id,
        version_number=version_number,
        filename=name,
        doc_type=doc_type,
        size=size,
        file_path=file_path,
        checksum="",
        uploader=uploader,
        summary=summary,
        extracted_claim=extracted_claim,
        content=content
    )

def get_document_by_id(doc_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM documents WHERE id = ?', (doc_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    d = dict(row)
    v_id = d.get('version_id')
    changes = []
    if v_id:
        cursor.execute('SELECT * FROM version_changes WHERE version_id = ? ORDER BY id ASC', (v_id,))
        changes = [dict(c) for c in cursor.fetchall()]
    conn.close()
    return format_doc_dict(d, changes)

def get_version_by_id(version_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM document_versions WHERE version_id = ?', (version_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    d = dict(row)
    cursor.execute('SELECT * FROM version_changes WHERE version_id = ? ORDER BY id ASC', (version_id,))
    changes = [dict(c) for c in cursor.fetchall()]
    conn.close()
    return format_doc_dict(d, changes)

def get_versions_by_file_id(file_id):
    """Returns all versions for a given logical document ordered newest first."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM document_versions WHERE file_id = ? ORDER BY version_number DESC', (file_id,))
    rows = cursor.fetchall()
    results = []
    for r in rows:
        d = dict(r)
        v_id = d['version_id']
        cursor.execute('SELECT * FROM version_changes WHERE version_id = ? ORDER BY id ASC', (v_id,))
        changes = [dict(c) for c in cursor.fetchall()]
        results.append(format_doc_dict(d, changes))
    conn.close()
    return results

def get_all_document_versions():
    """Returns all document versions across all documents ordered newest first."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM document_versions ORDER BY id DESC')
    rows = cursor.fetchall()
    results = []
    for r in rows:
        d = dict(r)
        v_id = d['version_id']
        cursor.execute('SELECT * FROM version_changes WHERE version_id = ? ORDER BY id ASC', (v_id,))
        changes = [dict(c) for c in cursor.fetchall()]
        results.append(format_doc_dict(d, changes))
    conn.close()
    return results

def get_all_documents():
    """
    Returns all documents/versions from SQLite ordered newest first.
    Compatible with existing test suites and the new versioning UI.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM documents ORDER BY id DESC')
    rows = cursor.fetchall()
    results = []
    for r in rows:
        d = dict(r)
        v_id = d.get('version_id')
        changes = []
        if v_id:
            cursor.execute('SELECT * FROM version_changes WHERE version_id = ? ORDER BY id ASC', (v_id,))
            changes = [dict(c) for c in cursor.fetchall()]
        results.append(format_doc_dict(d, changes))
    conn.close()
    return results

def update_document_content(doc_id, content, summary=None, extracted_claim=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if summary and extracted_claim:
        cursor.execute('''
            UPDATE documents 
            SET content = ?, summary = ?, extracted_claim = ?
            WHERE id = ?
        ''', (content, summary, extracted_claim, doc_id))
    else:
        cursor.execute('''
            UPDATE documents 
            SET content = ?
            WHERE id = ?
        ''', (content, doc_id))
    conn.commit()
    conn.close()
    return get_document_by_id(doc_id)

def delete_document(doc_identifier, delete_all_versions=False):
    """
    Deletes a document from SQLite.
    If delete_all_versions is False (DEFAULT):
        Deletes ONLY the specific document/version row.
        Preserves all other versions in the document's history.
    If delete_all_versions is True:
        Deletes all versions belonging to the same logical file_id.
    """
    import os
    conn = get_db_connection()
    cursor = conn.cursor()

    doc = None
    # 1. Try numeric lookup first
    try:
        numeric_id = int(doc_identifier)
        cursor.execute('SELECT * FROM documents WHERE id = ?', (numeric_id,))
        doc = cursor.fetchone()
        if not doc:
            cursor.execute('SELECT * FROM document_versions WHERE id = ?', (numeric_id,))
            doc = cursor.fetchone()
    except (ValueError, TypeError):
        pass

    # 2. Try version_id lookup
    if not doc:
        cursor.execute('SELECT * FROM documents WHERE version_id = ?', (str(doc_identifier),))
        doc = cursor.fetchone()
        if not doc:
            cursor.execute('SELECT * FROM document_versions WHERE version_id = ?', (str(doc_identifier),))
            doc = cursor.fetchone()

    # 3. Try file_id lookup
    if not doc:
        cursor.execute('SELECT * FROM documents WHERE file_id = ?', (str(doc_identifier),))
        doc = cursor.fetchone()
        if not doc:
            cursor.execute('SELECT * FROM document_versions WHERE file_id = ?', (str(doc_identifier),))
            doc = cursor.fetchone()

    # 4. Try name/filename lookup as fallback
    if not doc:
        cursor.execute('SELECT * FROM documents WHERE name = ?', (str(doc_identifier),))
        doc = cursor.fetchone()
        if not doc:
            cursor.execute('SELECT * FROM document_versions WHERE filename = ?', (str(doc_identifier),))
        doc = cursor.fetchone()

    if not doc:
        conn.close()
        return {'success': False, 'error': f'Document {doc_identifier} not found in database'}

    doc_dict = dict(doc)
    doc_id = doc_dict.get('id')
    file_id = doc_dict.get('file_id') or f"DOC-{doc_id}"
    version_id = doc_dict.get('version_id')
    version_number = doc_dict.get('version_number') or doc_dict.get('version') or 1
    filename = doc_dict.get('name') or doc_dict.get('filename') or 'Document'
    file_path = doc_dict.get('file_path')

    if delete_all_versions and file_id:
        # Find all associated document IDs and version IDs
        cursor.execute('SELECT id, version_id, file_path FROM documents WHERE file_id = ?', (file_id,))
        docs_rows = cursor.fetchall()
        cursor.execute('SELECT id, version_id, file_path FROM document_versions WHERE file_id = ?', (file_id,))
        vers_rows = cursor.fetchall()

        all_d_ids = {r['id'] for r in docs_rows if r['id']}
        all_v_ids = {r['version_id'] for r in docs_rows if r['version_id']} | {r['version_id'] for r in vers_rows if r['version_id']}
        file_paths = {r['file_path'] for r in docs_rows if r['file_path']} | {r['file_path'] for r in vers_rows if r['file_path']}

        cursor.execute('DELETE FROM documents WHERE file_id = ?', (file_id,))
        cursor.execute('DELETE FROM document_versions WHERE file_id = ?', (file_id,))
        for d_id in all_d_ids:
            cursor.execute('DELETE FROM claims WHERE document_id = ?', (d_id,))
        for v_id in all_v_ids:
            cursor.execute('DELETE FROM claims WHERE version_id = ?', (v_id,))
            cursor.execute('DELETE FROM version_changes WHERE version_id = ?', (v_id,))
        cursor.execute('DELETE FROM version_changes WHERE file_id = ?', (file_id,))
        cursor.execute('DELETE FROM version_conflicts WHERE file_id = ?', (file_id,))

        conn.commit()
        conn.close()

        for fp in file_paths:
            try:
                if fp and os.path.exists(fp) and ('uploads' in fp or 'tmp' in fp):
                    os.remove(fp)
            except Exception:
                pass

        sync_dependent_data_after_change()
        return {
            'success': True,
            'deleted_all': True,
            'file_id': file_id,
            'filename': filename,
            'message': f"All versions of '{filename}' ({file_id}) deleted successfully."
        }
    else:
        # PRESERVE VERSION HISTORY: Delete ONLY this specific version/document record!
        if doc_id:
            cursor.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
            cursor.execute('DELETE FROM claims WHERE document_id = ?', (doc_id,))
        if version_id:
            cursor.execute('DELETE FROM documents WHERE version_id = ?', (version_id,))
            cursor.execute('DELETE FROM document_versions WHERE version_id = ?', (version_id,))
            cursor.execute('DELETE FROM claims WHERE version_id = ?', (version_id,))
            cursor.execute('DELETE FROM version_changes WHERE version_id = ?', (version_id,))

        cursor.execute('SELECT COUNT(*) as cnt FROM document_versions WHERE file_id = ?', (file_id,))
        row = cursor.fetchone()
        remaining_count = row['cnt'] if row else 0

        cursor.execute('SELECT COUNT(*) as cnt FROM documents WHERE file_id = ?', (file_id,))
        d_row = cursor.fetchone()
        remaining_docs = d_row['cnt'] if d_row else 0

        conn.commit()
        conn.close()

        if file_path:
            try:
                conn_check = get_db_connection()
                c_check = conn_check.cursor()
                c_check.execute('SELECT COUNT(*) as c FROM documents WHERE file_path = ?', (file_path,))
                c1 = c_check.fetchone()['c']
                c_check.execute('SELECT COUNT(*) as c FROM document_versions WHERE file_path = ?', (file_path,))
                c2 = c_check.fetchone()['c']
                conn_check.close()
                if c1 == 0 and c2 == 0 and os.path.exists(file_path) and ('uploads' in file_path or 'tmp' in file_path):
                    os.remove(file_path)
            except Exception:
                pass

        sync_dependent_data_after_change()
        return {
            'success': True,
            'deleted_all': False,
            'file_id': file_id,
            'version_id': version_id,
            'version_number': version_number,
            'filename': filename,
            'remaining_versions': max(remaining_count, remaining_docs),
            'message': f"Version {version_number} of '{filename}' deleted. Version history preserved ({max(remaining_count, remaining_docs)} remaining)."
        }

def find_version_by_checksum(checksum, file_id=None):
    """Checks if a file with this exact SHA-256 hash already exists."""
    if not checksum:
        return None
    conn = get_db_connection()
    cursor = conn.cursor()
    if file_id:
        cursor.execute('SELECT * FROM document_versions WHERE checksum = ? AND file_id = ? LIMIT 1', (checksum, file_id))
    else:
        cursor.execute('SELECT * FROM document_versions WHERE checksum = ? LIMIT 1', (checksum,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return format_doc_dict(dict(row))
    return None

def find_parent_file_by_name(filename):
    """Finds the canonical document family for a given filename."""
    if not filename:
        return None
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT file_id, version_id, version_number, filename, uploader
        FROM document_versions 
        WHERE LOWER(filename) = LOWER(?)
        ORDER BY version_number DESC LIMIT 1
    ''', (filename,))
    row = cursor.fetchone()
    if row:
        res = {
            'file_id': row['file_id'],
            'latest_version_id': row['version_id'],
            'latest_version': row['version_number'],
            'filename': row['filename'],
            'last_uploader': row['uploader']
        }
        conn.close()
        return res

    cursor.execute('''
        SELECT file_id, version_id, version_number, name, uploader
        FROM documents 
        WHERE LOWER(name) = LOWER(?)
        ORDER BY id DESC LIMIT 1
    ''', (filename,))
    row2 = cursor.fetchone()
    conn.close()
    if row2 and row2['file_id']:
        return {
            'file_id': row2['file_id'],
            'latest_version_id': row2['version_id'],
            'latest_version': row2['version_number'] or 1,
            'filename': row2['name'],
            'last_uploader': row2['uploader']
        }
    return None

def save_version_changes(version_id, file_id, changes_list):
    conn = get_db_connection()
    cursor = conn.cursor()
    saved = []
    now_str = datetime.now().strftime('%d %b %Y %H:%M')
    for ch in changes_list:
        cursor.execute('''
            INSERT INTO version_changes (
                version_id, file_id, field_name, old_value, new_value,
                change_type, modified_by, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            version_id, file_id,
            ch.get('field_name', 'Field'),
            ch.get('old_value', ''),
            ch.get('new_value', ''),
            ch.get('change_type', 'Modified'),
            ch.get('modified_by', 'Person B'),
            ch.get('timestamp', now_str)
        ))
        saved.append({
            'id': cursor.lastrowid,
            **ch
        })
    conn.commit()
    conn.close()
    return saved

def get_version_changes(version_id=None, file_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if version_id:
        cursor.execute('SELECT * FROM version_changes WHERE version_id = ? ORDER BY id ASC', (version_id,))
    elif file_id:
        cursor.execute('SELECT * FROM version_changes WHERE file_id = ? ORDER BY id ASC', (file_id,))
    else:
        cursor.execute('SELECT * FROM version_changes ORDER BY id DESC LIMIT 100')
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_version_conflict(file_id, v_id_a, v_id_b, field, val_a, val_b, uploader_a, uploader_b, reason):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO version_conflicts (
            file_id, version_id_a, version_id_b, field_name,
            value_a, value_b, uploader_a, uploader_b, status, reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Conflict Detected', ?)
    ''', (file_id, v_id_a, v_id_b, field, val_a, val_b, uploader_a, uploader_b, reason))
    c_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {
        'id': c_id,
        'file_id': file_id,
        'version_id_a': v_id_a,
        'version_id_b': v_id_b,
        'field_name': field,
        'value_a': val_a,
        'value_b': val_b,
        'uploader_a': uploader_a,
        'uploader_b': uploader_b,
        'status': 'Conflict Detected',
        'reason': reason
    }

def get_version_conflicts(file_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if file_id:
        cursor.execute('SELECT * FROM version_conflicts WHERE file_id = ? ORDER BY id DESC', (file_id,))
    else:
        cursor.execute('SELECT * FROM version_conflicts ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_integrated_document(file_id):
    """
    Synthesizes the master integrated document from all versions of a document family.
    Reconciles attributes while retaining full provenance to every contributing version.
    """
    versions = get_versions_by_file_id(file_id)
    if not versions:
        return None

    # Sort versions chronologically: v1, v2, v3
    sorted_vers = sorted(versions, key=lambda v: v.get('version_number', 1))

    contributors = list(dict.fromkeys([v.get('uploader', 'Unknown') for v in sorted_vers]))
    latest_ver = sorted_vers[-1]

    # Aggregate fields from version changes & claims
    fields = {}
    full_timeline = []

    for v in sorted_vers:
        v_num = v.get('version_number', 1)
        v_uploader = v.get('uploader', 'Unknown')
        v_id = v.get('version_id')

        # Add to timeline
        full_timeline.append({
            'version_number': v_num,
            'version_id': v_id,
            'uploader': v_uploader,
            'date': v.get('uploaded'),
            'summary': v.get('summary'),
            'changes': v.get('changes', [])
        })

        # Process version changes
        for ch in v.get('changes', []):
            fname = ch.get('field_name')
            if fname and fname != 'Document':
                if fname not in fields:
                    fields[fname] = {
                        'field': fname,
                        'current_value': ch.get('new_value'),
                        'contributed_by': v_uploader,
                        'source_version': f"Version {v_num}",
                        'source_version_id': v_id,
                        'history': []
                    }
                else:
                    fields[fname]['current_value'] = ch.get('new_value')
                    fields[fname]['contributed_by'] = v_uploader
                    fields[fname]['source_version'] = f"Version {v_num}"
                    fields[fname]['source_version_id'] = v_id

                fields[fname]['history'].append({
                    'version': f"Version {v_num}",
                    'value': ch.get('new_value'),
                    'contributor': v_uploader,
                    'timestamp': ch.get('timestamp')
                })

    # Also pull claims from the latest version to populate remaining fields
    latest_claims = get_claims_by_document(latest_ver.get('id', 0))
    for c in latest_claims:
        attr = c.get('attribute', 'Field')
        if attr not in fields:
            fields[attr] = {
                'field': attr,
                'current_value': c.get('value'),
                'contributed_by': latest_ver.get('uploader'),
                'source_version': f"Version {latest_ver.get('version_number')}",
                'source_version_id': latest_ver.get('version_id'),
                'history': [{
                    'version': f"Version {latest_ver.get('version_number')}",
                    'value': c.get('value'),
                    'contributor': latest_ver.get('uploader'),
                    'timestamp': latest_ver.get('uploaded')
                }]
            }

    # Check for active conflicts
    conflicts = get_version_conflicts(file_id)

    return {
        'file_id': file_id,
        'filename': latest_ver.get('filename'),
        'total_versions': len(sorted_vers),
        'contributors': contributors,
        'current_version': latest_ver.get('version_number'),
        'latest_version_id': latest_ver.get('version_id'),
        'synthesized_summary': f"Integrated master record compiled across {len(sorted_vers)} version(s) contributed by {', '.join(contributors)}.",
        'status': 'Conflict Detected' if conflicts else 'Integrated Single Source of Truth',
        'has_conflicts': len(conflicts) > 0,
        'conflicts': conflicts,
        'fields': list(fields.values()),
        'contributing_versions': [
            {
                'version_number': v.get('version_number'),
                'version_id': v.get('version_id'),
                'uploader': v.get('uploader'),
                'date': v.get('uploaded'),
                'checksum': v.get('checksum')
            }
            for v in sorted_vers
        ],
        'timeline': full_timeline
    }


# ================= CLAIMS OPERATIONS =================

def save_document_claims(document_id, claims_list):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM claims WHERE document_id = ?', (document_id,))
    
    saved_claims = []
    for c in claims_list:
        cursor.execute('''
            INSERT INTO claims (document_id, subject, attribute, value, source, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            document_id,
            c.get('subject', 'General Entity'),
            c.get('attribute', 'Attribute'),
            c.get('value', ''),
            c.get('source', f"Doc #{document_id}"),
            float(c.get('confidence', 0.85))
        ))
        saved_claims.append({
            'id': cursor.lastrowid,
            'document_id': document_id,
            'subject': c.get('subject'),
            'attribute': c.get('attribute'),
            'value': c.get('value'),
            'source': c.get('source'),
            'confidence': float(c.get('confidence', 0.85))
        })

    conn.commit()
    conn.close()
    return saved_claims

def get_claims_by_document(document_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM claims WHERE document_id = ? ORDER BY id ASC', (document_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_claims():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM claims ORDER BY id ASC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def sync_dependent_data_after_change():
    """
    Synchronizes cross-document conflicts, changes, and missing information
    whenever documents are uploaded, modified, or deleted.
    Guarantees that 0 documents in DB -> 0 conflicts, 0 changes, 0 missing info.
    """
    import conflict_detector
    import change_detector

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) as cnt FROM documents')
    doc_count = cursor.fetchone()['cnt']

    if doc_count == 0:
        cursor.execute('DELETE FROM conflicts')
        cursor.execute('DELETE FROM changes')
        cursor.execute('DELETE FROM missing_information')
        cursor.execute('DELETE FROM claims')
        cursor.execute('DELETE FROM document_versions')
        cursor.execute('DELETE FROM version_changes')
        cursor.execute('DELETE FROM version_conflicts')
        conn.commit()
        conn.close()
        return

    # Delete orphaned conflicts where claims or documents no longer exist
    cursor.execute('''
        DELETE FROM conflicts 
        WHERE (claim_id_1 IS NOT NULL AND claim_id_1 NOT IN (SELECT id FROM claims))
           OR (claim_id_2 IS NOT NULL AND claim_id_2 NOT IN (SELECT id FROM claims))
           OR (source_a_name NOT IN (SELECT name FROM documents UNION SELECT filename FROM document_versions))
           OR (source_b_name NOT IN (SELECT name FROM documents UNION SELECT filename FROM document_versions))
    ''')

    # Delete orphaned changes where claims no longer exist
    cursor.execute('''
        DELETE FROM changes
        WHERE (claim_id_old IS NOT NULL AND claim_id_old NOT IN (SELECT id FROM claims))
          AND (claim_id_new IS NOT NULL AND claim_id_new NOT IN (SELECT id FROM claims))
    ''')
    cursor.execute('''
        DELETE FROM changes
        WHERE source NOT IN (SELECT name FROM documents UNION SELECT filename FROM document_versions)
          AND (new_source IS NULL OR new_source NOT IN (SELECT name FROM documents UNION SELECT filename FROM document_versions))
    ''')

    # Delete missing info for deleted documents
    cursor.execute('''
        DELETE FROM missing_information
        WHERE (document_id IS NOT NULL AND document_id NOT IN (SELECT id FROM documents))
           OR (source_document NOT IN (SELECT name FROM documents UNION SELECT filename FROM document_versions))
    ''')

    conn.commit()
    conn.close()

    # Re-detect conflicts and changes from remaining active claims
    remaining_claims = get_all_claims()
    confs = conflict_detector.detect_conflicts_from_claims(remaining_claims)
    save_detected_conflicts(confs)

    remaining_docs = get_all_documents()
    docs_map = {d['id']: d for d in remaining_docs}
    chs = change_detector.detect_changes_from_claims(remaining_claims, docs_map)
    save_detected_changes(chs)

    missing = change_detector.detect_missing_information(remaining_docs, remaining_claims)
    save_missing_information(missing)

# ================= CONFLICTS OPERATIONS =================

def save_detected_conflicts(conflicts_list):
    """
    Saves newly detected conflicts into SQLite conflicts table.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM conflicts')
    
    saved = []
    for c in conflicts_list:
        cursor.execute('''
            INSERT INTO conflicts (
                claim_id_1, claim_id_2, reason, confidence, status,
                subject, attribute, source_a_name, source_a_claim, source_b_name, source_b_claim,
                discrepancy, severity
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            c.get('claim_id_1'),
            c.get('claim_id_2'),
            c.get('reason', 'Contradictory values asserted.'),
            str(c.get('confidence', '94%')),
            c.get('status', 'Conflict Detected'),
            c.get('subject', 'Milestone Entity'),
            c.get('attribute', 'Target Value'),
            c.get('sourceA', {}).get('name', 'Source A'),
            c.get('sourceA', {}).get('claim', ''),
            c.get('sourceB', {}).get('name', 'Source B'),
            c.get('sourceB', {}).get('claim', ''),
            c.get('discrepancy', 'Value mismatch'),
            c.get('severity', 'High')
        ))
        conflict_id = cursor.lastrowid
        saved.append({
            'id': conflict_id,
            **c
        })

    conn.commit()
    conn.close()
    return saved

def get_all_conflicts():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM conflicts ORDER BY id ASC')
    rows = cursor.fetchall()
    conn.close()
    
    formatted = []
    for r in rows:
        formatted.append({
            'id': r['id'],
            'claim_id_1': r['claim_id_1'],
            'claim_id_2': r['claim_id_2'],
            'subject': r['subject'] or 'Project Submission',
            'attribute': r['attribute'] or 'Submission Deadline',
            'topic': f"{r['subject'] or 'Project'} {r['attribute'] or 'Deadline'}",
            'category': r['subject'] or 'Milestone Timeline',
            'sourceA': {
                'name': r['source_a_name'] or 'Source A',
                'label': 'Source A',
                'claim': r['source_a_claim'] or '',
                'origin': f"Extracted from {r['source_a_name'] or 'Source A'}"
            },
            'sourceB': {
                'name': r['source_b_name'] or 'Source B',
                'label': 'Source B',
                'claim': r['source_b_claim'] or '',
                'origin': f"Extracted from {r['source_b_name'] or 'Source B'}"
            },
            'reason': r['reason'],
            'confidence': r['confidence'],
            'status': r['status'] or 'Conflict Detected',
            'discrepancy': r['discrepancy'] or f"{r['source_a_claim']} vs {r['source_b_claim']}",
            'severity': r['severity'] or 'High'
        })
    return formatted

def get_conflict_evidence(conflict_id):
    """
    Returns complete structured evidence for a conflict:
    1. Source A: Document name, original text/claim, date
    2. Source B: Document name, original text/claim, date
    3. Comparison: Subject, Attribute, Value A, Value B
    4. Explanation: 'These two claims refer to the same subject and attribute but contain different values.'
    5. Confidence score
    6. Source info: Source name, upload date, claim confidence
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM conflicts WHERE id = ?', (conflict_id,))
    c = cursor.fetchone()
    if not c:
        conn.close()
        return None
    c = dict(c)

    claim1 = None
    claim2 = None
    if c.get('claim_id_1'):
        cursor.execute('SELECT * FROM claims WHERE id = ?', (c['claim_id_1'],))
        row = cursor.fetchone()
        if row:
            claim1 = dict(row)
    if c.get('claim_id_2'):
        cursor.execute('SELECT * FROM claims WHERE id = ?', (c['claim_id_2'],))
        row = cursor.fetchone()
        if row:
            claim2 = dict(row)

    doc1 = None
    if claim1 and claim1.get('document_id'):
        cursor.execute('SELECT * FROM documents WHERE id = ?', (claim1['document_id'],))
        row = cursor.fetchone()
        if row:
            doc1 = dict(row)
    elif c.get('source_a_name'):
        cursor.execute('SELECT * FROM documents WHERE name = ?', (c['source_a_name'],))
        row = cursor.fetchone()
        if row:
            doc1 = dict(row)

    doc2 = None
    if claim2 and claim2.get('document_id'):
        cursor.execute('SELECT * FROM documents WHERE id = ?', (claim2['document_id'],))
        row = cursor.fetchone()
        if row:
            doc2 = dict(row)
    elif c.get('source_b_name'):
        cursor.execute('SELECT * FROM documents WHERE name = ?', (c['source_b_name'],))
        row = cursor.fetchone()
        if row:
            doc2 = dict(row)

    conn.close()

    subject = c.get('subject') or 'Project Submission'
    attribute = c.get('attribute') or 'Submission Deadline'
    val_a = c.get('source_a_claim') or (claim1['value'] if claim1 else '20 October')
    val_b = c.get('source_b_claim') or (claim2['value'] if claim2 else '25 October')
    src_a_name = c.get('source_a_name') or (doc1['name'] if doc1 else 'Source A')
    src_b_name = c.get('source_b_name') or (doc2['name'] if doc2 else 'Source B')

    def clean_snippet(doc, val, attr):
        if not doc:
            return f"{attr}: {val}" if attr and val else str(val)
        if doc.get('extracted_claim'):
            return doc['extracted_claim']
        content = doc.get('content') or ''
        val_clean = str(val).split(' at ')[0].split(',')[0].strip()
        for line in content.split('\n'):
            line_str = line.strip()
            if not line_str:
                continue
            if val_clean.lower() in line_str.lower() or str(val).lower() in line_str.lower():
                return line_str
        if doc.get('summary'):
            return doc['summary']
        return f"{attr}: {val}"

    orig_text_a = clean_snippet(doc1, val_a, attribute)
    orig_text_b = clean_snippet(doc2, val_b, attribute)

    conf_a = f"{int(round(float(claim1.get('confidence', 0.94)) * 100))}%" if claim1 else "94%"
    conf_b = f"{int(round(float(claim2.get('confidence', 0.94)) * 100))}%" if claim2 else "95%"

    return {
        'id': c['id'],
        'claim_id_1': c.get('claim_id_1'),
        'claim_id_2': c.get('claim_id_2'),
        'subject': subject,
        'attribute': attribute,
        'topic': f"{subject} {attribute}",
        'confidence': str(c.get('confidence', '94%')),
        'status': c.get('status', 'Conflict Detected'),
        'reason': c.get('reason'),
        'explanation': "These two claims refer to the same subject and attribute but contain different values.",
        'why_flagged': {
            'title': "WHY WAS THIS FLAGGED?",
            'topic': f"{subject} {attribute}",
            'subject': subject,
            'attribute': attribute,
            'source_a_doc': src_a_name,
            'source_a_claim': val_a,
            'source_a_quote': orig_text_a,
            'source_b_doc': src_b_name,
            'source_b_claim': val_b,
            'source_b_quote': orig_text_b,
            'why': f"Both refer to {subject} → {attribute}, but the values are different.",
            'explanation': "These two claims refer to the same subject and attribute but contain different values.",
            'confidence': str(c.get('confidence', '94%')),
            'status': "Conflict Detected"
        },
        'comparison': {
            'subject': subject,
            'attribute': attribute,
            'value_a': val_a,
            'value_b': val_b
        },
        'sourceA': {
            'document_name': src_a_name,
            'name': src_a_name,
            'label': 'Source A',
            'claim': val_a,
            'value': val_a,
            'original_text': orig_text_a,
            'date': (doc1.get('uploaded') if doc1 else '02 Oct 2026'),
            'upload_date': (doc1.get('uploaded') if doc1 else '02 Oct 2026'),
            'confidence': conf_a,
            'claim_confidence': conf_a,
            'source_name': src_a_name
        },
        'sourceB': {
            'document_name': src_b_name,
            'name': src_b_name,
            'label': 'Source B',
            'claim': val_b,
            'value': val_b,
            'original_text': orig_text_b,
            'date': (doc2.get('uploaded') if doc2 else '04 Oct 2026'),
            'upload_date': (doc2.get('uploaded') if doc2 else '04 Oct 2026'),
            'confidence': conf_b,
            'claim_confidence': conf_b,
            'source_name': src_b_name
        },
        'source_a': {
            'document_name': src_a_name,
            'name': src_a_name,
            'claim': val_a,
            'original_text': orig_text_a,
            'date': (doc1.get('uploaded') if doc1 else '02 Oct 2026')
        },
        'source_b': {
            'document_name': src_b_name,
            'name': src_b_name,
            'claim': val_b,
            'original_text': orig_text_b,
            'date': (doc2.get('uploaded') if doc2 else '04 Oct 2026')
        }
    }

# ================= STEP 7: CHANGES OPERATIONS =================

def save_detected_changes(changes_list):
    """Saves detected semantic changes into SQLite changes table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM changes')
    saved = []
    for ch in changes_list:
        cursor.execute('''
            INSERT INTO changes (
                subject, attribute, title, change_type, category,
                old_value, new_value, old_source, new_source, source,
                source_delta, date, timestamp, impact, is_conflict,
                claim_id_old, claim_id_new
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ch.get('subject', 'Project Milestone'),
            ch.get('attribute', 'Timeline'),
            ch.get('title', 'Detected Revision'),
            ch.get('change_type', 'deadline changed'),
            ch.get('category', 'Timeline'),
            ch.get('old_value', ''),
            ch.get('new_value', ''),
            ch.get('old_source', ''),
            ch.get('new_source', ''),
            ch.get('source', ch.get('new_source', 'latest document')),
            ch.get('source_delta', f"{ch.get('old_source')} → {ch.get('new_source')}"),
            ch.get('date', '04 Oct 2026'),
            ch.get('timestamp', ch.get('date', '04 Oct 2026')),
            ch.get('impact', 'Temporal update applied across project specifications.'),
            1 if ch.get('is_conflict') else 0,
            ch.get('claim_id_old'),
            ch.get('claim_id_new')
        ))
        saved.append({
            'id': cursor.lastrowid,
            **ch
        })
    conn.commit()
    conn.close()
    return saved

def get_all_changes():
    """Returns all detected changes from SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM changes ORDER BY id ASC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ================= STEP 7: MISSING INFORMATION OPERATIONS =================

def save_missing_information(missing_list):
    """Saves missing field gaps into SQLite missing_information table."""
    import json
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM missing_information')
    saved = []
    for m in missing_list:
        ctx = json.dumps(m.get('present_context', {})) if isinstance(m.get('present_context'), dict) else str(m.get('present_context', ''))
        cursor.execute('''
            INSERT INTO missing_information (
                document_id, source_document, related_subject, missing_field,
                field_key, status, severity, impact, present_context
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            m.get('document_id'),
            m.get('source_document', 'Document'),
            m.get('related_subject', 'Capstone Project Submission'),
            m.get('missing_field', 'Required Field'),
            m.get('field_key', 'field'),
            m.get('status', 'Missing Information'),
            m.get('severity', 'Medium'),
            m.get('impact', 'Field required for completeness'),
            ctx
        ))
        saved.append({
            'id': cursor.lastrowid,
            **m
        })
    conn.commit()
    conn.close()
    return saved

def get_all_missing_information():
    """Returns all missing information records from SQLite."""
    import json
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM missing_information ORDER BY id ASC')
    rows = cursor.fetchall()
    conn.close()
    formatted = []
    for r in rows:
        d = dict(r)
        if d.get('present_context'):
            try:
                d['present_context'] = json.loads(d['present_context'])
            except Exception:
                pass
        formatted.append(d)
    return formatted

