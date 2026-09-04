import React, { useState } from 'react';

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
      {/* 🔌 PASTE YOUR REACT COMPONENT OR EMBED WIDGET HERE                 */}
      {/* (Generate from Agent Studio -> Embed Code -> React Export)        */}
      {/* ================================================================= */}
    </div>
  );
}
