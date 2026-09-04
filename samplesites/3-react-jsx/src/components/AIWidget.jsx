// src/components/AIWidget.jsx (JavaScript / JSX)
import { useEffect } from 'react';

export default function AIWidget({ userId = 'guest', userRole = 'user' }) {
  useEffect(() => {
    const script = document.createElement('script');
    // Paste your exported React component configuration from Agent Studio below:
    script.src = 'https://plug-n-play-rag.onrender.com/static/pnp-widget.js';
    script.setAttribute('data-api-host', 'https://plug-n-play-rag.onrender.com');
    script.setAttribute('data-agent-id', 'YOUR_AGENT_ID');
    script.setAttribute('data-title', 'AI Assistant');
    script.setAttribute('data-user-id', userId);
    script.setAttribute('data-user-role', userRole);
    script.setAttribute('data-theme', 'dark');
    script.async = true;
    document.body.appendChild(script);

    return () => {
      document.body.removeChild(script);
      const widget = document.getElementById('pnp-widget-container');
      const btn = document.getElementById('pnp-widget-trigger');
      if (widget) widget.remove();
      if (btn) btn.remove();
    };
  }, [userId, userRole]);

  return null;
}