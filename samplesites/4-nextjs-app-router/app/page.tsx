import React from 'react';

export default function HomePage() {
  return (
    <div className="container">
      <header className="header-nav">
        <div style={{ fontSize: '20px', fontWeight: '800' }}>
          ☁️ OmniCloud Engine
        </div>
        <nav style={{ display: 'flex', gap: '20px', fontSize: '14px', color: 'var(--text-muted)' }}>
          <span>Solutions</span>
          <span>Documentation</span>
          <span>Security &amp; HIPAA</span>
        </nav>
      </header>

      <main>
        <section className="hero-box">
          <h1>Next-Gen Serverless Vector Architecture</h1>
          <p>
            Deploy sub-millisecond AI pipelines, automated SQL synthesis, and private VPC embeddings without managing infrastructure.
          </p>
          <button className="btn-cta">Start Free Deployment</button>
        </section>
      </main>
    </div>
  );
}
