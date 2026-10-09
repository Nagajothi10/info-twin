import re
from datetime import datetime

def normalize_value(val):
    """
    Normalizes dates, amounts, and text values for fair, robust comparison.
    """
    if not val:
        return ""
    val_clean = str(val).strip().lower()

    # 1. Date normalization (e.g. '20 October 2026 at 23:59 IST' -> '2026-10-20')
    date_match = re.search(
        r'(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s*(\d{4})?',
        val_clean
    )
    if date_match:
        day = date_match.group(1).zfill(2)
        month_str = date_match.group(2)[:3]
        year = date_match.group(3) or "2026"
        month_map = {
            'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
            'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
        }
        month = month_map.get(month_str, '10')
        return f"{year}-{month}-{day}"

    # ISO date match (2026-10-25)
    iso_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', val_clean)
    if iso_match:
        return iso_match.group(0)

    # 2. Venue normalization (e.g. 'Lab 302 AI Center' vs 'Lab 302' vs 'Seminar Hall A')
    if 'hall a' in val_clean or 'seminar hall' in val_clean:
        return 'seminar hall a'
    if 'lab 302' in val_clean:
        return 'lab 302'

    lab_match = re.search(r'(lab\s+\d+|seminar\s+hall\s+[a-z0-9]+|auditorium)', val_clean)
    if lab_match:
        return lab_match.group(1)

    # 3. Numeric / percentage normalization
    pct_match = re.search(r'(\d+)%', val_clean)
    if pct_match:
        return f"{pct_match.group(1)}%"

    # 4. Standard text normalization (strip non-alphanumeric)
    return re.sub(r'[^a-z0-9]', '', val_clean)

def are_attributes_related(attr1, attr2):
    """
    Checks if two attributes are identical or refer to the same conceptual aspect.
    """
    a1 = str(attr1).lower().strip()
    a2 = str(attr2).lower().strip()
    if a1 == a2:
        return True

    # Both refer to deadline / due date / submission date / cutoff
    is_date_1 = any(k in a1 for k in ['deadline', 'submission date', 'due date', 'cutoff', 'scheduled date'])
    is_date_2 = any(k in a2 for k in ['deadline', 'submission date', 'due date', 'cutoff', 'scheduled date'])
    if is_date_1 and is_date_2:
        return True

    # Both refer to venue / location / room
    is_venue_1 = any(k in a1 for k in ['venue', 'room', 'location', 'hall'])
    is_venue_2 = any(k in a2 for k in ['venue', 'room', 'location', 'hall'])
    if is_venue_1 and is_venue_2:
        return True

    # Both refer to late policy / grace period / penalties / buffer
    is_policy_1 = any(k in a1 for k in ['late', 'grace', 'penalty', 'tolerance', 'buffer'])
    is_policy_2 = any(k in a2 for k in ['late', 'grace', 'penalty', 'tolerance', 'buffer'])
    if is_policy_1 and is_policy_2:
        return True

    return False

def are_subjects_related(subj1, subj2):
    """
    Checks if subjects are identical or related in context.
    """
    s1 = str(subj1).lower().strip()
    s2 = str(subj2).lower().strip()
    if s1 == s2:
        return True

    # Project submission and milestones
    if ('submission' in s1 or 'project' in s1) and ('submission' in s2 or 'project' in s2):
        return True
    
    # Viva and event logistics
    if ('viva' in s1 or 'event' in s1 or 'defense' in s1 or 'logistics' in s1) and \
       ('viva' in s2 or 'event' in s2 or 'defense' in s2 or 'logistics' in s2):
        return True

    # Policy / regulations
    if ('policy' in s1 or 'regulation' in s1 or 'buffer' in s1) and \
       ('policy' in s2 or 'regulation' in s2 or 'buffer' in s2):
        return True

    return False

def detect_conflicts_from_claims(claims):
    """
    Compares all claims and identifies conflicting values asserted across different sources.
    Claims from the SAME document or same document lineage are skipped.
    Only actual discrepancies supported by the document claims are returned.
    """
    if not claims or len(claims) < 2:
        return []

    conflicts = []
    seen_pairs = set()

    for i in range(len(claims)):
        for j in range(i + 1, len(claims)):
            c1 = claims[i]
            c2 = claims[j]

            doc_id_1 = c1.get('document_id')
            doc_id_2 = c2.get('document_id')
            src1 = (c1.get('source') or '').strip()
            src2 = (c2.get('source') or '').strip()

            # Must come from different documents
            if doc_id_1 and doc_id_2 and doc_id_1 == doc_id_2:
                continue
            # Must not be the exact same source filename (skip versions of the same file)
            if src1 and src2 and src1.lower() == src2.lower():
                continue

            # Must have same or related subject
            if not are_subjects_related(c1.get('subject'), c2.get('subject')):
                continue

            # Must have same or related attribute
            if not are_attributes_related(c1.get('attribute'), c2.get('attribute')):
                continue

            # Normalize values
            norm_val_1 = normalize_value(c1.get('value', ''))
            norm_val_2 = normalize_value(c2.get('value', ''))

            # If normalized values differ, a discrepancy exists!
            if norm_val_1 and norm_val_2 and norm_val_1 != norm_val_2:
                # Canonical pair key to avoid duplicate combinations
                subj_key = min(c1.get('subject', ''), c2.get('subject', ''))
                attr_key = min(c1.get('attribute', ''), c2.get('attribute', ''))
                pair_key = tuple(sorted([
                    f"{src1}_{norm_val_1}",
                    f"{src2}_{norm_val_2}"
                ])) + (subj_key, attr_key)

                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                # Calculate confidence
                conf1 = float(c1.get('confidence', 0.85))
                conf2 = float(c2.get('confidence', 0.85))
                avg_conf = (conf1 + conf2) / 2.0
                conf_pct = f"{int(round(avg_conf * 100))}%"

                # Assign severity dynamically
                attr_lower = str(c1.get('attribute', '')).lower()
                subj_lower = str(c1.get('subject', '')).lower()
                if 'deadline' in attr_lower or 'date' in attr_lower or 'cutoff' in attr_lower:
                    severity = "High"
                elif 'venue' in attr_lower or 'room' in attr_lower or 'location' in attr_lower:
                    severity = "Medium"
                else:
                    severity = "Low"

                # Generate clear conflict reason
                reason = (
                    f"Contradictory values asserted for '{c1.get('subject')}' ({c1.get('attribute')}): "
                    f"'{c1.get('value')}' in {src1} vs '{c2.get('value')}' in {src2}."
                )

                conflicts.append({
                    "claim_id_1": c1.get('id'),
                    "claim_id_2": c2.get('id'),
                    "subject": c1.get('subject', 'Milestone Entity'),
                    "attribute": c1.get('attribute', 'Target Value'),
                    "topic": f"{c1.get('subject')} {c1.get('attribute')}",
                    "category": c1.get('subject'),
                    "sourceA": {
                        "name": src1,
                        "label": "Source A",
                        "claim": c1.get('value'),
                        "origin": f"Extracted from {src1}"
                    },
                    "sourceB": {
                        "name": src2,
                        "label": "Source B",
                        "claim": c2.get('value'),
                        "origin": f"Extracted from {src2}"
                    },
                    "reason": reason,
                    "confidence": conf_pct,
                    "status": "Conflict Detected",
                    "discrepancy": f"{c1.get('value')} vs {c2.get('value')}",
                    "severity": severity
                })

    return conflicts
