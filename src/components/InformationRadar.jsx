import React from 'react';

export default function InformationRadar({ 
  onSelectCategory, 
  conflictsCount = 3,
  changesCount = 5,
  missingCount = 2
}) {
  const radarItems = [
    {
      id: 'temporal',
      title: 'Temporal Consistency',
      status: conflictsCount > 0 ? 'Critical Alert' : 'Consistent',
      type: conflictsCount > 0 ? 'danger' : 'success',
      icon: '⏰',
      score: conflictsCount > 0 ? '62%' : '100%',
      detail: `${conflictsCount} active discrepancy(ies) flagged across ingested claims repository.`,
      metric: `${conflictsCount} Active Conflicts`
    },
    {
      id: 'agreement',
      title: 'Cross-Source Agreement',
      status: 'Moderate Drift',
      type: 'warning',
      icon: '⚖️',
      score: '84%',
      detail: 'Cross-verification engine actively tracking divergent source anchors.',
      metric: `${conflictsCount} Divergences`
    },
    {
      id: 'change',
      title: 'Revision Dynamics',
      status: changesCount > 0 ? 'Active Changes' : 'Stable',
      type: 'info',
      icon: '🔄',
      score: '91%',
      detail: `${changesCount} semantic update(s) tracked across guidelines, schedules, and circulars.`,
      metric: `${changesCount} Updates Tracked`
    },
    {
      id: 'completeness',
      title: 'Information Completeness',
      status: missingCount > 0 ? 'Missing Fields' : 'Complete',
      type: 'warning',
      icon: '🧩',
      score: missingCount > 0 ? `${Math.max(65, 100 - missingCount * 4)}%` : '100%',
      detail: `${missingCount} mandatory field gap(s) flagged across ingested documents.`,
      metric: `${missingCount} Gap Fields`
    },
    {
      id: 'freshness',
      title: 'Document Freshness',
      status: 'Outdated Found',
      type: 'danger',
      icon: '⏳',
      score: '70%',
      detail: 'notice.pdf published 02 Oct superseded by informal email on 04 Oct.',
      metric: '1 Superseded'
    },
    {
      id: 'compliance',
      title: 'Policy Compliance',
      status: 'Verified Stable',
      type: 'success',
      icon: '🛡️',
      score: '98%',
      detail: 'Assessment structure and weightage conform strictly to Academic Handbook.',
      metric: '0 Policy Breaches'
    }
  ];

  return (
    <div className="radar-section">
      <div className="section-header-row">
        <div>
          <div className="section-eyebrow">INTELLIGENCE RADAR</div>
          <h2 className="section-title">Information Health & Anomaly Radar</h2>
        </div>
        <div className="radar-summary-pill">
          <span className="radar-pulse-dot"></span>
          <span>Live Twin Telemetry: <strong>Requires Attention</strong></span>
        </div>
      </div>

      <div className="radar-grid">
        {radarItems.map((item) => (
          <div 
            key={item.id} 
            className={`radar-card radar-${item.type}`}
            onClick={() => onSelectCategory && onSelectCategory(item.id)}
          >
            <div className="radar-card-top">
              <div className="radar-icon-box">{item.icon}</div>
              <span className={`radar-status-badge badge-${item.type}`}>
                {item.status}
              </span>
            </div>

            <h3 className="radar-card-title">{item.title}</h3>
            <p className="radar-card-detail">{item.detail}</p>

            <div className="radar-card-footer">
              <span className="radar-metric-tag">{item.metric}</span>
              <div className="radar-score-wrap">
                <span className="radar-score-label">Integrity</span>
                <span className="radar-score-value">{item.score}</span>
              </div>
            </div>

            <div className="radar-progress-bar">
              <div 
                className={`radar-progress-fill fill-${item.type}`} 
                style={{ width: item.score }}
              ></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
