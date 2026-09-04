import React, { useState } from 'react';
import { AIWidget } from './components/AIWidget';

export default function App() {
  const [role, setRole] = useState<'user' | 'admin'>('user');

  return (
    <div className="app-container">
      <header className="navbar">
        <div className="logo">
          <span>⚡ Nexus Cloud Dashboard</span>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Role:</span>
          <select 
            value={role} 
            onChange={(e) => setRole(e.target.value as any)}
            style={{ background: 'var(--surface)', color: 'var(--text-main)', border: '1px solid var(--border)', padding: '6px 12px', borderRadius: '6px' }}
          >
            <option value="user">User (Customer)</option>
            <option value="admin">Admin (Full Access)</option>
          </select>
        </div>
      </header>

      <main>
        <section className="hero-card">
          <h1>Cluster Performance &amp; SLA Metrics</h1>
          <p>Real-time distributed telemetry, vector indexing load, and database IOPS monitoring for enterprise tenants.</p>
        </section>

        <div className="metrics-grid">
          <div className="metric-box">
            <div className="metric-title">Active Ingestion Pipelines</div>
            <div className="metric-value">12 Nodes</div>
            <div className="metric-sub">▲ 99.98% Uptime</div>
          </div>
          <div className="metric-box">
            <div className="metric-title">Vector Search Latency</div>
            <div className="metric-value">4.2 ms</div>
            <div className="metric-sub">FastEmbed (384-dim)</div>
          </div>
          <div className="metric-box">
            <div className="metric-title">Memory Allocation</div>
            <div className="metric-value">2.4 GB / 8 GB</div>
            <div className="metric-sub">Normal Range</div>
          </div>
        </div>
      </main>

      {/* ================================================================= */}
      {/* 🔌 PLUG-N-PLAY AI WIDGET COMPONENT (REACT TSX HOOK)               */}
      {/* ================================================================= */}
      <AIWidget userId="user_demo_101" userRole={role} />
    </div>
  );
}
