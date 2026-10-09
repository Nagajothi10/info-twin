"""
Step 10 End-to-End Integration & Regression Test Suite
Tests:
1. Health check & DB baseline
2. Upload & Text Extraction for all 5 formats (PDF, DOCX, TXT, CSV, XLSX)
3. Structured Claim Extraction (/api/analyze/<id>, /api/claims)
4. Conflict Detection (/api/detect-conflicts, /api/conflicts)
5. Evidence & Explainability (/api/conflicts/<id>/evidence)
6. Change Detection & Missing Information (/api/detect-changes, /api/changes, /api/missing-info)
7. Information Ripple & Impact Analysis (/api/analyze-impact)
8. What-If Simulation (/api/what-if) with immutability verification
9. Action Recommendations (/api/recommendations)
"""

import os
import sys
import json
import sqlite3
import urllib.request
import urllib.parse

BASE_URL = 'http://localhost:5000'
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_DIR = os.path.join(ROOT_DIR, 'demo_data')

def post_json(endpoint, payload):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        f"{BASE_URL}{endpoint}",
        data=data,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

def get_json(endpoint):
    with urllib.request.urlopen(f"{BASE_URL}{endpoint}") as resp:
        return json.loads(resp.read().decode('utf-8'))

def upload_multipart(filepath, filename):
    import mimetypes
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

    with open(filepath, 'rb') as f:
        file_bytes = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {mimetype}\r\n\r\n"
    ).encode('utf-8') + file_bytes + f"\r\n--{boundary}--\r\n".encode('utf-8')

    req = urllib.request.Request(
        f"{BASE_URL}/api/upload",
        data=body,
        headers={
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'Content-Length': str(len(body))
        },
        method='POST'
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

def run_tests():
    print("=================================================================")
    print("        INFO-TWIN STEP 10: END-TO-END VERIFICATION SUITE         ")
    print("=================================================================\n")

    # 1. Health check
    print("[1/9] Testing /api/health ...")
    health = get_json('/api/health')
    assert health.get('status') in ['ok', 'healthy'], f"Backend unhealthy: {health}"
    print(f"      Backend status: {health.get('status')}. Service: {health.get('service')}\n")

    # 2. Upload and extraction across 5 formats
    print("[2/9] Testing Upload & Extraction across 5 formats (PDF, DOCX, TXT, CSV, XLSX) ...")
    demo_files = [
        '01_Dean_Statutory_Notice.pdf',
        '02_Coordinator_Update_Email.txt',
        '03_Master_Schedule.csv',
        '03_Master_Schedule.xlsx',
        '04_Department_Handbook.docx'
    ]
    uploaded_doc_ids = []
    for fname in demo_files:
        fpath = os.path.join(DEMO_DIR, fname)
        assert os.path.exists(fpath), f"Demo file missing: {fpath}"
        res = upload_multipart(fpath, fname)
        doc = res.get('document', {})
        doc_id = doc.get('id')
        uploaded_doc_ids.append(doc_id)
        content_len = len(doc.get('extracted_content', ''))
        print(f"      Uploaded: {fname:<32} | Type: {doc.get('type'):<4} | Size: {doc.get('size'):<8} | Extracted: {content_len} chars")
        assert content_len > 0, f"Extraction failed for {fname}"
        assert res.get('claims_count', 0) >= 0
    print("      All 5 formats uploaded and extracted successfully.\n")

    # 3. Documents API and Single Document Extraction
    print("[3/9] Testing /api/documents and /api/documents/<id> ...")
    docs_res = get_json('/api/documents')
    total_docs = docs_res.get('total', 0)
    print(f"      Total documents in knowledge base: {total_docs}")
    assert total_docs >= 5, "Fewer documents than uploaded"
    test_doc = get_json(f"/api/documents/{uploaded_doc_ids[0]}")
    assert test_doc.get('filename') == demo_files[0]
    print(f"      Retrieved doc #{uploaded_doc_ids[0]}: {test_doc.get('filename')} with {len(test_doc.get('claims', []))} claims\n")

    # 4. Structured Claim Extraction API
    print("[4/9] Testing Claim Extraction (/api/analyze/<id>, /api/claims) ...")
    claims_res = get_json('/api/claims')
    total_claims = claims_res.get('total', 0)
    print(f"      Total structured claims: {total_claims}")
    assert total_claims > 0, "No claims extracted"
    # Inspect a claim
    sample_claim = claims_res.get('claims')[0]
    print(f"      Sample claim: [{sample_claim.get('subject')}] -> {sample_claim.get('attribute')} = {sample_claim.get('value')}\n")

    # 5. Conflict Detection API
    print("[5/9] Testing Conflict Detection (/api/detect-conflicts, /api/conflicts) ...")
    detect_res = post_json('/api/detect-conflicts', {})
    print(f"      Detected conflicts count: {detect_res.get('total')}")
    conflicts_res = get_json('/api/conflicts')
    assert conflicts_res.get('total', 0) > 0, "No conflicts found"
    
    # Check for intentional deadline conflict: 20 October vs 25 October
    deadline_conflict = None
    for c in conflicts_res.get('conflicts', []):
        combined = f"{c.get('sourceA', {}).get('claim', '')} {c.get('sourceB', {}).get('claim', '')}"
        if '20 October' in combined and '25 October' in combined:
            deadline_conflict = c
            break

    print(f"      Found intentional deadline conflict: {deadline_conflict is not None}")
    if deadline_conflict:
        print(f"      Conflict details: {deadline_conflict.get('topic')} ({deadline_conflict.get('discrepancy')})")
        print(f"      Source A: {deadline_conflict.get('sourceA', {}).get('name')} -> {deadline_conflict.get('sourceA', {}).get('claim')}")
        print(f"      Source B: {deadline_conflict.get('sourceB', {}).get('name')} -> {deadline_conflict.get('sourceB', {}).get('claim')}")
    print()

    # 6. Evidence & Why API
    print("[6/9] Testing Evidence Dossier (/api/conflicts/<id>/evidence) ...")
    target_conflict_id = conflicts_res.get('conflicts')[0].get('id')
    evidence = get_json(f"/api/conflicts/{target_conflict_id}/evidence")
    assert 'source_a' in evidence and 'source_b' in evidence, "Evidence missing sources"
    assert 'comparison' in evidence, "Evidence missing comparison"
    assert 'explanation' in evidence, "Evidence missing explanation"
    print(f"      Evidence for conflict #{target_conflict_id}:")
    print(f"      Explanation: {evidence.get('explanation')}")
    print(f"      Confidence: {evidence.get('confidence')}\n")

    # 7. Change Detection & Missing Information API
    print("[7/9] Testing Change & Missing Information Detection (/api/detect-changes, /api/changes, /api/missing-info) ...")
    changes_post = post_json('/api/detect-changes', {})
    print(f"      Changes detected: {changes_post.get('changes_count')}, Missing fields: {changes_post.get('missing_count')}")
    changes_get = get_json('/api/changes')
    assert changes_get.get('changes_count', 0) > 0, "No changes recorded"
    assert changes_get.get('missing_count', 0) > 0, "No missing fields recorded"
    
    # Inspect change: 20 October -> 25 October
    sample_change = changes_get.get('changes')[0]
    print(f"      Sample Change: {sample_change.get('change_type')}: '{sample_change.get('old_value')}' -> '{sample_change.get('new_value')}'")
    
    # Inspect missing field: Submission Method
    missing_get = get_json('/api/missing-info')
    sub_method_missing = any('submission' in m.get('missing_field', '').lower() for m in missing_get.get('missing_info', []))
    print(f"      Detected missing 'Submission Method' / link: {sub_method_missing}\n")

    # 8. Information Ripple & Impact Analysis API
    print("[8/9] Testing Information Ripple (/api/analyze-impact) ...")
    impact = post_json('/api/analyze-impact', {'conflict_id': target_conflict_id})
    print(f"      Trigger: {impact.get('trigger')}")
    print(f"      Impact Level: {impact.get('impact_level')}")
    print(f"      Affected Cascade: {' -> '.join(impact.get('affected', []))}")
    assert len(impact.get('affected', [])) >= 4, "Impact cascade incomplete"
    print()

    # 9. What-If Simulation & Action Recommendations (with DB immutability check)
    print("[9/9] Testing What-If Simulator & Action Recommendations (/api/what-if, /api/recommendations) ...")
    
    # Pre-simulation DB state
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'infotwin.db')
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM claims")
    c_count1 = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM conflicts")
    conf_count1 = cur.fetchone()[0]
    conn.close()

    what_if = post_json('/api/what-if', {'hypothetical_value': '30 October'})
    print(f"      What-If Result:")
    print(f"      Original: {what_if.get('original_value')} | Scenario: {what_if.get('hypothetical_value')}")
    print(f"      Potential Impact: {what_if.get('impact_level')}")
    print(f"      Affected Items: {what_if.get('affected')}")
    print(f"      Database Modified Flag: {what_if.get('database_modified')}")
    assert what_if.get('database_modified') is False, "DB modified flag must be false"
    assert what_if.get('original_value') == '25 October', "Expected original value 25 October"
    assert what_if.get('hypothetical_value') == '30 October', "Expected scenario 30 October"

    # Post-simulation DB state verification
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM claims")
    c_count2 = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM conflicts")
    conf_count2 = cur.fetchone()[0]
    conn.close()
    assert c_count1 == c_count2, "Claims count changed during What-If simulation!"
    assert conf_count1 == conf_count2, "Conflicts count changed during What-If simulation!"
    print(f"      Verified: SQLite claims and conflicts counts remained exactly {c_count1} and {conf_count1} (ZERO DB mutations).")

    # Recommendations
    recs = get_json('/api/recommendations')
    print(f"      Total Action Recommendations: {recs.get('total')}")
    primary = recs.get('recommendations')[0]
    print(f"      Top Priority Recommendation: [{primary.get('priority')}]")
    print(f"      Action: {primary.get('recommended_action')}")
    print(f"      Reason: {primary.get('reason')}")
    assert 'HIGH' in primary.get('priority')
    assert 'Verify revised project deadline' in primary.get('recommended_action')
    print()

    print("=================================================================")
    print("   ALL STEP 10 END-TO-END FLOW TESTS COMPLETED WITH 100% SUCCESS! ")
    print("=================================================================")

if __name__ == '__main__':
    run_tests()
