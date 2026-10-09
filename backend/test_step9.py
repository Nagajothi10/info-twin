import urllib.request
import json
import sqlite3
import sys

def test_api():
    base_url = 'http://localhost:5000'
    print("=== Testing INFO-TWIN Backend APIs (Step 9) ===")
    
    # 1. Health
    req = urllib.request.urlopen(f"{base_url}/api/health")
    print(f"1. Health check status: {req.status}")
    assert req.status == 200
    
    # 2. Record database state before simulation
    conn = sqlite3.connect('backend/infotwin.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM claims')
    claims_count_before = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM conflicts')
    conflicts_count_before = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM changes')
    changes_count_before = cursor.fetchone()[0]
    conn.close()
    print(f"DB before simulation: {claims_count_before} claims, {conflicts_count_before} conflicts, {changes_count_before} changes")

    # 3. Test POST /api/what-if with deadline 30 October
    what_if_data = json.dumps({'claim_id': 1, 'hypothetical_value': '30 October'}).encode('utf-8')
    req = urllib.request.Request(
        f"{base_url}/api/what-if",
        data=what_if_data,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print("2. POST /api/what-if result:")
        print(f"   Original Value:     {res.get('original_value')}")
        print(f"   Hypothetical Value: {res.get('hypothetical_value')}")
        print(f"   Impact Level:       {res.get('impact_level')}")
        print(f"   Affected Items:     {res.get('affected')}")
        print(f"   Database Modified:  {res.get('database_modified')}")
        print(f"   Explanation:        {res.get('explanation')}")

        assert res.get('original_value') == '25 October', f"Unexpected original_value: {res.get('original_value')}"
        assert res.get('hypothetical_value') == '30 October', f"Unexpected hypothetical_value: {res.get('hypothetical_value')}"
        assert res.get('impact_level') == 'High', f"Unexpected impact_level: {res.get('impact_level')}"
        assert 'Submission' in res.get('affected', [])
        assert 'Faculty Review' in res.get('affected', [])
        assert 'Evaluation' in res.get('affected', [])
        assert 'Viva Schedule' in res.get('affected', [])
        assert res.get('database_modified') is False, "Database modified flag must be False"

    # 4. Verify DB was NOT modified
    conn = sqlite3.connect('backend/infotwin.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM claims')
    claims_count_after = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM conflicts')
    conflicts_count_after = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM changes')
    changes_count_after = cursor.fetchone()[0]
    conn.close()
    assert claims_count_before == claims_count_after, "Claims count changed!"
    assert conflicts_count_before == conflicts_count_after, "Conflicts count changed!"
    assert changes_count_before == changes_count_after, "Changes count changed!"
    print("3. Verified SQLite database was NOT modified during What-If simulation!")

    # 5. Test GET /api/recommendations
    with urllib.request.urlopen(f"{base_url}/api/recommendations") as resp:
        rec_data = json.loads(resp.read().decode('utf-8'))
        print(f"\n4. GET /api/recommendations returned {rec_data.get('total')} recommendations:")
        for r in rec_data.get('recommendations', []):
            print(f"   - [{r.get('priority')}]")
            print(f"     Action: {r.get('recommended_action')}")
            print(f"     Reason: {r.get('reason')}")
            print(f"     Finding: {r.get('finding')}")
        assert rec_data.get('total') > 0
        primary = rec_data.get('recommendations')[0]
        assert 'HIGH' in primary.get('priority')
        assert 'Verify revised project deadline' in primary.get('recommended_action')
        assert 'A deadline change may affect submission and review schedules.' in primary.get('reason')

    # 6. Verify existing endpoints continue working
    print("\n5. Verifying regression of existing features:")
    for endpoint in ['/api/documents', '/api/conflicts', '/api/changes', '/api/missing-info']:
        with urllib.request.urlopen(f"{base_url}{endpoint}") as resp:
            print(f"   - Verified {endpoint}: status {resp.status}")
            assert resp.status == 200

    print("\n=======================================================")
    print(">>> ALL STEP 9 INTEGRATION & REGRESSION TESTS PASSED! <<<")
    print("=======================================================")

if __name__ == '__main__':
    test_api()
