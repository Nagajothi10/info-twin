import React from 'react';

export default function StatCard({ 
  title, 
  value, 
  subtext, 
  icon, 
  variant = 'default',
  trend,
  onClick
}) {
  return (
    <div className={`stat-card stat-card-${variant}`} onClick={onClick}>
      <div className="stat-card-header">
        <span className="stat-icon-badge">{icon}</span>
        {trend && (
          <span className={`stat-trend-tag trend-${trend.type}`}>
            {trend.label}
          </span>
        )}
      </div>
      <div className="stat-card-body">
        <div className="stat-value">{value}</div>
        <div className="stat-title">{title}</div>
        {subtext && <div className="stat-subtext">{subtext}</div>}
      </div>
      <div className="stat-glow"></div>
    </div>
  );
}
