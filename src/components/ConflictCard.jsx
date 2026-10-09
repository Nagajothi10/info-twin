import React, { useState, useEffect } from 'react';

export default function ConflictCard({ 
  conflicts = [], 
  onViewEvidence,
  onResolveConflict,
  onDetectConflicts,
  isDetecting = false
}) {
  const [activeConflictId, setActiveConflictId] = useState(conflicts[0]?.id || null);

  useEffect(() => {
    if (conflicts.length > 0) {
      if (!activeConflictId || !conflicts.some(c => String(c.id) === String(activeConflictId))) {
        setActiveConflictId(conflicts[0].id);
      }
    } else {
      setActiveConflictId(null);
    }
  }, [conflicts, activeConflictId]);

  if (conflicts.length === 0) {
    return (
      <div className="conflicts-container">
        <div className="section-header-row">
          <div>
            <div className="section-eyebrow">AUTOMATED CROSS-VERIFICATION ENGINE</div>
            <h2 className="section-title">Conflict Detection</h2>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button 
              className={`btn-primary ${isDetecting ? 'analyzing' : ''}`}
              onClick={onDetectConflicts}
              disabled={isDetecting}
            >
              {isDetecting ? (
                <>
                  <span className="spinner-icon"></span>
                  <span>Comparing Claims...</span>
                </>
              ) : (
                <>
                  <span>⚡</span>
                  <span>Detect Conflicts</span>
                </>
              )}
            </button>

            <div className="conflict-badge-counter" style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#10b981', borderColor: 'rgba(16, 185, 129, 0.3)' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981', display: 'inline-block' }}></span>
              <span>0 Conflicts Flagged</span>
            </div>
          </div>
        </div>

        <div className="empty-state-card" style={{ padding: '52px 24px', textAlign: 'center', background: 'var(--card-bg, #1e293b)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)', margin: '16px 0' }}>
          <div style={{ fontSize: '3rem', marginBottom: '14px' }}>✓</div>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc', marginBottom: '8px' }}>
            Zero Claim Conflicts Flagged
          </h3>
          <p style={{ color: '#94a3b8', maxWidth: '520px', margin: '0 auto 20px', lineHeight: 1.5, fontSize: '0.88rem' }}>
            All extracted document claims and entity attributes are consistent. No contradictory deadlines, venues, or policy buffers exist in the active corpus.
          </p>
          <button 
            className={`btn-primary ${isDetecting ? 'analyzing' : ''}`}
            onClick={onDetectConflicts}
            disabled={isDetecting}
          >
            <span>⚡</span>
            <span>{isDetecting ? 'Running Cross-Verification...' : 'Run Conflict Scan'}</span>
          </button>
        </div>
      </div>
    );
  }

  const currentConflict = conflicts.find(c => String(c.id) === String(activeConflictId)) || conflicts[0];

  return (
    <div className="conflicts-container">
      <div className="section-header-row">
        <div>
          <div className="section-eyebrow">AUTOMATED CROSS-VERIFICATION ENGINE</div>
          <h2 className="section-title">Conflict Detection</h2>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Detect Conflicts Button */}
          <button 
            className={`btn-primary ${isDetecting ? 'analyzing' : ''}`}
            onClick={onDetectConflicts}
            disabled={isDetecting}
          >
            {isDetecting ? (
              <>
                <span className="spinner-icon"></span>
                <span>Comparing Claims...</span>
              </>
            ) : (
              <>
                <span>⚡</span>
                <span>Detect Conflicts</span>
              </>
            )}
          </button>

          <div className="conflict-badge-counter">
            <span className="dot-pulse-danger"></span>
            <span>{conflicts.length} Conflict{conflicts.length !== 1 ? 's' : ''} Flagged</span>
          </div>
        </div>
      </div>

      {/* Pipeline flow indicator: Claims -> Compare -> Detect Conflict -> Display Result */}
      <div className="claims-pipeline-banner" style={{ marginBottom: '16px' }}>
        <div className="pipeline-flow-pills">
          <span className="flow-pill active">Claims</span>
          <span className="flow-arrow">→</span>
          <span className="flow-pill active">Compare</span>
          <span className="flow-arrow">→</span>
          <span className={`flow-pill ${isDetecting ? 'active' : ''}`}>Detect Conflict</span>
          <span className="flow-arrow">→</span>
          <span className="flow-pill active">Display Result</span>
        </div>
        <span className="text-muted text-mono" style={{ fontSize: '0.75rem' }}>
          Rule-Based Value Matching Active
        </span>
      </div>

      {/* Selector pills for multiple detected conflicts */}
      <div className="conflict-tabs-selector">
        {conflicts.map((c) => (
          <button
            key={c.id}
            className={`conflict-tab-btn ${String(c.id) === String(activeConflictId) ? 'active' : ''}`}
            onClick={() => setActiveConflictId(c.id)}
          >
            <span className="tab-alert-icon">⚠️</span>
            <span className="tab-topic">{c.subject || c.topic || 'Discrepancy'}: {c.attribute || ''}</span>
            <span className="tab-confidence">{c.confidence}</span>
          </button>
        ))}
      </div>

      {/* Featured Conflict Card */}
      {currentConflict && (
        <div className="primary-conflict-card">
          <div className="p-conflict-header">
            <div className="topic-meta">
              <span className="topic-category-badge">{currentConflict.subject || currentConflict.category || 'Milestone Timeline'}</span>
              <h3 className="conflict-topic-title">
                {currentConflict.subject} — <span style={{ color: 'var(--cyan)' }}>{currentConflict.attribute}</span>
              </h3>
            </div>
            <div className="conflict-header-right">
              <div className="status-badge-alert">
                <span className="status-indicator-dot"></span>
                <span>Status: {currentConflict.status || 'Conflict Detected'}</span>
              </div>
              <div className="confidence-pill">
                <span className="conf-label">Confidence:</span>
                <span className="conf-val">{currentConflict.confidence}</span>
              </div>
            </div>
          </div>

          {/* Source comparison visual battle */}
          <div className="conflict-comparison-grid">
            {/* Source A Card */}
            <div className="source-card source-a">
              <div className="source-card-badge">
                <span className="source-tag">{currentConflict.sourceA?.label || 'Source A'}</span>
                <span className="source-file text-mono">{currentConflict.sourceA?.name}</span>
              </div>
              <div className="source-origin-text">{currentConflict.sourceA?.origin || `From ${currentConflict.sourceA?.name}`}</div>
              <div className="source-claim-box">
                <div className="claim-label">Value from Source A:</div>
                <div className="claim-highlight highlight-a">{currentConflict.sourceA?.claim}</div>
              </div>
              <div className="source-footer-meta">
                <span>Authority: Canonical Source</span>
                <span>Verified Anchor</span>
              </div>
            </div>

            {/* Versus Icon */}
            <div className="conflict-versus-divider">
              <div className="versus-circle">VS</div>
              <div className="discrepancy-indicator">
                <span>{currentConflict.discrepancy || 'Contradictory Values'}</span>
              </div>
            </div>

            {/* Source B Card */}
            <div className="source-card source-b">
              <div className="source-card-badge">
                <span className="source-tag">{currentConflict.sourceB?.label || 'Source B'}</span>
                <span className="source-file text-mono">{currentConflict.sourceB?.name}</span>
              </div>
              <div className="source-origin-text">{currentConflict.sourceB?.origin || `From ${currentConflict.sourceB?.name}`}</div>
              <div className="source-claim-box">
                <div className="claim-label">Value from Source B:</div>
                <div className="claim-highlight highlight-b">{currentConflict.sourceB?.claim}</div>
              </div>
              <div className="source-footer-meta">
                <span>Authority: Operational Source</span>
                <span>Alternate Anchor</span>
              </div>
            </div>
          </div>

          {/* Reason Explanation Box */}
          <div className="why-detected-box" style={{ margin: '16px 0', padding: '14px 18px' }}>
            <div className="why-header" style={{ marginBottom: '6px' }}>
              <span className="why-icon">⚠️</span>
              <h4 className="why-title" style={{ fontSize: '0.88rem' }}>Conflict Reason & Analysis</h4>
            </div>
            <p className="why-summary-text" style={{ fontSize: '0.82rem', marginBottom: 0 }}>
              {currentConflict.reason || `Values for '${currentConflict.subject}' (${currentConflict.attribute}) differ between ${currentConflict.sourceA?.name} and ${currentConflict.sourceB?.name}. Both sources remain displayed without automated dismissal.`}
            </p>
          </div>

          {/* Confidence Meter */}
          <div className="confidence-meter-container">
            <div className="confidence-labels">
              <span>Machine Intelligence Detection Certainty</span>
              <span className="text-mono font-bold text-cyan">{currentConflict.confidence} Certainty</span>
            </div>
            <div className="confidence-bar-track">
              <div 
                className="confidence-bar-fill" 
                style={{ width: currentConflict.confidence }}
              ></div>
            </div>
          </div>

          {/* Action Toolbar */}
          <div className="conflict-card-actions">
            <div className="conflict-tip-text">
              <span>💡 Cross-referenced entity values: <strong>{currentConflict.sourceA?.claim}</strong> vs <strong>{currentConflict.sourceB?.claim}</strong>.</span>
            </div>
            <div className="action-buttons-wrap">
              <button 
                className="btn-secondary"
                style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '8px 16px', fontWeight: '700' }}
                onClick={() => onViewEvidence && onViewEvidence(currentConflict)}
                title="Explain why this conflict was flagged"
              >
                <span>❓</span>
                <span>Why?</span>
              </button>
              <button 
                className="btn-evidence"
                onClick={() => onViewEvidence && onViewEvidence(currentConflict)}
                title="View full evidence dossier and explainability breakdown"
              >
                <span>🔍</span>
                <span>Why? / View Evidence</span>
              </button>
              <button 
                className="btn-resolve"
                onClick={() => onResolveConflict && onResolveConflict(currentConflict)}
              >
                <span>⚡</span>
                <span>Resolve in Simulator</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
