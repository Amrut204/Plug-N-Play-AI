// src/components/AIWidget.tsx (TypeScript + Vite / SWC / CRA)
import React, { useEffect } from 'react';

interface AIWidgetProps {
  userId?: string;
  userRole?: 'user' | 'student' | 'staff' | 'admin';
}

export const AIWidget: React.FC<AIWidgetProps> = ({
  userId = 'guest',
  userRole = 'user'
}) => {
  useEffect(() => {
    const script = document.createElement('script');
    // Paste your exported React component configuration from Agent Studio below:
    script.src = 'https://plug-n-play-rag.onrender.com/static/pnp-widget.js';
    script.setAttribute('data-api-host', 'https://plug-n-play-rag.onrender.com');
    script.setAttribute('data-agent-id', 'YOUR_AGENT_ID');
    script.setAttribute('data-title', 'AI Assistant');
    script.setAttribute('data-user-id', userId);
    script.setAttribute('data-user-role', userRole);
    script.async = true;
    document.body.appendChild(script);

    return () => {
      document.body.removeChild(script);
      document.getElementById('pnp-widget-container')?.remove();
      document.getElementById('pnp-widget-trigger')?.remove();
    };
  }, [userId, userRole]);

  return null;
};