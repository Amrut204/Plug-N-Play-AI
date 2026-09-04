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
    script.src = 'http://127.0.0.1:8000/static/pnp-widget.js';
    script.setAttribute('data-api-host', 'http://127.0.0.1:8000');
    script.setAttribute('data-agent-id', '9b7f7f22-a73c-472a-8f14-0b97c6e0e63d');
    script.setAttribute('data-title', 'customersupport');
    script.setAttribute('data-user-id', userId);
    script.setAttribute('data-user-role', userRole);
    script.setAttribute('data-primary-color', '#09090b');
    script.setAttribute('data-accent-color', '#318c52');
    script.setAttribute('data-bg-color', '#09090b');
    script.setAttribute('data-header-bg', '#121215');
    script.setAttribute('data-text-color', '#f8fafc');
    script.setAttribute('data-user-bubble', '#ffffff');
    script.setAttribute('data-position', 'bottom-right');
    script.setAttribute('data-widget-size', 'medium');
    script.setAttribute('data-btn-shape', 'circle');
    script.setAttribute('data-border-radius', '24');
    script.setAttribute('data-theme', 'dark');
    script.setAttribute('data-welcome', 'Hello! I am your AI Assistant. Ask me anything or tap the mic to speak:');
    script.setAttribute('data-show-branding', 'true');
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