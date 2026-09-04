import React, { useState } from 'react';
import AIWidget from './components/AIWidget';

export default function App() {
  const [activeAccount, setActiveAccount] = useState('Checking');

  return (
    <div className="app-container">
      <header className="nav-bar">
        <div className="logo">
          <span>🏛️ Sterling Private Bank</span>
        </div>
        <div>
          <button className="btn-action" style={{ background: '#ffffff', color: '#09090b' }}>
            Account Settings
          </button>
        </div>
      </header>

      <main>
        <div className="card-grid">
          <div className="bank-card">
            <div className="account-type">Primary Checking Account</div>
            <div className="balance">$24,850.75</div>
            <div className="actions-row">
              <button className="btn-action" onClick={() => alert('Transfer Funds')}>Transfer</button>
              <button className="btn-action" onClick={() => alert('Pay Bills')}>Pay Bill</button>
            </div>
          </div>

          <div className="bank-card">
            <div className="account-type">High-Yield Treasury Savings (5.2% APY)</div>
            <div className="balance">$142,500.00</div>
            <div className="actions-row">
              <button className="btn-action" onClick={() => alert('Deposit')}>Deposit</button>
              <button className="btn-action" onClick={() => alert('Statements')}>Statements</button>
            </div>
          </div>
        </div>
      </main>

      {/* ================================================================= */}
      {/* 🔌 PLUG-N-PLAY AI WIDGET COMPONENT (REACT JSX HOOK)                */}
      {/* ================================================================= */}
      <AIWidget userId="cust_sterling_99" userRole="user" />
    </div>
  );
}
