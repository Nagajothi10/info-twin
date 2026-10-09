import React, { useState, useEffect } from 'react';

export default function EvidencePanel({ 
  conflict, 
  allConflicts = [],
  onSelectConflict,
  onSimulateImpact 
}) {
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(false);
  const [activeConflictId, setActiveConflictId] = useState(conflict?.id || allConflicts[0]?.id || null);
  const [evidenceData, setEvidenceData] = useState(null);

  // Sync activeConflictId when conflict prop or allConflicts changes
  useEffect(() => {
    if (conflict?.id) {
      setActiveConflictId(conflict.id);
    } else if (allConflicts.length > 0 && (!activeConflictId || !allConflicts.some(c => String(c.id) === String(activeConflictId)))) {
      setActiveConflictId(allConflicts[0].id);
    } else if (allConflicts.length === 0) {
      setActiveConflictId(null);
      setEvidenceData(null);
    }
  }, [conflict, allConflicts]);

  // Fetch real evidence from GET /api/conflicts/<id>/evidence
  useEffect(() => {
    if (!activeConflictId) {
      setEvidenceData(null);
      return;
    }

    let isMounted = true;
    setLoading(true);

    fetch(`http://localhost:5000/api/conflicts/${activeConflictId}/evidence`)
      .then((res) => {
        if (!res.ok) throw new Error(`Evidence API returned status ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (isMounted) {
          setEvidenceData(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        console.warn('Backend evidence fetch notice:', err);
        if (isMounted) {
          // Fall back only to the real conflict item in allConflicts if present
          const found = allConflicts.find(c => String(c.id) === String(activeConflictId));
          if (found) {
            setEvidenceData({
              id: found.id,
              subject: found.subject,
              attribute: found.attribute,
              topic: found.topic || `${found.subject} ${found.attribute}`,
              confidence: found.confidence || '94%',
              status: found.status || 'Conflict Detected',
              explanation: found.reason || 'These two claims refer to the same subject and attribute but contain different values.',
              why_flagged: {
                title: 'WHY WAS THIS FLAGGED?',
                topic: `${found.subject} ${found.attribute}`,
                subject: found.subject,
                attribute: found.attribute,
                source_a_doc: found.sourceA?.name,
                source_a_claim: found.sourceA?.claim,
                source_a_quote: found.sourceA?.claim,
                source_b_doc: found.sourceB?.name,
                source_b_claim: found.sourceB?.claim,
                source_b_quote: found.sourceB?.claim,
                why: `Both refer to ${found.subject} → ${found.attribute}, but the values are different.`,
                explanation: found.reason,
                confidence: found.confidence,
                status: 'Conflict Detected'
              },
              comparison: {
                subject: found.subject,
                attribute: found.attribute,
                value_a: found.sourceA?.claim,
                value_b: found.sourceB?.claim
              },
              sourceA: {
                document_name: found.sourceA?.name,
                name: found.sourceA?.name,
                label: 'Source A',
                claim: found.sourceA?.claim,
                value: found.sourceA?.claim,
                original_text: found.sourceA?.claim,
                date: 'Ingested',
                upload_date: 'Ingested',
                confidence: found.confidence,
                source_name: found.sourceA?.name
              },
              sourceB: {
                document_name: found.sourceB?.name,
                name: found.sourceB?.name,
                label: 'Source B',
                claim: found.sourceB?.claim,
                value: found.sourceB?.claim,
                original_text: found.sourceB?.claim,
                date: 'Ingested',
                upload_date: 'Ingested',
                confidence: found.confidence,
                source_name: found.sourceB?.name
              }
            });
          } else {
            setEvidenceData(null);
          }
          setLoading(false);
        }
      });

    return () => { isMounted = false; };
  }, [activeConflictId, allConflicts]);

  const handleCopyEvidence = () => {
    if (!evidenceData) return;
    const textToCopy = `INFO-TWIN Conflict Evidence Dossier #${evidenceData.id}
Subject: ${evidenceData.subject} (${evidenceData.attribute})
Source A (${evidenceData.sourceA?.document_name}): ${evidenceData.sourceA?.claim}
Source B (${evidenceData.sourceB?.document_name}): ${evidenceData.sourceB?.claim}
Confidence: ${evidenceData.confidence}
Explanation: ${evidenceData.explanation}`;

    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!evidenceData && allConflicts.length === 0) {
    return (
      <div className="evidence-container">
        <div className="section-header-row">
          <div>
            <div className="section-eyebrow">STEP 6 — EVIDENCE & EXPLAINABILITY</div>
            <h2 className="section-title">Evidence & Why Was It Flagged?</h2>
          </div>
        </div>
        <div className="empty-state-card" style={{ padding: '52px 24px', textAlign: 'center', background: 'var(--card-bg, #1e293b)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)', margin: '16px 0' }}>
          <div style={{ fontSize: '3rem', marginBottom: '14px' }}>📋</div>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc', marginBottom: '8px' }}>
            No Active Conflict Evidence Dossier
          </h3>
          <p style={{ color: '#94a3b8', maxWidth: '520px', margin: '0 auto', lineHeight: 1.5, fontSize: '0.88rem' }}>
            Evidence dossiers and side-by-side textual comparisons are generated when contradictory assertions are detected. There are currently zero conflicting claims in the workspace.
          </p>
        </div>
      </div>
    );
  }

  const displayData = evidenceData || {};
  const why = displayData.why_flagged || {};
  const comparison = displayData.comparison || {
    subject: displayData.subject,
    attribute: displayData.attribute,
    value_a: displayData.sourceA?.claim,
    value_b: displayData.sourceB?.claim
  };
  const sourceA = displayData.sourceA || {};
  const sourceB = displayData.sourceB || {};

  return (
    <div className="evidence-container">
      {/* Header */}
      <div className="section-header-row">
        <div>
          <div className="section-eyebrow">STEP 6 — EVIDENCE & EXPLAINABILITY</div>
          <h2 className="section-title">Evidence & Why Was It Flagged?</h2>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button 
            className="btn-secondary btn-sm"
            onClick={handleCopyEvidence}
            disabled={!evidenceData}
          >
            <span>{copied ? '✓' : '📋'}</span>
            <span>{copied ? 'Copied Dossier!' : 'Copy Evidence'}</span>
          </button>
          {onSimulateImpact && (
            <button 
              className="btn-primary btn-sm"
              onClick={onSimulateImpact}
            >
              <span>⛓️</span>
              <span>View Downstream Ripple</span>
            </button>
          )}
        </div>
      </div>

      {/* Conflict Selector Pills (if multiple conflicts exist) */}
      {allConflicts.length > 1 && (
        <div className="conflict-tabs-selector" style={{ marginBottom: '16px' }}>
          {allConflicts.map((c) => (
            <button
              key={c.id}
              className={`conflict-tab-btn ${String(c.id) === String(activeConflictId) ? 'active' : ''}`}
              onClick={() => {
                setActiveConflictId(c.id);
                if (onSelectConflict) onSelectConflict(c);
              }}
            >
              <span>⚠️</span>
              <span className="tab-topic">{c.subject || c.topic}: {c.attribute}</span>
              <span className="tab-confidence">{c.confidence}</span>
            </button>
          ))}
        </div>
      )}

      {loading && (
        <div style={{ padding: '12px 16px', color: 'var(--cyan)', fontSize: '0.85rem' }}>
          ⏳ Fetching live evidence from backend database...
        </div>
      )}

      {/* 1. WHY WAS THIS FLAGGED? Primary Card */}
      <div className="why-flagged-card">
        <div className="why-flagged-header">
          <div className="why-title-group">
            <span className="why-icon-badge">❓</span>
            <div>
              <span className="why-eyebrow">EXPLAINABILITY DOSSIER #{displayData.id || activeConflictId}</span>
              <h3 className="why-main-title">{why.title || 'WHY WAS THIS FLAGGED?'}</h3>
            </div>
          </div>
          <div className="why-header-tags">
            <span className="badge-alert-pill">
              <span className="dot-pulse-danger"></span>
              <span>Status: {displayData.status || 'Conflict Detected'}</span>
            </span>
            {displayData.confidence && (
              <span className="badge-confidence">
                Confidence: {displayData.confidence}
              </span>
            )}
          </div>
        </div>

        {/* WHY? Callout */}
        <div className="why-explanation-callout">
          <div className="why-callout-header">
            <span className="why-badge">WHY?</span>
            <span className="why-callout-rule">
              Both refer to <strong>{displayData.subject} → {displayData.attribute}</strong>, but the values are different.
            </span>
          </div>
          <p className="why-callout-body">
            "{displayData.explanation || 'These two claims refer to the same subject and attribute but contain different values.'}"
          </p>
          <div className="why-callout-footer">
            <div className="why-confidence-box">
              <span className="why-conf-label">Confidence:</span>
              <span className="why-conf-value">{displayData.confidence || '94%'}</span>
            </div>
            <div className="why-neutrality-tag">
              ⚖️ Unresolved Conflict • Both sources preserved neutrally
            </div>
          </div>
        </div>
      </div>

      {/* 2. REQUIRED COMPARISON MATRIX */}
      <div className="comparison-matrix-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <h4 style={{ fontSize: '0.95rem', fontWeight: '700', color: '#fff', margin: 0 }}>
            ⚖️ Claim Comparison Matrix
          </h4>
          <span className="badge-comparison">Subject & Attribute Alignment</span>
        </div>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '14px' }}>
          Exact entity comparison highlighting the discrepancy between both authoritative records:
        </p>
        <div className="comparison-table-wrap">
          <table className="comparison-table">
            <thead>
              <tr>
                <th>Subject</th>
                <th>Attribute</th>
                <th>Value A ({sourceA.document_name || sourceA.name})</th>
                <th>Value B ({sourceB.document_name || sourceB.name})</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style={{ fontWeight: '700', color: '#f8fafc' }}>
                  {comparison.subject}
                </td>
                <td style={{ color: 'var(--cyan)', fontWeight: '700' }}>
                  {comparison.attribute}
                </td>
                <td className="highlight-cell-a">
                  {comparison.value_a}
                </td>
                <td className="highlight-cell-b">
                  {comparison.value_b}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* 3. SOURCE INFORMATION CARDS */}
      <div className="evidence-quotes-grid" style={{ marginBottom: '24px' }}>
        {/* Source A Information */}
        <div className="statement-box statement-a">
          <div className="statement-header">
            <div className="statement-source-tag">
              <span className="tag-source">SOURCE A INFORMATION</span>
              <span className="tag-file text-mono">{sourceA.document_name || sourceA.name}</span>
            </div>
            <span className="tag-section">Authority: Primary Ingested</span>
          </div>

          <div style={{ marginBottom: '12px', fontSize: '0.82rem', color: '#94a3b8' }}>
            Original Extracted Text:
          </div>
          <blockquote className="statement-quote">
            "{sourceA.original_text || sourceA.claim}"
          </blockquote>

          <div className="statement-meta-footer">
            <div className="meta-row">
              <span className="meta-label">📄 Document / Source Name:</span>
              <span className="meta-value text-mono">{sourceA.source_name || sourceA.document_name}</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">📅 Upload / Publication Date:</span>
              <span className="meta-value">{sourceA.upload_date || sourceA.date || 'Available'}</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">🎯 Claim Confidence:</span>
              <span className="meta-value highlight-text-a">{sourceA.claim_confidence || sourceA.confidence || '94%'}</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">📌 Extracted Value:</span>
              <span className="meta-value highlight-text-a">{sourceA.claim || sourceA.value}</span>
            </div>
          </div>
        </div>

        {/* Source B Information */}
        <div className="statement-box statement-b">
          <div className="statement-header">
            <div className="statement-source-tag">
              <span className="tag-source">SOURCE B INFORMATION</span>
              <span className="tag-file text-mono">{sourceB.document_name || sourceB.name}</span>
            </div>
            <span className="tag-section">Authority: Alternate Ingested</span>
          </div>

          <div style={{ marginBottom: '12px', fontSize: '0.82rem', color: '#94a3b8' }}>
            Original Extracted Text:
          </div>
          <blockquote className="statement-quote">
            "{sourceB.original_text || sourceB.claim}"
          </blockquote>

          <div className="statement-meta-footer">
            <div className="meta-row">
              <span className="meta-label">📄 Document / Source Name:</span>
              <span className="meta-value text-mono">{sourceB.source_name || sourceB.document_name}</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">📅 Upload / Publication Date:</span>
              <span className="meta-value">{sourceB.upload_date || sourceB.date || 'Available'}</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">🎯 Claim Confidence:</span>
              <span className="meta-value highlight-text-b">{sourceB.claim_confidence || sourceB.confidence || '94%'}</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">📌 Extracted Value:</span>
              <span className="meta-value highlight-text-b">{sourceB.claim || sourceB.value}</span>
            </div>
          </div>
        </div>
      </div>

      {/* 4. IMPARTIALITY GUARANTEE BANNER */}
      <div className="impartiality-guarantee-banner">
        <span className="impartiality-icon">⚖️</span>
        <div className="impartiality-text">
          <strong>Impartiality Protocol:</strong> INFO-TWIN does NOT automatically declare either source as correct. 
          Both claims represent authentic assertions extracted from system documents. Reconcile this discrepancy using the 
          <strong> What-If Simulator</strong> or publish an administrative circular to establish a canonical ground truth.
        </div>
      </div>

      {/* Provenance Hierarchy Breakdown */}
      <div className="provenance-summary">
        <div className="prov-item">
          <span className="prov-title">Entity Comparison</span>
          <span className="prov-desc">Subject: <strong>{displayData.subject}</strong> | Attribute: <strong>{displayData.attribute}</strong></span>
        </div>
        <div className="prov-item">
          <span className="prov-title">Discrepancy Severity</span>
          <span className="prov-desc">Value divergence detected between {sourceA.document_name} and {sourceB.document_name}.</span>
        </div>
        <div className="prov-item">
          <span className="prov-title">Explainability Rule</span>
          <span className="prov-desc">Rule-based temporal & attribute anomaly trigger (Confidence: {displayData.confidence}).</span>
        </div>
      </div>
    </div>
  );
}
