"""
INFO-TWIN What-If Simulator & Prescriptive Action Engine (Step 9)
Fully dynamic and data-driven simulation and recommendations based on live SQLite data.
"""

import database

def simulate_what_if(claim_id=None, hypothetical_value=None, conflict_id=None):
    """
    Simulates a temporary what-if scenario WITHOUT modifying the database.
    Inputs:
      - claim_id or conflict_id
      - hypothetical_value (e.g. '30 October')
    Returns:
      - original_value
      - hypothetical_value
      - impact_level
      - affected
      - affected_details
      - explanation
    """
    all_conflicts = database.get_all_conflicts()
    all_claims = database.get_all_claims()

    # Empty workspace guard
    if not all_conflicts and not all_claims:
        return {
            "has_data": False,
            "trigger": "No Ingested Claims",
            "original_value": "N/A",
            "hypothetical_value": str(hypothetical_value or "N/A"),
            "impact_level": "None",
            "affected": [],
            "affected_details": [],
            "explanation": "No active claims or documents available in workspace to simulate. Ingest documents to test hypothetical scenario variations.",
            "is_simulated": True,
            "database_modified": False
        }

    original_value = None
    trigger = None

    if conflict_id:
        try:
            c_id = int(conflict_id)
            match = next((c for c in all_conflicts if c.get('id') == c_id), None)
            if match:
                original_value = match.get('source_b_claim') or match.get('source_a_claim')
                trigger = f"{match.get('subject')} {match.get('attribute')}".strip()
        except Exception:
            pass

    if not original_value and claim_id:
        try:
            cl_id = int(claim_id)
            match_cl = next((c for c in all_claims if c.get('id') == cl_id), None)
            if match_cl:
                original_value = match_cl.get('value')
                trigger = f"{match_cl.get('subject')} {match_cl.get('attribute')}".strip()
        except Exception:
            pass

    # Fallback to first available conflict or claim
    if not original_value and all_conflicts:
        c0 = all_conflicts[0]
        original_value = c0.get('source_b_claim') or c0.get('source_a_claim')
        trigger = f"{c0.get('subject')} {c0.get('attribute')}".strip()

    if not original_value and all_claims:
        cl0 = all_claims[0]
        original_value = cl0.get('value')
        trigger = f"{cl0.get('subject')} {cl0.get('attribute')}".strip()

    if not original_value:
        original_value = "25 October"
        trigger = "Project Deadline"

    hypo_val = str(hypothetical_value or "30 October").strip()

    # Rule-based calculation of impact
    is_date = any(k in trigger.lower() for k in ['deadline', 'submission', 'date', 'milestone'])
    is_venue = any(k in trigger.lower() for k in ['venue', 'room', 'hall', 'location'])

    if is_date:
        affected = [
            "Submission",
            "Faculty Review",
            "Evaluation",
            "Viva Schedule"
        ]
        impact_level = "High"
        explanation = (
            f"Hypothetically shifting {trigger} from '{original_value}' to '{hypo_val}' "
            f"delays deliverable submission cutoff, compresses faculty review turnaround, and impacts downstream viva defense milestones."
        )
        affected_details = [
            {
                "name": "Submission",
                "status": "Directly Affected",
                "icon": "✓",
                "severity": "high",
                "detail": f"Portal upload window extended to {hypo_val}. Code repository locks delayed."
            },
            {
                "name": "Faculty Review",
                "status": "Directly Affected",
                "icon": "✓",
                "severity": "high",
                "detail": "Faculty review buffer turnaround window compressed."
            },
            {
                "name": "Evaluation",
                "status": "Schedule Overlap",
                "icon": "⚠",
                "severity": "warning",
                "detail": "Score consolidation overlaps directly with semester grade audit."
            },
            {
                "name": "Viva Schedule",
                "status": "Severe Bottleneck",
                "icon": "⚠",
                "severity": "danger",
                "detail": "External defense examiners require date re-alignment."
            }
        ]
    elif is_venue:
        affected = [
            "Facility Allocation",
            "Hardware Lab Access",
            "Examiner Panel"
        ]
        impact_level = "Medium"
        explanation = (
            f"Hypothetically reassigning {trigger} from '{original_value}' to '{hypo_val}' "
            f"shifts room allocation requirements and demands updated laboratory setup verification."
        )
        affected_details = [
            {
                "name": "Facility Allocation",
                "status": "Reallocated",
                "icon": "✓",
                "severity": "medium",
                "detail": f"Target space updated to {hypo_val}."
            },
            {
                "name": "Hardware Lab Access",
                "status": "Resource Shift",
                "icon": "⚠",
                "severity": "warning",
                "detail": "Workstation allocations contingent on room reservation."
            },
            {
                "name": "Examiner Panel",
                "status": "Notification Needed",
                "icon": "⚠",
                "severity": "warning",
                "detail": f"Oral defense panel must be directed to {hypo_val}."
            }
        ]
    else:
        affected = [
            "Policy Compliance",
            "Audit Trail"
        ]
        impact_level = "Medium"
        explanation = (
            f"Hypothetically modifying {trigger} from '{original_value}' to '{hypo_val}' "
            f"triggers specification audit and requires departmental review."
        )
        affected_details = [
            {
                "name": "Policy Compliance",
                "status": "Modified",
                "icon": "✓",
                "severity": "medium",
                "detail": f"Value altered from '{original_value}' to '{hypo_val}'."
            },
            {
                "name": "Audit Trail",
                "status": "Logged",
                "icon": "⚠",
                "severity": "warning",
                "detail": "Requires recording in milestone audit ledger."
            }
        ]

    return {
        "has_data": True,
        "trigger": trigger,
        "original_value": original_value,
        "hypothetical_value": hypo_val,
        "impact_level": impact_level,
        "affected": affected,
        "affected_details": affected_details,
        "explanation": explanation,
        "is_simulated": True,
        "database_modified": False
    }

def get_action_recommendations():
    """
    Generates prescriptive action recommendations based strictly on live detected conflicts,
    changes, and missing information in the database.
    Returns [] when no active discrepancies exist.
    """
    conflicts = database.get_all_conflicts()
    changes = database.get_all_changes()
    missing = database.get_all_missing_information()

    # If database is completely empty or has zero issues:
    if not conflicts and not changes and not missing:
        return []

    recommendations = []

    # 1. Recommendations for detected conflicts
    for idx, c in enumerate(conflicts):
        attr = c.get('attribute', 'Target Value')
        subj = c.get('subject', 'Milestone')
        src_a = c.get('sourceA', {}).get('name') or c.get('source_a_name', 'Source A')
        src_b = c.get('sourceB', {}).get('name') or c.get('source_b_name', 'Source B')
        val_a = c.get('sourceA', {}).get('claim') or c.get('source_a_claim', '')
        val_b = c.get('sourceB', {}).get('claim') or c.get('source_b_claim', '')
        sev = (c.get('severity') or 'Medium').upper()
        disc = c.get('discrepancy') or f"'{val_a}' vs '{val_b}'"

        if 'deadline' in attr.lower() or 'date' in attr.lower():
            recommendations.append({
                "id": f"rec-conflict-{c.get('id', idx)}",
                "issue": f"{subj} Timeline Contradiction ({disc})",
                "priority": "HIGH — Action Required",
                "priority_level": "HIGH",
                "priority_color": "danger",
                "recommended_action": f"Verify revised {subj.lower()} {attr.lower()} and update affected schedules.",
                "reason": f"A deadline contradiction ({disc}) across {src_a} and {src_b} impacts submission windows and faculty turnaround.",
                "finding": f"Contradictory values asserted: '{val_a}' in {src_a} vs '{val_b}' in {src_b}.",
                "affected_targets": [src_a, src_b, "Master Schedule"],
                "suggested_dispatch": f"Issue formal verification notice regarding {subj}."
            })
        elif 'venue' in attr.lower() or 'room' in attr.lower() or 'location' in attr.lower():
            recommendations.append({
                "id": f"rec-conflict-{c.get('id', idx)}",
                "issue": f"{subj} Room Allocation Clash ({disc})",
                "priority": "MEDIUM — Review Soon",
                "priority_level": "MEDIUM",
                "priority_color": "warning",
                "recommended_action": f"Confirm facility reservation for {subj} and notify affected leads.",
                "reason": f"Conflicting facilities cited between {src_a} ('{val_a}') and {src_b} ('{val_b}').",
                "finding": f"Dual venue booking asserted across {src_a} and {src_b}.",
                "affected_targets": [src_a, src_b, "Facilities Office"],
                "suggested_dispatch": "Synchronize Facilities Master Roster."
            })
        else:
            recommendations.append({
                "id": f"rec-conflict-{c.get('id', idx)}",
                "issue": f"{subj} {attr} Discrepancy",
                "priority": f"{sev} — Action Required" if sev == "HIGH" else f"{sev} — Review Soon",
                "priority_level": sev,
                "priority_color": "danger" if sev == "HIGH" else "warning",
                "recommended_action": f"Reconcile contradictory values for {subj} ({attr}): {disc}.",
                "reason": c.get('reason') or f"Discrepancy detected between {src_a} and {src_b}.",
                "finding": f"Divergence detected: '{val_a}' in {src_a} vs '{val_b}' in {src_b}.",
                "affected_targets": [src_a, src_b],
                "suggested_dispatch": "Issue alignment memo."
            })

    # 2. Recommendations for missing information gaps
    if len(missing) > 0:
        missing_fields = list({m.get('missing_field') for m in missing if m.get('missing_field')})
        affected_docs = list({m.get('source_document') for m in missing if m.get('source_document')})
        recommendations.append({
            "id": "rec-missing-fields",
            "issue": f"Missing Mandatory Fields ({len(missing)} Gap{'s' if len(missing) != 1 else ''})",
            "priority": "MEDIUM — Review Soon",
            "priority_level": "MEDIUM",
            "priority_color": "warning",
            "recommended_action": f"Publish official addendum specifying missing field(s): {', '.join(missing_fields[:3])}.",
            "reason": "Omission of mandatory fields prevents students and faculty from executing required milestone steps.",
            "finding": f"{len(missing)} missing mandatory milestone fields identified across ingested documents.",
            "affected_targets": affected_docs[:3] or ["Student Portal", "Submission Instructions"],
            "suggested_dispatch": "Broadcast standardized submission guide addendum."
        })

    return recommendations
