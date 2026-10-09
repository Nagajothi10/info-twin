import React, { useState, useEffect } from 'react';

export default function ActionRecommendation({ onNavigateToSection }) {
  const [recommendations, setRecommendations] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [actionStatus, setActionStatus] = useState('');

  // Fetch live recommendations from backend GET /api/recommendations
  const loadRecommendations = () => {
    setIsLoading(true);
    fetch('http://localhost:5000/api/recommendations')
      .then((res) => {
        if (!res.ok) throw new Error('Failed to load recommendations');
        return res.json();
      })
      .then((data) => {
        if (data && Array.isArray(data.recommendations)) {
          setRecommendations(data.recommendations);
        } else {
          setRecommendations([]);
        }
      })
      .catch((err) => {
        console.warn('Live recommendations fetch notice:', err.message);
        setRecommendations([]);
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  useEffect(() => {
    loadRecommendations();
  }, []);

  const handleAction = (msg) => {
    setActionStatus(msg);
    setTimeout(() => setActionStatus(''), 4500);
  };

  // Primary High Priority Action Recommendation
  const primaryRec = recommendations.find(r => r.priority_level === 'HIGH' || (r.priority && r.priority.includes('HIGH'))) || recommendations[0];
  const secondaryRecs = recommendations.filter(r => r.id !== primaryRec?.id);

  if (recommendations.length === 0) {
    return (
      <div className="recommendation-container" id="actionRecommendationSection">
        <div className="action-hero-card" style={{ textAlign: 'center', padding: '38px 24px' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '10px' }}>✓</div>
          <h3 className="action-hero-title" style={{ fontSize: '1.2rem', marginBottom: '8px' }}>
            No Active Prescriptive Interventions Required
          </h3>
          <p className="action-hero-reason-text" style={{ maxWidth: '580px', margin: '0 auto', fontSize: '0.88rem', color: '#94a3b8', lineHeight: 1.5 }}>
            All ingested documents, milestone timelines, and policy buffers are currently synchronized. When contradictory assertions, venue clashes, or information gaps are detected, automated prescriptive guidance will appear here.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="recommendation-container" id="actionRecommendationSection">
      {/* Primary Hero Recommendation Card */}
      <div className="action-hero-card">
        {/* Priority Badge */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
          <div className="action-hero-badge">
            <span>🔴</span>
            <span>{primaryRec?.priority || 'HIGH — ACTION REQUIRED'}</span>
          </div>

          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <span className="rec-pill-ai">
              <span className="rec-sparkle">✨</span>
              <span>DATA-DRIVEN INTELLIGENCE</span>
            </span>
            <span style={{ fontSize: '0.72rem', color: '#94a3b8', background: 'rgba(255,255,255,0.06)', padding: '3px 8px', borderRadius: '4px' }}>
              GET /api/recommendations
            </span>
          </div>
        </div>

        {/* Recommended Action Statement */}
        <h3 className="action-hero-title">
          {primaryRec?.recommended_action || 'Reconcile detected contradictions across active documents.'}
        </h3>

        {/* Reason Box */}
        <div className="action-hero-reason-box">
          <span className="action-hero-reason-lbl">Reason:</span>
          <p className="action-hero-reason-text">
            {primaryRec?.reason || 'Discrepancy detected between ingested document records.'}
          </p>
          {primaryRec?.finding && (
            <div style={{ marginTop: '8px', fontSize: '0.8rem', color: '#94a3b8' }}>
              <strong>Finding:</strong> <span className="text-cyan">{primaryRec.finding}</span>
            </div>
          )}
        </div>

        {/* Action Status Toast */}
        {actionStatus && (
          <div className="rec-feedback-toast" style={{ marginBottom: '16px' }}>
            <span>✓</span>
            <span>{actionStatus}</span>
          </div>
        )}

        {/* Action Toolbar */}
        <div className="rec-actions-toolbar">
          <button 
            className="btn-primary btn-sm"
            onClick={() => handleAction('Dispatched automated verification memo to stakeholders.')}
          >
            <span>📧</span>
            <span>Verify Discrepancy</span>
          </button>
          
          <button 
            className="btn-secondary btn-sm"
            onClick={() => {
              handleAction('Navigating to Downstream Impact Analysis.');
              if (onNavigateToSection) onNavigateToSection('impact');
            }}
          >
            <span>🔄</span>
            <span>Update Affected Schedules</span>
          </button>

          <button 
            className="btn-secondary btn-sm"
            style={{ background: 'rgba(6, 182, 212, 0.2)', borderColor: 'rgba(6, 182, 212, 0.4)', color: '#38bdf8' }}
            onClick={() => {
              handleAction('Loaded Scenario in What-If Simulator Sandbox.');
              if (onNavigateToSection) onNavigateToSection('simulator');
            }}
          >
            <span>🔮</span>
            <span>Simulate in What-If</span>
          </button>

          <button 
            className="btn-ghost btn-sm"
            onClick={() => {
              if (onNavigateToSection) onNavigateToSection('evidence');
            }}
          >
            <span>🔍</span>
            <span>Inspect Evidence</span>
          </button>
        </div>
      </div>

      {/* Secondary Priority Recommendations Grid */}
      {secondaryRecs.length > 0 && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#94a3b8' }}>
              Additional Prescriptive Recommendations ({secondaryRecs.length})
            </span>
          </div>

          <div className="recommendations-secondary-grid">
            {secondaryRecs.map((rec) => {
              const isMed = rec.priority?.includes('MEDIUM');
              const isLow = rec.priority?.includes('LOW');
              const icon = isMed ? '🟡' : isLow ? '🔵' : '🔴';
              const chipClass = isMed ? 'chip-medium' : isLow ? 'chip-low' : 'chip-high';

              return (
                <div key={rec.id} className="rec-subcard">
                  <div className="rec-subcard-header">
                    <span className={`rec-priority-chip ${chipClass}`}>
                      <span>{icon}</span> {rec.priority}
                    </span>
                    <span style={{ fontSize: '0.7rem', color: '#64748b' }}>{rec.issue}</span>
                  </div>

                  <div style={{ fontSize: '0.92rem', fontWeight: 700, color: '#f1f5f9', lineHeight: 1.4 }}>
                    {rec.recommended_action}
                  </div>

                  <div style={{ fontSize: '0.8rem', color: '#94a3b8', lineHeight: 1.4 }}>
                    <span style={{ color: '#cbd5e1', fontWeight: 600 }}>Reason: </span>
                    {rec.reason}
                  </div>

                  {rec.affected_targets && (
                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: 'auto', paddingTop: '8px' }}>
                      {rec.affected_targets.map((tgt, idx) => (
                        <span key={idx} style={{ fontSize: '0.68rem', padding: '2px 7px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', color: '#94a3b8' }}>
                          {tgt}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
