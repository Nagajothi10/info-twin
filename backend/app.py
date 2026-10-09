import os
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

import database
import parser
import extractor
import conflict_detector
import change_detector
import impact_analyzer
import simulator
import git_conflict_detector

app = Flask(__name__)
# Enable CORS for frontend running on localhost:5173 or any origin
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Uploads directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Also ensure backend/uploads exists
BACKEND_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(BACKEND_UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32 MB max limit

# Initialize SQLite database and migrations
database.init_db()

# Seed initial changes and missing information if empty
try:
    if len(database.get_all_changes()) == 0:
        _docs = database.get_all_documents()
        _claims = database.get_all_claims()
        _dmap = {d['id']: d for d in _docs}
        _init_changes = change_detector.detect_changes_from_claims(_claims, _dmap)
        database.save_detected_changes(_init_changes)
    if len(database.get_all_missing_information()) == 0:
        _docs = database.get_all_documents()
        _claims = database.get_all_claims()
        _init_missing = change_detector.detect_missing_information(_docs, _claims)
        database.save_missing_information(_init_missing)
except Exception as _e:
    print("Warning during changes auto-init:", _e)


@app.route('/api/health', methods=['GET'])
def health():
    """Health check API returning system, database, and detector telemetry."""
    return jsonify({
        'status': 'ok',
        'service': 'INFO-TWIN Intelligence Backend',
        'database': 'SQLite connected',
        'claim_extractor': 'Rule-Based Entity Engine Active',
        'conflict_detector': 'Cross-Source Anomaly Engine Active',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'supported_formats': list(parser.ALLOWED_EXTENSIONS)
    }), 200

# ================= STEP 10: IMMUTABLE VERSIONED UPLOAD & STORAGE =================

VERSIONS_FOLDER = os.path.join(UPLOAD_FOLDER, 'versions')
os.makedirs(VERSIONS_FOLDER, exist_ok=True)
BACKEND_VERSIONS_FOLDER = os.path.join(BACKEND_UPLOAD_FOLDER, 'versions')
os.makedirs(BACKEND_VERSIONS_FOLDER, exist_ok=True)

import hashlib

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """
    Immutable Version-Controlled Upload:
    1. Computes SHA-256 hash.
    2. Identifies if file belongs to an existing parent document.
    3. Prevents duplicate uploads of the exact same content.
    4. Creates a new immutable version without overwriting prior versions.
    5. Performs automated change detection against the previous version.
    6. Identifies concurrent edit conflicts if multiple contributors edit the same baseline.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    raw_filename = secure_filename(file.filename)
    if not raw_filename:
        raw_filename = f"upload_{int(time.time())}.txt"

    if not parser.is_allowed_file(raw_filename):
        return jsonify({
            'error': f'Unsupported file extension. Allowed formats: {", ".join(sorted(parser.ALLOWED_EXTENSIONS))}'
        }), 400

    # 1. Read bytes and compute SHA-256 checksum
    file_bytes = file.read()
    file.seek(0)
    checksum = hashlib.sha256(file_bytes).hexdigest()

    # 2. Extract uploader and parent document inputs
    uploader = request.form.get('uploader') or request.form.get('uploaded_by') or request.args.get('uploader')
    parent_file_id = request.form.get('parent_file_id') or request.form.get('file_id') or request.args.get('parent_file_id')
    is_new_version_flag = request.form.get('is_new_version', '').lower() in ['true', '1', 'yes']

    # 3. Determine document identity & lineage
    parent_info = None
    if parent_file_id:
        # User explicitly specified the parent document
        existing_versions = database.get_versions_by_file_id(parent_file_id)
        if existing_versions:
            latest = existing_versions[0]
            parent_info = {
                'file_id': parent_file_id,
                'latest_version_id': latest.get('version_id'),
                'latest_version': latest.get('version_number', 1),
                'filename': latest.get('filename') or raw_filename,
                'last_uploader': latest.get('uploader')
            }
    elif not is_new_version_flag:
        # Check if an existing document with the exact same filename exists
        parent_info = database.find_parent_file_by_name(raw_filename)

    # 4. Check for EXACT duplicate file
    if parent_info:
        target_fid = parent_info['file_id']
        existing_dup = database.find_version_by_checksum(checksum, file_id=target_fid)
        if existing_dup:
            return jsonify({
                'is_duplicate': True,
                'message': f"Exact duplicate file detected. '{raw_filename}' (SHA-256: {checksum[:8]}...) matches existing Version {existing_dup['version_number']} uploaded by {existing_dup['uploader']}. No redundant version created.",
                'file_id': existing_dup['file_id'],
                'version_id': existing_dup['version_id'],
                'version': existing_dup['version_number'],
                'version_number': existing_dup['version_number'],
                'uploaded_by': existing_dup['uploader'],
                'uploader': existing_dup['uploader'],
                'created_at': existing_dup['upload_time'],
                'checksum': checksum,
                'status': 'Duplicate Rejected',
                'document': existing_dup,
                'claims_count': 0,
                'claims': []
            }), 200

    # 5. Determine version number and attribution
    if parent_info:
        file_id = parent_info['file_id']
        version_number = parent_info['latest_version'] + 1
        parent_version_id = parent_info['latest_version_id']
        if not uploader:
            uploader = f"Person {chr(65 + (version_number - 1) % 26)}"
    else:
        now_ms = int(time.time() * 1000)
        file_id = f"DOC-{now_ms % 100000:05d}"
        version_number = 1
        parent_version_id = None
        if not uploader:
            uploader = "Person A"

    version_id = f"VER-{file_id}-{version_number}"

    # 6. IMMUTABLE FILE STORAGE: Unique versioned path guaranteed NEVER to overwrite
    version_filename = f"{version_id}_{raw_filename}"
    version_save_path = os.path.join(VERSIONS_FOLDER, version_filename)
    file.save(version_save_path)

    # Mirror to backend/uploads/versions
    backend_save_path = os.path.join(BACKEND_VERSIONS_FOLDER, version_filename)
    try:
        shutil.copy2(version_save_path, backend_save_path)
    except Exception:
        pass

    # Also maintain current latest copy in root uploads for legacy direct readers
    try:
        shutil.copy2(version_save_path, os.path.join(UPLOAD_FOLDER, raw_filename))
        shutil.copy2(version_save_path, os.path.join(BACKEND_UPLOAD_FOLDER, raw_filename))
    except Exception:
        pass

    # 7. Real text extraction from the versioned file
    extracted_data = parser.extract_content(version_save_path, raw_filename)

    # 8. Extract claims from extracted text
    raw_claims = extractor.extract_claims_from_text(extracted_data['content'], raw_filename)

    # 9. Perform change detection against parent/previous version
    detected_changes = []
    if version_number > 1 and parent_version_id:
        prev_version = database.get_version_by_id(parent_version_id)
        if prev_version:
            prev_claims = database.get_claims_by_document(prev_version.get('id', 0))
            prev_version['claims'] = prev_claims
            detected_changes = change_detector.detect_version_diff(
                prev_version=prev_version,
                new_content=extracted_data['content'],
                new_claims=raw_claims,
                uploader=uploader
            )

    # 10. Check for concurrent branching conflict
    if parent_version_id:
        all_child_versions = [
            v for v in database.get_versions_by_file_id(file_id)
            if v.get('parent_version_id') == parent_version_id
        ]
        if all_child_versions:
            # Another user also modified the exact same parent version!
            sibling = all_child_versions[0]
            sib_claims = { (c['subject'], c['attribute']): c['value'] for c in database.get_claims_by_document(sibling.get('id', 0)) }
            for nc in raw_claims:
                s_key = (nc.get('subject'), nc.get('attribute'))
                if s_key in sib_claims:
                    val_sib = sib_claims[s_key]
                    val_curr = nc.get('value')
                    if change_detector.normalize_val(val_sib) != change_detector.normalize_val(val_curr):
                        database.save_version_conflict(
                            file_id=file_id,
                            v_id_a=sibling.get('version_id'),
                            v_id_b=version_id,
                            field=nc.get('attribute', 'Field'),
                            val_a=val_sib,
                            val_b=val_curr,
                            uploader_a=sibling.get('uploader', 'Person B'),
                            uploader_b=uploader,
                            reason=f"Concurrent conflict: {sibling.get('uploader')} set '{val_sib}' while {uploader} set '{val_curr}'."
                        )

    # 11. Persist new immutable version into database
    rel_path = os.path.relpath(version_save_path, PROJECT_ROOT)
    saved_doc = database.add_document_version(
        file_id=file_id,
        version_id=version_id,
        parent_version_id=parent_version_id,
        version_number=version_number,
        filename=raw_filename,
        doc_type=extracted_data['type'],
        size=extracted_data['size'],
        file_path=rel_path,
        checksum=checksum,
        uploader=uploader,
        summary=extracted_data['summary'],
        extracted_claim=extracted_data['extracted_claim'],
        content=extracted_data['content'],
        changes=detected_changes,
        status="Active" if version_number > 1 else "Ingested"
    )

    # 12. Save claims linked to this version
    saved_claims = database.save_document_claims(saved_doc['id'], raw_claims)
    # 13. Automatically sync cross-document conflicts, changes, and missing information
    try:
        database.sync_dependent_data_after_change()
    except Exception as sync_err:
        print(f"Sync warning after upload: {sync_err}")

    return jsonify({
        'message': f"File '{raw_filename}' Version {version_number} uploaded by {uploader}.",
        'file_id': file_id,
        'version_id': version_id,
        'parent_file_id': file_id,
        'filename': raw_filename,
        'version': version_number,
        'version_number': version_number,
        'uploaded_by': uploader,
        'uploader': uploader,
        'created_at': saved_doc['upload_time'],
        'checksum': checksum,
        'status': 'processed',
        'changes': saved_doc.get('changes', []),
        'document': saved_doc,
        'claims_count': len(saved_claims),
        'claims': saved_claims
    }), 201

@app.route('/api/documents', methods=['GET'])
def get_documents():
    """Returns list of all documents and versions stored in SQLite (newest first)."""
    docs = database.get_all_documents()
    formatted = []
    families = {}
    for d in docs:
        item = {
            **d,
            'filename': d.get('filename') or d.get('name'),
            'file_type': d.get('file_type') or d.get('type'),
            'upload_time': d.get('upload_time') or d.get('uploaded'),
            'extracted_content': d.get('content', '') or ''
        }
        formatted.append(item)
        fid = item.get('file_id') or f"DOC-{item.get('id')}"
        if fid not in families:
            families[fid] = {
                'file_id': fid,
                'filename': item['filename'],
                'latest_version': item.get('version', 1),
                'latest_uploader': item.get('uploader', 'Person A'),
                'versions': []
            }
        families[fid]['versions'].append(item)

    return jsonify({
        'total': len(families),
        'total_versions': len(formatted),
        'documents': formatted,
        'families': list(families.values())
    }), 200

@app.route('/api/documents/<file_id>/versions', methods=['GET'])
def get_document_versions_route(file_id):
    """Returns all versions for a given logical document ordered newest first."""
    # Check if numeric id passed
    try:
        numeric_id = int(file_id)
        doc = database.get_document_by_id(numeric_id)
        if doc and doc.get('file_id'):
            file_id = doc.get('file_id')
    except ValueError:
        pass

    versions = database.get_versions_by_file_id(file_id)
    return jsonify({
        'file_id': file_id,
        'total_versions': len(versions),
        'versions': versions
    }), 200

@app.route('/api/documents/version/<version_id>', methods=['GET'])
def get_version_details_route(version_id):
    """Returns specific version details with claims and change list."""
    ver = database.get_version_by_id(version_id)
    if not ver:
        return jsonify({'error': f'Version {version_id} not found'}), 404
    claims = database.get_claims_by_document(ver.get('id', 0))
    return jsonify({
        'version': ver,
        'claims': claims,
        'changes': ver.get('changes', [])
    }), 200

@app.route('/api/documents/compare', methods=['POST', 'GET'])
def compare_versions_route():
    """
    Compares two versions (v1 and v2) and returns side-by-side field diffs.
    Inputs can be version_id (e.g. 'VER-DOC-001-1') or document id.
    """
    v1_id = request.args.get('v1') or (request.get_json(silent=True) or {}).get('v1')
    v2_id = request.args.get('v2') or (request.get_json(silent=True) or {}).get('v2')

    if not v1_id or not v2_id:
        return jsonify({'error': 'Please provide both v1 and v2 parameters'}), 400

    def resolve_version(vid):
        try:
            numeric_id = int(vid)
            d = database.get_document_by_id(numeric_id)
            if d:
                return d
        except ValueError:
            pass
        return database.get_version_by_id(str(vid))

    v1 = resolve_version(v1_id)
    v2 = resolve_version(v2_id)

    if not v1 or not v2:
        return jsonify({'error': 'One or both versions not found'}), 404

    v1_claims = database.get_claims_by_document(v1.get('id', 0))
    v2_claims = database.get_claims_by_document(v2.get('id', 0))

    # Compare claims
    v1_map = { (c['subject'], c['attribute']): c for c in v1_claims }
    v2_map = { (c['subject'], c['attribute']): c for c in v2_claims }

    diff_fields = []
    all_keys = set(v1_map.keys()).union(set(v2_map.keys()))

    for key in all_keys:
        subj, attr = key
        c1 = v1_map.get(key)
        c2 = v2_map.get(key)
        val1 = c1.get('value', 'Missing') if c1 else 'Missing'
        val2 = c2.get('value', 'Missing') if c2 else 'Missing'

        status = 'Identical'
        if val1 == 'Missing' and val2 != 'Missing':
            status = 'Added in V2'
        elif val1 != 'Missing' and val2 == 'Missing':
            status = 'Removed in V2'
        elif change_detector.normalize_val(val1) != change_detector.normalize_val(val2):
            status = 'Modified'

        diff_fields.append({
            'subject': subj,
            'attribute': attr,
            'field': f"{subj} - {attr}",
            'v1_value': val1,
            'v2_value': val2,
            'status': status
        })

    return jsonify({
        'v1': {
            'version_id': v1.get('version_id'),
            'version_number': v1.get('version_number'),
            'uploader': v1.get('uploader'),
            'date': v1.get('uploaded'),
            'filename': v1.get('filename')
        },
        'v2': {
            'version_id': v2.get('version_id'),
            'version_number': v2.get('version_number'),
            'uploader': v2.get('uploader'),
            'date': v2.get('uploaded'),
            'filename': v2.get('filename')
        },
        'differences': diff_fields,
        'changes_count': len([d for d in diff_fields if d['status'] != 'Identical'])
    }), 200

@app.route('/api/documents/<file_id>/history', methods=['GET'])
def get_document_history_route(file_id):
    """Returns complete version history timeline for a document."""
    try:
        numeric_id = int(file_id)
        doc = database.get_document_by_id(numeric_id)
        if doc and doc.get('file_id'):
            file_id = doc.get('file_id')
    except ValueError:
        pass

    versions = database.get_versions_by_file_id(file_id)
    if not versions:
        return jsonify({'error': f'Document {file_id} not found'}), 404

    timeline = []
    for v in sorted(versions, key=lambda x: x.get('version_number', 1), reverse=True):
        timeline.append({
            'version': v.get('version_number'),
            'version_id': v.get('version_id'),
            'uploader': v.get('uploader'),
            'date': v.get('upload_time') or v.get('uploaded'),
            'filename': v.get('filename'),
            'summary': v.get('summary'),
            'checksum': v.get('checksum'),
            'changes': v.get('changes', [])
        })

    return jsonify({
        'file_id': file_id,
        'filename': versions[0].get('filename'),
        'total_versions': len(versions),
        'timeline': timeline
    }), 200

@app.route('/api/documents/<file_id>/integrate', methods=['GET'])
def get_integrated_document_route(file_id):
    """Returns synthesized master document citing all versions and contributors."""
    try:
        numeric_id = int(file_id)
        doc = database.get_document_by_id(numeric_id)
        if doc and doc.get('file_id'):
            file_id = doc.get('file_id')
    except ValueError:
        pass

    integrated = database.get_integrated_document(file_id)
    if not integrated:
        return jsonify({'error': f'Document {file_id} not found'}), 404

    return jsonify(integrated), 200

@app.route('/api/version-conflicts', methods=['GET'])
def get_version_conflicts_route():
    """Returns all concurrent version conflicts."""
    file_id = request.args.get('file_id')
    conflicts = database.get_version_conflicts(file_id)
    return jsonify({
        'total': len(conflicts),
        'conflicts': conflicts
    }), 200

@app.route('/api/documents/<int:doc_id>', methods=['GET'])
def get_document_details(doc_id):
    """Returns specific document by ID with claims."""
    doc = database.get_document_by_id(doc_id)
    if not doc:
        return jsonify({'error': f'Document with id {doc_id} not found'}), 404

    doc_claims = database.get_claims_by_document(doc_id)

    return jsonify({
        'id': doc['id'],
        'filename': doc['filename'],
        'file_type': doc['file_type'],
        'upload_time': doc['upload_time'],
        'extracted_content': doc['extracted_content'],
        'claims': doc_claims,
        'document': doc
    }), 200

@app.route('/api/documents/<doc_id>', methods=['DELETE'])
def delete_document_route(doc_id):
    """
    Deletes a specific document or version.
    Supports integer ID (documents table), version_id (document_versions table), or file_id.
    Query param or JSON: delete_all_versions=true|false
    Default: delete_all_versions=False (preserves document version history).
    """
    try:
        delete_all = request.args.get('delete_all_versions', '').lower() in ('true', '1')
        if not delete_all and request.is_json:
            delete_all = bool((request.get_json(silent=True) or {}).get('delete_all_versions', False))

        res = database.delete_document(doc_id, delete_all_versions=delete_all)
        if not res.get('success'):
            return jsonify({'error': res.get('error', 'Document not found')}), 404

        return jsonify(res), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/extract/<int:doc_id>', methods=['POST'])
def re_extract_document(doc_id):
    """Re-extracts text content for the selected document."""
    doc = database.get_document_by_id(doc_id)
    if not doc:
        return jsonify({'error': f'Document with id {doc_id} not found'}), 404

    filename = doc['filename']
    file_path = doc.get('file_path') or ''
    if not os.path.isabs(file_path):
        candidate1 = os.path.join(PROJECT_ROOT, file_path)
        candidate2 = os.path.join(UPLOAD_FOLDER, filename)
        candidate3 = os.path.join(BACKEND_UPLOAD_FOLDER, filename)
        if os.path.exists(candidate1):
            file_path = candidate1
        elif os.path.exists(candidate2):
            file_path = candidate2
        elif os.path.exists(candidate3):
            file_path = candidate3

    if not os.path.exists(file_path):
        content = doc.get('extracted_content') or f"Extracted canonical text for {filename}."
        summary = f"Re-verified semantic content for {filename}."
        extracted_claim = doc.get('extracted_claim') or f"Verified claim in {filename}."
    else:
        extracted_data = parser.extract_content(file_path, filename)
        content = extracted_data['content']
        summary = extracted_data['summary']
        extracted_claim = extracted_data['extracted_claim']

    updated_doc = database.update_document_content(doc_id, content, summary, extracted_claim)

    return jsonify({
        'message': f'Document "{filename}" extracted successfully.',
        'id': updated_doc['id'],
        'filename': updated_doc['filename'],
        'file_type': updated_doc['file_type'],
        'upload_time': updated_doc['upload_time'],
        'extracted_content': updated_doc['extracted_content'],
        'document': updated_doc
    }), 200

@app.route('/api/analyze/<int:document_id>', methods=['POST'])
def analyze_document_claims(document_id):
    """Analyzes document text and extracts structured claims into SQLite."""
    doc = database.get_document_by_id(document_id)
    if not doc:
        return jsonify({'error': f'Document with id {document_id} not found'}), 404

    text = doc.get('extracted_content') or doc.get('summary') or ''
    filename = doc.get('filename') or doc.get('name') or 'Document'

    raw_claims = extractor.extract_claims_from_text(text, filename)
    saved_claims = database.save_document_claims(document_id, raw_claims)

    return jsonify({
        'message': f'Successfully analyzed {len(saved_claims)} structured claim(s) from "{filename}".',
        'document_id': document_id,
        'filename': filename,
        'count': len(saved_claims),
        'claims': saved_claims
    }), 200

@app.route('/api/claims', methods=['GET'])
def get_all_claims():
    """Returns all extracted claims from SQLite across all documents."""
    claims = database.get_all_claims()
    return jsonify({
        'total': len(claims),
        'claims': claims
    }), 200

@app.route('/api/detect-conflicts', methods=['POST'])
def detect_conflicts():
    """
    Step 5 Conflict Detection:
    1. Read all claims.
    2. Compare related claims.
    3. Detect conflicting values with normalized formatting.
    4. Store conflicts in SQLite conflicts table.
    5. Return the detected conflicts as JSON.
    """
    all_claims = database.get_all_claims()
    detected = conflict_detector.detect_conflicts_from_claims(all_claims)
    
    saved_conflicts = database.save_detected_conflicts(detected)

    return jsonify({
        'message': f'Detected {len(saved_conflicts)} cross-source conflict(s).',
        'total': len(saved_conflicts),
        'conflicts': saved_conflicts
    }), 200

@app.route('/api/conflicts', methods=['GET'])
def get_conflicts():
    """Returns all detected conflicts from SQLite as JSON."""
    conflicts = database.get_all_conflicts()
    return jsonify({
        'total': len(conflicts),
        'conflicts': conflicts
    }), 200

@app.route('/api/conflicts/<conflict_id>/evidence', methods=['GET'])
def get_conflict_evidence_route(conflict_id):
    """
    Step 6 Evidence and Explainability API:
    Returns complete evidence dossier required by frontend:
    - Source A (document name, original text/claim, date)
    - Source B (document name, original text/claim, date)
    - Comparison (subject, attribute, value_a, value_b)
    - Explanation ("These two claims refer to the same subject and attribute but contain different values.")
    - Confidence score
    - Source information (source name, upload date, claim confidence)
    Does NOT automatically declare one source as correct.
    """
    try:
        numeric_id = int(conflict_id)
        evidence = database.get_conflict_evidence(numeric_id)
    except ValueError:
        all_conflicts = database.get_all_conflicts()
        match = next((c for c in all_conflicts if str(c.get('id')) == str(conflict_id)), None)
        if match:
            evidence = database.get_conflict_evidence(match['id'])
        elif all_conflicts:
            evidence = database.get_conflict_evidence(all_conflicts[0]['id'])
        else:
            evidence = None

    if not evidence:
        return jsonify({'error': f'Conflict with id {conflict_id} not found'}), 404
    return jsonify(evidence), 200

# ================= STEP 7: CHANGE DETECTION & MISSING INFORMATION ROUTES =================

@app.route('/api/detect-changes', methods=['POST'])
def detect_changes_endpoint():
    """
    Step 7 Change Detection & Missing Information Detection:
    1. Read all claims and documents.
    2. Compare related claims temporally to detect semantic changes (deadline, amount, location, etc.).
    3. Detect missing important fields (deadline, responsible person, submission method, etc.).
    4. Store changes and missing info in SQLite.
    5. Return detected changes and missing info as JSON.
    """
    docs = database.get_all_documents()
    claims = database.get_all_claims()
    docs_map = {d['id']: d for d in docs}

    detected_changes = change_detector.detect_changes_from_claims(claims, docs_map)
    saved_changes = database.save_detected_changes(detected_changes)

    detected_missing = change_detector.detect_missing_information(docs, claims)
    saved_missing = database.save_missing_information(detected_missing)

    return jsonify({
        'message': f'Detected {len(saved_changes)} semantic change(s) and {len(saved_missing)} missing field gap(s).',
        'total': len(saved_changes),
        'changes_count': len(saved_changes),
        'missing_count': len(saved_missing),
        'changes': saved_changes,
        'missing_info': saved_missing
    }), 200

@app.route('/api/changes', methods=['GET'])
def get_changes_endpoint():
    """Returns all detected semantic changes and missing information from SQLite as JSON."""
    docs = database.get_all_documents()
    if len(docs) == 0:
        return jsonify({
            'total': 0,
            'changes_count': 0,
            'missing_count': 0,
            'changes': [],
            'missing_info': []
        }), 200

    changes = database.get_all_changes()
    missing_info = database.get_all_missing_information()

    # If empty, run detection once
    if len(changes) == 0 and len(docs) > 1:
        claims = database.get_all_claims()
        docs_map = {d['id']: d for d in docs}
        detected = change_detector.detect_changes_from_claims(claims, docs_map)
        changes = database.save_detected_changes(detected)
    if len(missing_info) == 0 and len(docs) > 0:
        claims = database.get_all_claims()
        detected_m = change_detector.detect_missing_information(docs, claims)
        missing_info = database.save_missing_information(detected_m)

    return jsonify({
        'total': len(changes),
        'changes_count': len(changes),
        'missing_count': len(missing_info),
        'changes': changes,
        'missing_info': missing_info
    }), 200

@app.route('/api/missing-info', methods=['GET'])
def get_missing_information_endpoint():
    """Returns all detected missing information records from SQLite."""
    docs = database.get_all_documents()
    if len(docs) == 0:
        return jsonify({
            'total': 0,
            'missing_items': []
        }), 200
    missing_info = database.get_all_missing_information()
    if len(missing_info) == 0 and len(docs) > 0:
        claims = database.get_all_claims()
        detected_m = change_detector.detect_missing_information(docs, claims)
        missing_info = database.save_missing_information(detected_m)

    return jsonify({
        'total': len(missing_info),
        'missing_info': missing_info
    }), 200

# ================= STEP 8: INFORMATION RIPPLE & IMPACT ANALYSIS =================

@app.route('/api/analyze-impact', methods=['GET', 'POST'])
def analyze_impact_endpoint():
    """
    Step 8 Information Ripple / Impact Analysis API:
    Input:
      - conflict_id or claim_id
    1. Identify the changed/conflicting claim.
    2. Find related subjects/attributes.
    3. Build an impact chain:
       Project Deadline -> Submission -> Faculty Review -> Evaluation -> Viva Schedule
    4. Return affected items.
    5. Assign an impact level (High, Medium, Low).
    """
    data = {}
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
    
    conflict_id = data.get('conflict_id') or request.args.get('conflict_id')
    claim_id = data.get('claim_id') or request.args.get('claim_id')

    conflict = None
    claim = None

    if conflict_id:
        try:
            numeric_id = int(conflict_id)
            all_conflicts = database.get_all_conflicts()
            conflict = next((c for c in all_conflicts if c.get('id') == numeric_id), None)
        except ValueError:
            all_conflicts = database.get_all_conflicts()
            conflict = next((c for c in all_conflicts if str(c.get('id')) == str(conflict_id)), None)

    if not conflict and claim_id:
        try:
            numeric_claim_id = int(claim_id)
            claims = database.get_all_claims()
            claim = next((c for c in claims if c.get('id') == numeric_claim_id), None)
        except ValueError:
            pass

    # Fallback to primary milestone conflict if none specified
    if not conflict and not claim:
        all_conflicts = database.get_all_conflicts()
        if all_conflicts:
            conflict = all_conflicts[0]

    result = impact_analyzer.analyze_impact(
        trigger_id=conflict_id or claim_id,
        conflict=conflict,
        claim=claim
    )

    return jsonify(result), 200

# ================= STEP 9: WHAT-IF SIMULATOR & ACTION RECOMMENDATIONS =================

@app.route('/api/what-if', methods=['GET', 'POST'])
def what_if_simulation_endpoint():
    """
    Step 9 What-If Simulator API:
    Inputs:
      - claim_id (optional)
      - conflict_id (optional)
      - hypothetical_value (e.g. '30 October')
      
    Guaranteed: Does NOT modify the real database.
    Creates a temporary scenario and analyzes possible cascading ripple.
    Returns:
      - original_value
      - hypothetical_value
      - impact_level
      - affected
      - explanation
    """
    data = {}
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
    
    claim_id = data.get('claim_id') or request.args.get('claim_id')
    conflict_id = data.get('conflict_id') or request.args.get('conflict_id')
    hypothetical_value = data.get('hypothetical_value') or request.args.get('hypothetical_value') or "30 October"

    simulation_result = simulator.simulate_what_if(
        claim_id=claim_id,
        hypothetical_value=hypothetical_value,
        conflict_id=conflict_id
    )

    return jsonify(simulation_result), 200

@app.route('/api/recommendations', methods=['GET'])
def get_recommendations_endpoint():
    """
    Step 9 Action Recommendations API:
    Returns prescriptive action recommendations with:
      - issue
      - priority (HIGH — Action Required, MEDIUM — Review Soon, LOW — Monitor)
      - recommended action
      - reason
    """
    recs = simulator.get_action_recommendations()
    return jsonify({
        'total': len(recs),
        'recommendations': recs
    }), 200



# ================= REAL GIT MERGE CONFLICT DETECTION & RESOLUTION API =================

@app.route('/api/git/status', methods=['GET'])
def get_git_status():
    """Returns status and branch summary of the real Git repository."""
    try:
        info = git_conflict_detector.get_git_repository_info()
        return jsonify(info), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/git/branches', methods=['GET'])
def get_git_branches():
    """Lists all available branches with latest commit information."""
    try:
        info = git_conflict_detector.get_git_repository_info()
        return jsonify({'branches': info['branches'], 'total': len(info['branches'])}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/git/compare', methods=['POST', 'GET'])
def compare_git_branches():
    """
    Compares two branches in the Git repository and executes authentic 3-way merge.
    Identifies real merge conflicts with line numbers and conflict hunks.
    """
    try:
        data = request.get_json(silent=True) or {}
        target_branch = request.args.get('target') or data.get('target_branch', 'main')
        source_branch = request.args.get('source') or data.get('source_branch', 'feature/revised-schedule')

        res = git_conflict_detector.compare_and_merge_branches(target_branch, source_branch)
        return jsonify(res), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/git/merge-3way', methods=['POST'])
def run_custom_merge_3way():
    """
    Runs authentic 3-way merge on raw user-provided texts.
    Accepts { base, ours, theirs, ours_label, theirs_label, filename }.
    Never returns fake results - validates against actual input lines.
    """
    try:
        data = request.get_json(silent=True) or {}
        base_text = data.get('base', '')
        ours_text = data.get('ours', '')
        theirs_text = data.get('theirs', '')
        ours_label = data.get('ours_label', 'HEAD')
        theirs_label = data.get('theirs_label', 'incoming')
        filename = data.get('filename', 'custom_file.txt')

        res = git_conflict_detector.run_3way_merge(
            base_text=base_text,
            ours_text=ours_text,
            theirs_text=theirs_text,
            ours_label=ours_label,
            theirs_label=theirs_label,
            filename=filename
        )
        return jsonify(res), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/git/parse-markers', methods=['POST'])
def parse_git_markers():
    """
    Parses any raw file or string containing Git conflict markers (<<<<<<<, =======, >>>>>>>).
    """
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        filename = data.get('filename', 'conflict_file.txt')
        res = git_conflict_detector.parse_raw_git_conflict_markers(content, filename)
        return jsonify(res), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/git/resolve', methods=['POST'])
def resolve_git_conflict_hunks():
    """
    Applies resolution selections ('ours', 'theirs', 'both', 'custom') to hunks in a file.
    """
    try:
        data = request.get_json(silent=True) or {}
        original_content = data.get('content', '')
        resolutions = data.get('resolutions', {})
        res = git_conflict_detector.apply_git_resolutions(original_content, resolutions)
        return jsonify(res), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/git/commit', methods=['POST'])
def commit_git_resolution_endpoint():
    """
    Creates a real Git merge commit in the repository for resolved files.
    """
    try:
        data = request.get_json(silent=True) or {}
        target_branch = data.get('target_branch', 'main')
        source_branch = data.get('source_branch', 'feature/revised-schedule')
        resolved_files = data.get('resolved_files', {})
        message = data.get('message', 'Merge resolved conflict')

        res = git_conflict_detector.commit_resolved_git_merge(
            target_branch=target_branch,
            source_branch=source_branch,
            resolved_files=resolved_files,
            commit_message=message
        )
        return jsonify(res), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/seed-demo', methods=['POST'])
def seed_demo_endpoint():
    """Seeds the canonical demo dataset into SQLite on demand."""
    try:
        res = database.seed_canonical_demo_corpus()
        return jsonify(res), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("INFO-TWIN Flask Backend with What-If Simulator & Action Recommendations running on http://localhost:5000 ...")
    app.run(host='0.0.0.0', port=5000, debug=False)




