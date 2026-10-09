import re

def extract_claims_from_text(text, filename="Document"):
    """
    Rule-based claim extraction engine.
    Extracts structured claims from document text:
    - Deadlines / Dates
    - Names / Authority
    - Amounts / Percentages / Duration
    - Locations / Venues
    - Requirements & Deliverables
    - Submission Methods
    - Important Directives

    Returns list of dicts:
    {
      "subject": "...",
      "attribute": "...",
      "value": "...",
      "source": "...",
      "confidence": 0.0
    }
    """
    claims = []
    if not text:
        return claims

    # Normalize lines
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # 1. DEADLINES & DATES
    # Matches "25 October 2026", "2026-10-25", "10 October 2026 at 23:59 IST", etc.
    date_patterns = [
        r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}(?:\s*(?:at|,)?\s*\d{1,2}:\d{2}(?:\s*[A-Z]+)?)?)',
        r'(\d{4}-\d{2}-\d{2})',
        r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})'
    ]

    for line in lines:
        for pat in date_patterns:
            matches = re.findall(pat, line, re.IGNORECASE)
            for match in matches:
                date_val = match.strip()
                lower_line = line.lower()
                
                # Determine subject and attribute based on context
                if any(k in lower_line for k in ['revised deadline', 'extended to', 'revised to']):
                    subject = "Project Submission"
                    attr = "Revised Deadline"
                    conf = 0.98
                elif any(k in lower_line for k in ['deadline', 'submission', 'portal upload', 'deliverable']):
                    subject = "Project Submission"
                    attr = "Submission Deadline"
                    conf = 0.95
                elif any(k in lower_line for k in ['viva', 'defense', 'oral']):
                    subject = "Viva Defense"
                    attr = "Scheduled Date"
                    conf = 0.92
                elif any(k in lower_line for k in ['review', 'peer review']):
                    subject = "Review Schedule"
                    attr = "Commencement Date"
                    conf = 0.90
                elif any(k in lower_line for k in ['circular ref', 'date:', 'dated']):
                    subject = "Document Governance"
                    attr = "Publication Date"
                    conf = 0.88
                else:
                    subject = "Project Milestones"
                    attr = "Key Date"
                    conf = 0.82

                claims.append({
                    "subject": subject,
                    "attribute": attr,
                    "value": date_val,
                    "source": filename,
                    "confidence": round(conf, 2)
                })

    # 2. NAMES & OFFICIAL AUTHORITIES
    name_patterns = [
        r'(Prof\.\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)',
        r'(Dr\.\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)',
        r'([A-Z][a-zA-Z]+\s+Verma)',
        r'([A-Z][a-zA-Z]+\s+Ramanathan)',
        r'(Dean\s+(?:of\s+)?[A-Z][a-zA-Z\s]+)',
        r'(Office of the Dean[A-Za-z\s,]*)'
    ]
    for line in lines:
        for pat in name_patterns:
            matches = re.findall(pat, line)
            for match in matches:
                name_val = match.strip().rstrip(',')
                if len(name_val) < 4:
                    continue
                claims.append({
                    "subject": "Academic Personnel",
                    "attribute": "Issuing Official / Coordinator",
                    "value": name_val,
                    "source": filename,
                    "confidence": 0.92
                })

    # 3. LOCATIONS & VENUES
    venue_patterns = [
        r'(Lab\s+\d+(?:\s+[-A-Za-z0-9\s]+)?)',
        r'(Seminar\s+Hall\s+[A-Z0-9]+)',
        r'(Auditorium\s+[A-Za-z0-9]+)',
        r'(Online\s+Portal)',
        r'(Virtual\s+Panels)'
    ]
    for line in lines:
        for pat in venue_patterns:
            matches = re.findall(pat, line, re.IGNORECASE)
            for match in matches:
                venue_val = match.strip()
                claims.append({
                    "subject": "Event Logistics",
                    "attribute": "Assigned Venue",
                    "value": venue_val,
                    "source": filename,
                    "confidence": 0.91
                })

    # 4. AMOUNTS, PERCENTAGES & TIME BUFFERS
    amount_patterns = [
        r'(\d+%\s*(?:Technical|Report|Implementation|Presentation|Mentor|Review|Defense|Viva)?)',
        r'(\b\d+\s*(?:calendar\s+days|working\s+days|days|hours)\b)'
    ]
    for line in lines:
        for pat in amount_patterns:
            matches = re.findall(pat, line, re.IGNORECASE)
            for match in matches:
                val = match.strip()
                if '%' in val:
                    attr = "Grading Weightage"
                    subj = "Evaluation Rubric"
                elif 'day' in val.lower() or 'hour' in val.lower():
                    attr = "Duration Window"
                    subj = "Policy Buffer"
                else:
                    attr = "Metric Value"
                    subj = "Quantitative Requirement"

                claims.append({
                    "subject": subj,
                    "attribute": attr,
                    "value": val,
                    "source": filename,
                    "confidence": 0.88
                })

    # 5. REQUIREMENTS & SUBMISSION METHODS
    req_patterns = [
        (r'(strict\s+zero-tolerance\s+late\s+policy[^\.\n]*)', "Submission Regulation", "Late Policy", 0.94),
        (r'(mandat(?:ory|es)\s+minimum\s+\d+[- ]day\s+review\s+period[^\.\n]*)', "Academic Policy", "Review Mandate", 0.93),
        (r'(technical\s+source\s+code\s+with\s+reproduction[^\.\n]*)', "Deliverable Specification", "Source Code", 0.90),
        (r'(supervisor\s+clearance[^\.\n]*)', "Eligibility Criteria", "Prerequisite", 0.87),
        (r'(hardware\s+lab\s+availability[^\.\n]*)', "Resource Dependency", "Infrastructure", 0.85)
    ]
    lower_full_text = text.lower()
    for pat, subj, attr, conf in req_patterns:
        m = re.search(pat, lower_full_text, re.IGNORECASE)
        if m:
            claims.append({
                "subject": subj,
                "attribute": attr,
                "value": m.group(1).capitalize().strip(),
                "source": filename,
                "confidence": round(conf, 2)
            })

    # Deduplicate claims while preserving order
    unique_claims = []
    seen = set()
    for c in claims:
        key = (c["subject"].lower(), c["attribute"].lower(), c["value"].lower())
        if key not in seen:
            seen.add(key)
            unique_claims.append(c)

    # If no specific patterns matched, provide a high-level extracted claim from lines
    if not unique_claims and lines:
        unique_claims.append({
            "subject": "Document Summary",
            "attribute": "Content Digest",
            "value": lines[0][:120],
            "source": filename,
            "confidence": 0.75
        })

    return unique_claims
