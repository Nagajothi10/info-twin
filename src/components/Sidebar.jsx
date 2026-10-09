import React from 'react';

export default function Sidebar({ activeTab, setActiveTab, counts = {} }) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊', badge: null },
    { id: 'documents', label: 'Documents', icon: '📁', badge: counts.docs || 6 },
    { id: 'conflicts', label: 'Claim Conflicts', icon: '⚠️', badge: counts.conflicts || 3, badgeType: 'danger' },
    { id: 'git-conflicts', label: 'Git Merge Conflicts', icon: '🔀', badge: 'Git', badgeType: 'info' },
    { id: 'changes', label: 'Changes', icon: '🔄', badge: counts.changes || 5, badgeType: 'info' },
    { id: 'evidence', label: 'Evidence', icon: '🔍', badge: null },
    { id: 'impact', label: 'Impact Analysis', icon: '⚡', badge: 'Ripple' },
    { id: 'simulator', label: 'What-If Simulator', icon: '🔮', badge: 'Live' }
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-logo-wrap">
          <div className="brand-logo-icon">
            <span className="logo-spark">✨</span>
          </div>
          <div className="brand-text">
            <h1 className="brand-title">INFO-TWIN</h1>
            <span className="brand-subtitle">Information Intelligence</span>
          </div>
        </div>
        <div className="brand-tag">
          <span className="tag-dot"></span>
          <span>Core AI Active</span>
        </div>
      </div>

      <div className="pipeline-crumb">
        <span className="pipeline-label">PIPELINE FLOW</span>
        <div className="pipeline-steps">
          <span className="p-step">Upload</span>
          <span className="p-arrow">→</span>
          <span className="p-step">Understand</span>
          <span className="p-arrow">→</span>
          <span className="p-step">Detect</span>
          <span className="p-arrow">→</span>
          <span className="p-step">Evidence</span>
          <span className="p-arrow">→</span>
          <span className="p-step">Impact</span>
          <span className="p-arrow">→</span>
          <span className="p-step">What-If</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-group-title">NAVIGATION</div>
        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
              {item.badge && (
                <span className={`nav-badge ${item.badgeType || 'default'}`}>
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="system-health-card">
          <div className="health-row">
            <span className="health-indicator"></span>
            <span className="health-title">Digital Twin Engine</span>
          </div>
          <p className="health-desc">Cross-document semantic graph synced</p>
          <div className="health-meter-wrap">
            <div className="health-meter-bar" style={{ width: '94%' }}></div>
          </div>
          <span className="health-stat">94% Confidence Rate</span>
        </div>
      </div>
    </aside>
  );
}
