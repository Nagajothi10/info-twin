import React, { useState, useEffect } from 'react';

export default function ChangesPanel({ onSelectConflict, onUpdateCounts }) {
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(false);
  const [isDetecting, setIsDetecting] = useState(false);
  const [changesList, setChangesList] = useState([]);
  const [missingList, setMissingList] = useState([]);

  // Fetch changes & missing information from backend
  const loadChanges = () => {
    setLoading(true);
    fetch('http://localhost:5000/api/changes')
      .then((res) => {
        if (!res.ok) throw new Error('Failed to load changes');
        return res.json();
      })
      .then((data) => {
        if (data) {
          const loadedChanges = data.changes || [];
          const loadedMissing = data.missing_info || [];
          setChangesList(loadedChanges);
          setMissingList(loadedMissing);
          if (onUpdateCounts) {
            onUpdateCounts({
              changes: data.changes_count ?? loadedChanges.length,
              missing: data.missing_count ?? loadedMissing.length
            });
          }
        }
      })
      .catch((err) => {
        console.warn('Backend changes API notice:', err);
        setChangesList([]);
        setMissingList([]);
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    loadChanges();
  }, []);

  const handleScanForChanges = async () => {
    setIsDetecting(true);
    try {
      const res = await fetch('http://localhost:5000/api/detect-changes', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setChangesList(data.changes || []);
        setMissingList(data.missing_info || []);
        if (onUpdateCounts) {
          onUpdateCounts({
            changes: data.changes_count || 0,
            missing: data.missing_count || 0
          });
        }
      }
    } catch (err) {
      console.warn('Error running detect-changes:', err);
    } finally {
      setIsDetecting(false);
    }
  };

  const filteredChanges = changesList.filter((item) => {
    if (filter === 'conflicts') return item.is_conflict;
    if (filter === 'normal') return !item.is_conflict;
    return true;
  });

  return (
    <div className="changes-container">
      {/* 1. Header & Controls */}
      <div className="section-header-row">
        <div>
          <div className="section-eyebrow">STEP 7 — SEMANTIC AUDIT & REVISIONS</div>
          <h2 className="section-title">
            Corpus Changes & Revisions ({changesList.length})
          </h2>
        </div>
        
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button 
            className={`btn-primary ${isDetecting ? 'analyzing' : ''}`}
            onClick={handleScanForChanges}
            disabled={isDetecting}
          >
            {isDetecting ? 'Scanning Claims...' : '⚡ Scan for Changes'}
          </button>

          {/* Filter Pills */}
          <div className="changes-filter-pills">
            <button 
              className={`filter-pill ${filter === 'all' ? 'active' : ''}`}
              onClick={() => setFilter('all')}
            >
              All ({changesList.length})
            </button>
            <button 
              className={`filter-pill ${filter === 'conflicts' ? 'active' : ''}`}
              onClick={() => setFilter('conflicts')}
            >
              ⚠️ Conflicts ({changesList.filter(c => c.is_conflict).length})
            </button>
            <button 
              className={`filter-pill ${filter === 'normal' ? 'active' : ''}`}
              onClick={() => setFilter('normal')}
            >
              ✓ Reconciled ({changesList.filter(c => !c.is_conflict).length})
            </button>
          </div>
        </div>
      </div>

      {loading && (
        <div style={{ padding: '16px', color: 'var(--cyan)', fontSize: '0.85rem' }}>
          ⏳ Loading detected semantic changes and missing field audit...
        </div>
      )}

      {/* 2. CHANGE DETECTION GRID */}
      {filteredChanges.length === 0 ? (
        <div className="empty-state-card" style={{ padding: '48px 24px', textAlign: 'center', background: 'var(--card-bg, #1e293b)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)', margin: '16px 0' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>✓</div>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#f8fafc', marginBottom: '8px' }}>
            Zero Revisions Flagged
          </h3>
          <p style={{ color: '#94a3b8', maxWidth: '520px', margin: '0 auto', fontSize: '0.85rem', lineHeight: 1.5 }}>
            No semantic discrepancies or date shifts detected across active documents. Upload new versions to track revision histories.
          </p>
        </div>
      ) : (
        <div className="changes-grid">
          {filteredChanges.map((item) => (
            <div key={item.id} className="change-card">
              {/* Header: Change Detected Badge & Type */}
              <div className="change-card-header">
                <span className="change-detected-badge">
                  🔵 CHANGE DETECTED
                </span>
                <span className="change-type-pill">
                  {item.change_type || 'revision'}
                </span>
              </div>

              {/* Title / Changed Information */}
              <h3 className="change-title">
                {item.title || `${item.subject}: ${item.attribute}`}
              </h3>

              {/* Old Value vs New Value Diff */}
              <div className="change-diff-box">
                <div className="diff-item old">
                  <span className="diff-prefix">-</span>
                  <div className="diff-val-wrap">
                    <span className="diff-label-sub">Old Value ({item.old_source || 'Prior Document'})</span>
                    <span className="diff-val font-bold">{item.old_value}</span>
                  </div>
                </div>
                <div className="diff-item new">
                  <span className="diff-prefix">+</span>
                  <div className="diff-val-wrap">
                    <span className="diff-label-sub">New Value ({item.new_source || item.source || 'Latest Document'})</span>
                    <span className="diff-val font-bold">{item.new_value}</span>
                  </div>
                </div>
              </div>

              {/* Changed Meta: Source, Date, Subject */}
              <div className="change-details-meta">
                <div className="change-meta-item">
                  <span className="change-meta-lbl">📄 Source (Latest):</span>
                  <span className="change-meta-val text-mono text-cyan">
                    {item.source || item.new_source}
                  </span>
                </div>
                <div className="change-meta-item">
                  <span className="change-meta-lbl">📅 Date / Timestamp:</span>
                  <span className="change-meta-val">
                    {item.date || item.timestamp || 'Ingested'}
                  </span>
                </div>
                <div className="change-meta-item">
                  <span className="change-meta-lbl">📌 Related Subject:</span>
                  <span className="change-meta-val">
                    {item.subject} → {item.attribute}
                  </span>
                </div>
              </div>

              {/* Footer with Source Delta & Conflict Inspection Link */}
              <div className="change-card-footer">
                <div className="change-source-info">
                  <span className="text-muted" style={{ fontSize: '0.72rem' }}>Delta:</span>
                  <span className="source-path text-mono" style={{ fontSize: '0.72rem' }}>
                    {item.source_delta || `${item.old_source} → ${item.new_source}`}
                  </span>
                </div>
                {item.is_conflict && (
                  <button 
                    className="btn-conflict-link"
                    onClick={() => onSelectConflict && onSelectConflict(item)}
                    title="Cross-reference in Conflict Detection"
                  >
                    Inspect Conflict →
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 3. MISSING INFORMATION SECTION */}
      <div className="missing-section-wrap" style={{ marginTop: '32px' }}>
        <div className="section-header-row" style={{ marginBottom: '18px' }}>
          <div>
            <div className="section-eyebrow">INFORMATION COMPLETENESS AUDIT</div>
            <h2 className="section-title">
              Missing Information ({missingList.length})
            </h2>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="badge-warning font-bold" style={{ fontSize: '0.75rem', padding: '6px 12px', borderRadius: '999px' }}>
              ⚠️ Mandatory Milestone Attributes Audited
            </span>
          </div>
        </div>

        <p style={{ fontSize: '0.84rem', color: 'var(--text-dim)', marginBottom: '22px' }}>
          Identifies documents where core academic milestone parameters (deadline, responsible person, submission method, submission location/link, required documents) are missing or unspecified.
        </p>

        {missingList.length === 0 ? (
          <div className="empty-state-card" style={{ padding: '38px 24px', textAlign: 'center', background: 'var(--card-bg, #1e293b)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)' }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '10px' }}>✓</div>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f8fafc', marginBottom: '6px' }}>
              Complete Documentation
            </h3>
            <p style={{ color: '#94a3b8', maxWidth: '520px', margin: '0 auto', fontSize: '0.85rem' }}>
              All audited mandatory milestone attributes are specified across active documents. No completeness gaps detected.
            </p>
          </div>
        ) : (
          <div className="missing-info-grid">
            {missingList.map((m, idx) => (
              <div key={m.id || idx} className="missing-card">
                {/* Card Top: Missing Info Badge & Severity */}
                <div className="missing-card-top">
                  <span className="missing-badge">
                    🟡 MISSING INFORMATION
                  </span>
                  <span className={`missing-severity-tag sev-${(m.severity || 'medium').toLowerCase()}`}>
                    {m.severity || 'Medium'} Gap
                  </span>
                </div>

                {/* Missing Field Heading */}
                <h3 className="missing-field-heading">
                  Missing Field: <span className="missing-field-title-highlight">{m.missing_field}</span>
                </h3>

                {/* Source Document & Related Subject */}
                <div className="missing-meta-box">
                  <div className="missing-meta-row">
                    <span className="text-muted">Source Document:</span>
                    <span className="text-mono font-bold text-light">📄 {m.source_document}</span>
                  </div>
                  <div className="missing-meta-row">
                    <span className="text-muted">Related Subject:</span>
                    <span className="text-cyan font-bold">{m.related_subject}</span>
                  </div>
                </div>

                {/* Context Display showing present fields vs missing fields */}
                <div className="missing-context-box">
                  <div className="missing-context-line is-present">
                    <span>Deadline:</span>
                    <span>{m.present_context?.deadline || 'Specified'}</span>
                  </div>
                  <div className={`missing-context-line ${m.missing_field === 'Submission Method' || m.present_context?.submission_method === 'Missing' ? 'is-missing' : 'is-present'}`}>
                    <span>Submission method:</span>
                    <span>{m.present_context?.submission_method === 'Missing' ? 'Missing' : (m.missing_field === 'Submission Method' ? 'Missing' : m.present_context?.submission_method || 'Specified')}</span>
                  </div>
                  <div className={`missing-context-line ${m.missing_field === 'Responsible Person' || m.present_context?.responsible_person === 'Missing' ? 'is-missing' : 'is-present'}`}>
                    <span>Responsible person:</span>
                    <span>{m.present_context?.responsible_person === 'Missing' ? 'Missing' : (m.missing_field === 'Responsible Person' ? 'Missing' : m.present_context?.responsible_person || 'Specified')}</span>
                  </div>
                </div>

                {/* Impact / Recommendation */}
                <div className="missing-impact-text">
                  <strong>Impact:</strong> {m.impact || 'Requires administrative confirmation before deliverable submission window opens.'}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
