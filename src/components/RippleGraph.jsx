import React, { useState, useEffect } from 'react';

export default function RippleGraph({ 
  conflict, 
  onNavigateToSimulator 
}) {
  const [analyzingImpact, setAnalyzingImpact] = useState(false);
  const [hasAnalyzed, setHasAnalyzed] = useState(false);
  const [activeNode, setActiveNode] = useState(null);
  const [impactData, setImpactData] = useState(null);

  // Fetch live impact analysis from POST /api/analyze-impact
  const fetchImpactAnalysis = (targetConflict = conflict) => {
    setAnalyzingImpact(true);
    const body = targetConflict?.id ? { conflict_id: targetConflict.id } : {};

    fetch('http://localhost:5000/api/analyze-impact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
      .then((res) => {
        if (!res.ok) throw new Error('Impact analysis API failed');
        return res.json();
      })
      .then((data) => {
        if (data && data.has_impact !== false && data.nodes && data.nodes.length > 0) {
          const formattedNodes = (data.nodes || []).map((n) => ({
            ...n,
            statusType: n.status_type || n.statusType || 'warning',
            impactLevel: n.impact_level ? `${n.impact_level} Impact` : 'High Impact',
            icon: n.id === 'deadline' || n.name?.includes('DEADLINE') ? '⏰' : 
                  n.id === 'submission' || n.name?.includes('SUBMISSION') ? '📤' : 
                  n.id === 'faculty_review' || n.name?.includes('REVIEW') ? '📝' : 
                  n.id === 'evaluation' || n.name?.includes('EVALUATION') ? '📊' : 
                  n.id?.includes('venue') ? '📍' : '🎓'
          }));

          setImpactData({
            has_impact: true,
            trigger: data.trigger || 'Milestone Change',
            old_value: data.old_value || 'Baseline',
            new_value: data.new_value || 'Revision',
            impact_level: data.impact_level || 'High',
            affected: data.affected || [],
            recommended_attention: data.recommended_attention || "Review buffer and notification rosters.",
            nodes: formattedNodes
          });
          setActiveNode(formattedNodes[0]);
          setHasAnalyzed(true);
        } else {
          setImpactData({
            has_impact: false,
            trigger: null,
            nodes: [],
            affected: [],
            recommended_attention: data?.recommended_attention || "No active discrepancies detected across documents."
          });
          setActiveNode(null);
          setHasAnalyzed(true);
        }
      })
      .catch((err) => {
        console.warn('Live impact analysis fetch notice:', err);
        setImpactData(null);
      })
      .finally(() => {
        setAnalyzingImpact(false);
      });
  };

  useEffect(() => {
    fetchImpactAnalysis(conflict);
  }, [conflict]);

  if (!impactData || !impactData.has_impact || !impactData.nodes || impactData.nodes.length === 0) {
    return (
      <div className="ripple-container">
        <div className="section-header-row">
          <div>
            <div className="section-eyebrow">STEP 8 — INFORMATION RIPPLE & DOWNSTREAM IMPACT</div>
            <h2 className="section-title">Downstream Schedule & Process Impact</h2>
          </div>
          <button 
            className={`btn-primary ${analyzingImpact ? 'analyzing' : ''}`}
            onClick={() => fetchImpactAnalysis(conflict)}
            disabled={analyzingImpact}
          >
            {analyzingImpact ? 'Recalculating...' : 'Refresh Impact Scan'}
          </button>
        </div>

        <div className="empty-state-card" style={{ padding: '52px 24px', textAlign: 'center', background: 'var(--card-bg, #1e293b)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)', margin: '16px 0' }}>
          <div style={{ fontSize: '3rem', marginBottom: '14px' }}>⛓️</div>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc', marginBottom: '8px' }}>
            No Active Downstream Ripple Impacts Detected
          </h3>
          <p style={{ color: '#94a3b8', maxWidth: '520px', margin: '0 auto', lineHeight: 1.5, fontSize: '0.88rem' }}>
            All milestone chains are synchronized. When an upstream deadline contradiction or venue reallocation is detected, the automated cascading ripple will be modeled here.
          </p>
        </div>
      </div>
    );
  }

  const currentNodes = impactData.nodes;

  return (
    <div className="ripple-container">
      {/* 1. Header & Quick Actions */}
      <div className="section-header-row">
        <div>
          <div className="section-eyebrow">STEP 8 — INFORMATION RIPPLE & DOWNSTREAM IMPACT</div>
          <h2 className="section-title">Downstream Schedule & Process Impact</h2>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button 
            className={`btn-primary ${analyzingImpact ? 'analyzing' : ''}`}
            onClick={() => fetchImpactAnalysis(conflict)}
            disabled={analyzingImpact}
          >
            {analyzingImpact ? (
              <>
                <span className="spinner-icon"></span>
                <span>Propagating Ripple...</span>
              </>
            ) : (
              <>
                <span>🔄</span>
                <span>Recalculate Ripple</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* 2. Primary Impact Summary Card */}
      <div className="impact-summary-card">
        <div className="impact-summary-top">
          <div className="impact-indicator-badge">
            <span className="dot-pulse-danger"></span>
            <span>Trigger: {impactData.trigger}</span>
          </div>
          <div className="impact-level-pill">
            <span className="pill-lbl">Severity:</span>
            <span className={`pill-val sev-${(impactData.impact_level || 'high').toLowerCase()}`}>
              {impactData.impact_level} Impact
            </span>
          </div>
        </div>

        <div className="impact-meta-grid">
          <div className="impact-meta-item">
            <span className="impact-meta-key">Trigger Entity</span>
            <span className="impact-meta-val">{impactData.trigger}</span>
          </div>
          <div className="impact-meta-item">
            <span className="impact-meta-key">Old Value</span>
            <span className="impact-meta-val" style={{ color: '#fca5a5' }}>{impactData.old_value}</span>
          </div>
          <div className="impact-meta-item">
            <span className="impact-meta-key">New Value</span>
            <span className="impact-meta-val" style={{ color: '#86efac' }}>{impactData.new_value}</span>
          </div>
          <div className="impact-meta-item">
            <span className="impact-meta-key">Propagation Reach</span>
            <span className="impact-meta-val text-cyan">{impactData.affected?.length || currentNodes.length} Downstream Stages</span>
          </div>
        </div>

        {/* Affected Items List */}
        <div style={{ marginBottom: '8px' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 800, textTransform: 'uppercase', color: '#94a3b8' }}>
            Affected Items ({impactData.affected?.length || currentNodes.length}):
          </span>
        </div>
        <div className="affected-tags-container">
          {(impactData.affected || []).map((item, idx) => (
            <div key={idx} className="affected-tag-item">
              <span className="affected-tag-dot"></span>
              <span>{item}</span>
            </div>
          ))}
        </div>

        {/* Recommended Attention Callout */}
        <div className="recommended-attention-callout">
          <span style={{ fontSize: '1.3rem' }}>💡</span>
          <div>
            <strong>Recommended Attention:</strong> {impactData.recommended_attention}
          </div>
        </div>
      </div>

      <div className="ripple-card">
        <div className="ripple-info-banner">
          <div className="banner-text">
            <strong>Cascading Dependency Chain:</strong> When an upstream document changes the <strong>{impactData.trigger}</strong>, the shift ripples forward into downstream milestones.
          </div>
          {onNavigateToSimulator && (
            <button className="btn-ghost btn-sm" onClick={onNavigateToSimulator}>
              🔮 Open What-If Simulator →
            </button>
          )}
        </div>

        {/* 4. VISUAL FLOW (Highlighting affected nodes) */}
        <div className={`ripple-flow-track ${analyzingImpact ? 'pulsing-flow' : ''}`}>
          {currentNodes.map((node, index) => {
            const isLast = index === currentNodes.length - 1;
            const isSelected = activeNode?.id === node.id;
            return (
              <React.Fragment key={node.id || index}>
                {/* Node Box */}
                <div 
                  className={`ripple-node node-${node.statusType} ${isSelected ? 'node-selected' : ''} ${hasAnalyzed ? 'analyzed' : ''}`}
                  onClick={() => setActiveNode(node)}
                  title={`Click to view details for ${node.name}`}
                >
                  <div className="node-step-badge">0{node.step}</div>
                  <div className="node-icon-wrap">{node.icon}</div>
                  <div className="node-name" style={{ fontSize: '0.82rem', letterSpacing: '0.04em' }}>{node.name}</div>
                  <div className="node-date">{node.date}</div>
                  
                  <div className={`node-impact-tag tag-${node.statusType}`}>
                    {node.status}
                  </div>

                  <div className="node-delay-pill">
                    {node.delay}
                  </div>
                </div>

                {/* Arrow connector */}
                {!isLast && (
                  <div className={`ripple-arrow-wrap ${analyzingImpact ? 'arrow-active' : ''}`}>
                    <div className="ripple-line">
                      <div className="ripple-pulse-bullet"></div>
                    </div>
                    <span className="arrow-glyph">→</span>
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* 5. VERTICAL VISUAL CASCADE */}
        <div className="vertical-visual-cascade">
          <div className="cascade-header">
            <h4 style={{ fontSize: '0.95rem', fontWeight: 800, color: '#fff', margin: 0 }}>
              ⛓️ Complete Sequential Dependency Cascade
            </h4>
            <span className="text-muted" style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
              Highlighting {currentNodes.length} Interconnected Stages
            </span>
          </div>

          <div className="cascade-steps-list">
            {currentNodes.map((node, idx) => {
              const isLast = idx === currentNodes.length - 1;
              return (
                <React.Fragment key={node.id || idx}>
                  <div 
                    className={`cascade-node-row ${node.isTrigger ? 'is-trigger' : 'is-affected'}`}
                    onClick={() => setActiveNode(node)}
                  >
                    <div className="cascade-node-left">
                      <span className="cascade-step-num">STAGE 0{node.step}</span>
                      <span style={{ fontSize: '1.2rem' }}>{node.icon}</span>
                      <div>
                        <div className="cascade-node-title">{node.name}</div>
                        <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{node.detail}</div>
                      </div>
                    </div>

                    <div style={{ textAlign: 'right' }}>
                      <div className={`tag-${node.statusType}`} style={{ display: 'inline-block', fontSize: '0.7rem', padding: '2px 8px', borderRadius: '4px', fontWeight: 800 }}>
                        {node.status}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: '#cbd5e1', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                        {node.date} ({node.delay})
                      </div>
                    </div>
                  </div>

                  {!isLast && (
                    <div className="cascade-connector-arrow">
                      <span>↓</span>
                    </div>
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>

        {/* 6. Selected / Active Node Detailed Impact Breakdown */}
        <div className="ripple-breakdown-section">
          <h4 className="breakdown-heading">Downstream Impact Breakdown</h4>
          <div className="breakdown-grid">
            {currentNodes.map((node, index) => (
              <div 
                key={node.id || index} 
                className={`breakdown-card ${activeNode?.id === node.id ? 'active' : ''}`}
                onClick={() => setActiveNode(node)}
              >
                <div className="bd-card-top">
                  <span className="bd-node-icon">{node.icon}</span>
                  <div className="bd-node-title-group">
                    <span className="bd-node-name">{node.name}</span>
                    <span className="bd-node-date text-mono">{node.date}</span>
                  </div>
                  <span className={`bd-status-chip chip-${node.statusType}`}>
                    {node.status}
                  </span>
                </div>
                <p className="bd-detail-text">{node.detail}</p>
                <div className="bd-footer">
                  <span className="bd-risk-level">Impact: {node.impactLevel}</span>
                  <span className="bd-delay-metric text-mono">{node.delay}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
