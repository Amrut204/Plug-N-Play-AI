(function() {
    // Plug-N-Play AI Universal Embeddable Widget v2 — Fully Customizable
    const scriptTag = document.currentScript || document.querySelector('script[src*="pnp-widget.js"]');
    const agentId = (scriptTag && scriptTag.getAttribute('data-agent-id')) || 'default';
    let sessionToken = scriptTag ? scriptTag.getAttribute('data-session-token') : null;
    let activeSessionId = null;
    const apiHost = (scriptTag && scriptTag.getAttribute('data-api-host')) || 'http://127.0.0.1:8000';
    const userId = (scriptTag && scriptTag.getAttribute('data-user-id')) || 'guest_user';
    const userRole = (scriptTag && scriptTag.getAttribute('data-user-role')) || 'user';
    const botTitle = (scriptTag && scriptTag.getAttribute('data-title')) || 'AI Assistant';
    const botSubtitle = (scriptTag && scriptTag.getAttribute('data-subtitle')) || 'Connected to Plug-N-Play Layer';

    // --- Customization data-* attributes ---
    const primaryColor = (scriptTag && scriptTag.getAttribute('data-primary-color')) || '#09090b';
    const bgColor = (scriptTag && scriptTag.getAttribute('data-bg-color')) || '#09090b';
    const headerBg = (scriptTag && scriptTag.getAttribute('data-header-bg')) || '#121215';
    const textColor = (scriptTag && scriptTag.getAttribute('data-text-color')) || '#f8fafc';
    const userBubble = (scriptTag && scriptTag.getAttribute('data-user-bubble')) || '#ffffff';
    const accentColor = (scriptTag && scriptTag.getAttribute('data-accent-color')) || '#22c55e';
    const borderRadius = (scriptTag && scriptTag.getAttribute('data-border-radius')) || '18';
    const widgetPosition = (scriptTag && scriptTag.getAttribute('data-position')) || 'bottom-right';
    const fontFamily = (scriptTag && scriptTag.getAttribute('data-font-family')) || '';
    const widgetSize = (scriptTag && scriptTag.getAttribute('data-widget-size')) || 'medium';
    const btnShape = (scriptTag && scriptTag.getAttribute('data-btn-shape')) || 'circle';
    const avatarText = (scriptTag && scriptTag.getAttribute('data-avatar-text')) || 'AI';
    const avatarUrl = (scriptTag && scriptTag.getAttribute('data-avatar-url')) || '';
    const welcomeMsg = (scriptTag && scriptTag.getAttribute('data-welcome')) || 'Hello! I am your AI Assistant. Ask me anything or tap the mic to speak:';
    const showBranding = (scriptTag && scriptTag.getAttribute('data-show-branding')) !== 'false';
    const themeMode = (scriptTag && scriptTag.getAttribute('data-theme')) || 'dark';
    const allowedDomains = (scriptTag && scriptTag.getAttribute('data-allowed-domains')) || '';
    const autoOpenMs = parseInt((scriptTag && scriptTag.getAttribute('data-auto-open')) || '0', 10);
    const persistSession = (scriptTag && scriptTag.getAttribute('data-persist-session')) === 'true';
    const lang = (scriptTag && scriptTag.getAttribute('data-lang')) || 'en';

    // --- Domain Allowlisting ---
    if (allowedDomains) {
        const allowed = allowedDomains.split(',').map(d => d.trim().toLowerCase());
        const currentHost = window.location.hostname.toLowerCase();
        if (!allowed.some(d => currentHost === d || currentHost.endsWith('.' + d))) {
            console.warn('[Plug-N-Play AI] Widget blocked on unauthorized domain:', currentHost);
            return;
        }
    }

    // --- i18n Labels ---
    const i18n = {
        en: { send: 'Send', listening: 'Listening... (Speak now)', placeholder: 'Type or speak a question...', helpful: 'Helpful?', read: 'Read', stop: 'Stop', support: 'Support', connecting: 'Connecting...', alertSent: 'Alert Sent', escalated: 'Human Support Escalated', escalatedDesc: 'A support representative has been notified. Someone will follow up shortly.', thinking: 'Thinking...', active: 'Active Session', poweredBy: 'Powered by Plug-N-Play AI', noVoice: 'Voice not supported in this browser.' },
        es: { send: 'Enviar', listening: 'Escuchando... (Habla ahora)', placeholder: 'Escribe o habla tu pregunta...', helpful: '¿Útil?', read: 'Leer', stop: 'Parar', support: 'Soporte', connecting: 'Conectando...', alertSent: 'Alerta enviada', escalated: 'Soporte humano escalado', escalatedDesc: 'Un representante ha sido notificado.', thinking: 'Pensando...', active: 'Sesión activa', poweredBy: 'Impulsado por Plug-N-Play AI', noVoice: 'Voz no soportada.' },
        hi: { send: 'भेजें', listening: 'सुन रहे हैं... (अब बोलें)', placeholder: 'सवाल टाइप या बोलें...', helpful: 'सहायक?', read: 'पढ़ें', stop: 'रोकें', support: 'सहायता', connecting: 'जोड़ रहे हैं...', alertSent: 'अलर्ट भेजा', escalated: 'मानव सहायता', escalatedDesc: 'एक प्रतिनिधि को सूचित किया गया है।', thinking: 'सोच रहे हैं...', active: 'सक्रिय सत्र', poweredBy: 'Plug-N-Play AI द्वारा संचालित', noVoice: 'आवाज़ समर्थित नहीं है।' },
        fr: { send: 'Envoyer', listening: 'Écoute... (Parlez)', placeholder: 'Tapez ou parlez...', helpful: 'Utile?', read: 'Lire', stop: 'Arrêter', support: 'Support', connecting: 'Connexion...', alertSent: 'Alerte envoyée', escalated: 'Support humain', escalatedDesc: 'Un représentant a été notifié.', thinking: 'Réflexion...', active: 'Session active', poweredBy: 'Propulsé par Plug-N-Play AI', noVoice: 'Voix non supportée.' },
    };
    const t = i18n[lang] || i18n.en;

    // --- Starter Questions / Conversation Chips ---
    const rawStarters = (scriptTag && (scriptTag.getAttribute('data-starter-questions') || scriptTag.getAttribute('data-starter-prompts'))) || '';
    let starterPrompts = [];
    if (rawStarters) {
        try { starterPrompts = JSON.parse(rawStarters); } catch (e) {
            starterPrompts = rawStarters.split(',').map(s => s.trim()).filter(Boolean);
        }
    }
    if (!starterPrompts || starterPrompts.length === 0) {
        starterPrompts = ["What are the main guidelines?", "How do I look up my data?", "What is the official policy?"];
    }

    // --- Inject custom Google Font if specified ---
    if (fontFamily && !['system', 'default', ''].includes(fontFamily.toLowerCase())) {
        const fontLink = document.createElement('link');
        fontLink.rel = 'stylesheet';
        fontLink.href = `https://fonts.googleapis.com/css2?family=${encodeURIComponent(fontFamily)}:wght@400;500;600;700&display=swap`;
        document.head.appendChild(fontLink);
    }

    // --- Computed theme values ---
    const isLight = themeMode === 'light';
    const cPrimary = primaryColor;
    const cBg = isLight ? '#ffffff' : bgColor;
    const cHeaderBg = isLight ? '#f8fafc' : headerBg;
    const cText = isLight ? '#0f172a' : textColor;
    const cTextMuted = isLight ? '#64748b' : '#a1a1aa';
    const cTextDim = isLight ? '#94a3b8' : '#71717a';
    const cUserBubble = isLight ? '#0f172a' : userBubble;
    const cUserBubbleText = isLight ? '#ffffff' : (userBubble === '#ffffff' ? '#09090b' : '#ffffff');
    const cAsstBubble = isLight ? '#f1f5f9' : '#18181b';
    const cAsstBorder = isLight ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.08)';
    const cInputBg = isLight ? '#f1f5f9' : '#18181b';
    const cInputBorder = isLight ? 'rgba(0,0,0,0.12)' : 'rgba(255,255,255,0.1)';
    const cBorderSubtle = isLight ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.12)';
    const cChipBg = isLight ? 'rgba(0,0,0,0.04)' : 'rgba(255,255,255,0.05)';
    const cChipBorder = isLight ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)';
    const cAccent = accentColor;
    const cSendBg = isLight ? '#0f172a' : '#ffffff';
    const cSendText = isLight ? '#ffffff' : '#09090b';
    const cIconBtnBg = isLight ? '#e2e8f0' : '#18181b';
    const cIconBtnBorder = isLight ? 'rgba(0,0,0,0.12)' : 'rgba(255,255,255,0.12)';
    const cIconBtnText = isLight ? '#334155' : '#e2e8f0';
    const fontStack = fontFamily && !['system', 'default', ''].includes(fontFamily.toLowerCase())
        ? `'${fontFamily}', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
        : `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`;
    const bRadius = parseInt(borderRadius, 10) || 18;

    // --- Size Presets ---
    const sizes = { small: { w: 360, h: 480 }, medium: { w: 410, h: 590 }, large: { w: 460, h: 660 } };
    const sz = sizes[widgetSize] || sizes.medium;

    // --- Position ---
    const pos = widgetPosition.toLowerCase();
    const posBottom = pos.includes('bottom');
    const posRight = pos.includes('right');
    const btnPos = `${posBottom ? 'bottom: 24px;' : 'top: 24px;'} ${posRight ? 'right: 24px;' : 'left: 24px;'}`;
    const winPos = `${posBottom ? 'bottom: 92px;' : 'top: 92px;'} ${posRight ? 'right: 24px;' : 'left: 24px;'}`;

    // --- Button Shape ---
    const btnBorderRadius = btnShape === 'pill' ? '28px' : btnShape === 'square' ? '12px' : '50%';
    const btnWidth = btnShape === 'pill' ? '72px' : '56px';

    // Inject styles
    const style = document.createElement('style');
    style.innerHTML = `
        .pnp-widget-btn {
            position: fixed;
            ${btnPos}
            width: ${btnWidth};
            height: 56px;
            border-radius: ${btnBorderRadius};
            background: ${cPrimary};
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
            border: 1px solid ${cBorderSubtle};
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 999999;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            color: ${cSendText};
        }
        .pnp-widget-btn:hover {
            transform: scale(1.06);
            box-shadow: 0 14px 28px -4px rgba(0, 0, 0, 0.5);
        }
        .pnp-widget-window {
            position: fixed;
            ${winPos}
            width: ${sz.w}px;
            height: ${sz.h}px;
            max-height: calc(100vh - 120px);
            max-width: calc(100vw - 32px);
            background: ${cBg};
            border: 1px solid ${cBorderSubtle};
            border-radius: ${bRadius}px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.75);
            display: none;
            flex-direction: column;
            overflow: hidden;
            z-index: 999999;
            font-family: ${fontStack};
            color: ${cText};
            animation: pnpSlideUp 0.25s ease-out forwards;
        }
        @keyframes pnpSlideUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .pnp-header {
            padding: 14px 18px;
            background: ${cHeaderBg};
            border-bottom: 1px solid ${cBorderSubtle};
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .pnp-header-info {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .pnp-avatar {
            width: 34px;
            height: 34px;
            border-radius: 8px;
            background: ${cUserBubble};
            color: ${cUserBubbleText};
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: ${avatarUrl ? '0' : '14px'};
            overflow: hidden;
            ${avatarUrl ? `background-image: url('${avatarUrl}'); background-size: cover; background-position: center;` : ''}
        }
        .pnp-header-title {
            font-size: 13.5px;
            font-weight: 700;
            color: ${cText};
            line-height: 1.2;
        }
        .pnp-header-status {
            font-size: 10.5px;
            color: ${cAccent};
            display: flex;
            align-items: center;
            gap: 5px;
            margin-top: 2px;
        }
        .pnp-status-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: ${cAccent};
            display: inline-block;
        }
        .pnp-header-actions {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .pnp-escalate-btn {
            background: rgba(239, 68, 68, 0.12);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #f87171;
            font-size: 10.5px;
            font-weight: 600;
            padding: 4px 8px;
            border-radius: 6px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 4px;
            transition: all 0.2s;
        }
        .pnp-escalate-btn:hover {
            background: rgba(239, 68, 68, 0.25);
            color: #ffffff;
        }
        .pnp-close-btn {
            background: transparent;
            border: none;
            color: ${cTextDim};
            cursor: pointer;
            padding: 4px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .pnp-close-btn:hover {
            color: ${cText};
            background: ${cChipBg};
        }
        .pnp-messages {
            flex: 1;
            padding: 16px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 14px;
            background: ${cBg};
        }
        .pnp-messages::-webkit-scrollbar { width: 4px; }
        .pnp-messages::-webkit-scrollbar-track { background: transparent; }
        .pnp-messages::-webkit-scrollbar-thumb { background: ${cTextDim}; border-radius: 4px; }
        .pnp-msg {
            max-width: 86%;
            padding: 10px 14px;
            border-radius: 12px;
            font-size: 13px;
            line-height: 1.5;
            word-break: break-word;
        }
        .pnp-msg-user {
            align-self: flex-end;
            background: ${cUserBubble};
            color: ${cUserBubbleText};
            border-bottom-right-radius: 3px;
        }
        .pnp-msg-asst {
            align-self: flex-start;
            background: ${cAsstBubble};
            border: 1px solid ${cAsstBorder};
            color: ${cText};
            border-bottom-left-radius: 3px;
        }
        .pnp-badge-route {
            display: inline-block;
            font-size: 9.5px;
            font-weight: 700;
            padding: 2px 7px;
            border-radius: 999px;
            letter-spacing: 0.04em;
            margin-bottom: 6px;
        }
        .pnp-badge-sql { background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }
        .pnp-badge-rag { background: rgba(34, 197, 94, 0.15); color: #22c55e; border: 1px solid rgba(34, 197, 94, 0.3); }
        .pnp-badge-hybrid { background: rgba(192, 132, 252, 0.15); color: #c084fc; border: 1px solid rgba(192, 132, 252, 0.3); }
        .pnp-badge-blocked { background: rgba(244, 63, 94, 0.15); color: #fda4af; border: 1px solid rgba(244, 63, 94, 0.3); }
        .pnp-badge-action { background: rgba(234, 179, 8, 0.15); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.35); }
        .pnp-badge-cached { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); margin-left: 4px; }
        
        /* Action Proposal Card */
        .pnp-action-card {
            margin-top: 10px;
            padding: 12px;
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.12);
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .pnp-action-card-header {
            display: flex;
            align-items: center;
            gap: 6px;
            font-weight: 600;
            font-size: 12px;
            color: ${cText};
        }
        .pnp-action-params {
            display: flex;
            flex-direction: column;
            gap: 4px;
            padding: 6px 8px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 6px;
            font-size: 11.5px;
        }
        .pnp-action-param-row {
            display: flex;
            justify-content: space-between;
            gap: 8px;
        }
        .pnp-action-param-key {
            color: ${cTextDim};
            font-family: monospace;
            text-transform: capitalize;
        }
        .pnp-action-param-val {
            color: ${cText};
            font-weight: 500;
            word-break: break-all;
        }
        .pnp-action-btns {
            display: flex;
            gap: 8px;
            margin-top: 4px;
        }
        .pnp-action-btn-confirm {
            flex: 1;
            background: #22c55e;
            color: #ffffff;
            border: none;
            border-radius: 6px;
            padding: 7px 12px;
            font-size: 11.5px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.15s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
        }
        .pnp-action-btn-confirm:hover {
            background: #16a34a;
        }
        .pnp-action-btn-dismiss {
            background: rgba(255, 255, 255, 0.08);
            color: ${cTextDim};
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            padding: 7px 10px;
            font-size: 11.5px;
            cursor: pointer;
            transition: all 0.15s;
        }
        .pnp-action-btn-dismiss:hover {
            background: rgba(255, 255, 255, 0.15);
            color: ${cText};
        }
        .pnp-action-status-success {
            display: flex;
            align-items: center;
            gap: 6px;
            color: #4ade80;
            font-weight: 600;
            font-size: 12px;
            padding: 6px 8px;
            background: rgba(34, 197, 94, 0.12);
            border: 1px solid rgba(34, 197, 94, 0.25);
            border-radius: 6px;
        }
        .pnp-action-status-error {
            display: flex;
            align-items: center;
            gap: 6px;
            color: #f87171;
            font-weight: 600;
            font-size: 12px;
            padding: 6px 8px;
            background: rgba(239, 68, 68, 0.12);
            border: 1px solid rgba(239, 68, 68, 0.25);
            border-radius: 6px;
        }
        
        .pnp-feedback-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-top: 8px;
            padding-top: 6px;
            border-top: 1px solid ${cAsstBorder};
        }
        .pnp-fb-actions {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .pnp-fb-btn {
            background: transparent;
            border: none;
            color: ${cTextDim};
            font-size: 11.5px;
            cursor: pointer;
            padding: 2px 6px;
            border-radius: 4px;
            transition: all 0.2s;
        }
        .pnp-fb-btn:hover {
            color: ${cText};
            background: ${cChipBg};
        }
        .pnp-fb-btn.active {
            color: ${cAccent};
            background: rgba(34, 197, 94, 0.15);
        }
        .pnp-fb-btn.pnp-tts-speaking {
            color: #ef4444 !important;
            background: rgba(239, 68, 68, 0.15) !important;
            border-color: rgba(239, 68, 68, 0.35) !important;
            font-weight: 700;
            animation: pnpPulse 1.5s infinite;
        }
        
        .pnp-input-area {
            padding: 12px 14px;
            background: ${cHeaderBg};
            border-top: 1px solid ${cBorderSubtle};
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .pnp-input {
            flex: 1;
            background: ${cInputBg};
            border: 1px solid ${cInputBorder};
            border-radius: 10px;
            padding: 9px 13px;
            font-size: 13px;
            color: ${cText};
            outline: none;
            font-family: ${fontStack};
            transition: all 0.2s;
        }
        .pnp-input:focus {
            border-color: ${cText};
            box-shadow: 0 0 0 2px ${isLight ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.15)'};
        }
        .pnp-input::placeholder { color: ${cTextMuted}; }
        .pnp-icon-btn {
            background: ${cIconBtnBg};
            border: 1px solid ${cIconBtnBorder};
            color: ${cIconBtnText};
            border-radius: 10px;
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s;
            flex-shrink: 0;
        }
        .pnp-icon-btn:hover {
            background: ${isLight ? '#cbd5e1' : '#27272a'};
            color: ${cText};
            border-color: ${isLight ? 'rgba(0,0,0,0.2)' : 'rgba(255,255,255,0.25)'};
        }
        .pnp-mic-btn.recording {
            background: #ef4444 !important;
            color: #ffffff !important;
            border-color: #ef4444 !important;
            animation: pnpPulse 1.2s infinite;
        }
        @keyframes pnpPulse {
            0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
            70% { transform: scale(1.05); box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
            100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
        }
        .pnp-send-btn {
            background: ${cSendBg};
            border: none;
            color: ${cSendText};
            border-radius: 10px;
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s;
            flex-shrink: 0;
        }
        .pnp-send-btn:hover {
            opacity: 0.85;
            transform: scale(1.03);
        }
        .pnp-starter-chips {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 8px;
        }
        .pnp-chip {
            background: ${cChipBg};
            border: 1px solid ${cChipBorder};
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 11px;
            color: ${cTextMuted};
            cursor: pointer;
            transition: all 0.2s;
        }
        .pnp-chip:hover {
            color: ${cText};
            background: ${isLight ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.1)'};
            border-color: ${isLight ? 'rgba(0,0,0,0.15)' : 'rgba(255,255,255,0.2)'};
        }
        .pnp-branding {
            text-align: center;
            padding: 6px 14px;
            font-size: 10px;
            color: ${cTextDim};
            background: ${cHeaderBg};
            border-top: 1px solid ${cBorderSubtle};
            letter-spacing: 0.02em;
        }
        .pnp-branding a {
            color: ${cTextMuted};
            text-decoration: none;
            font-weight: 600;
        }
        .pnp-branding a:hover { text-decoration: underline; }
    `;
    document.head.appendChild(style);

    // Widget HTML Elements
    const triggerBtn = document.createElement('button');
    triggerBtn.id = 'pnp-widget-trigger';
    triggerBtn.className = 'pnp-widget-btn';
    triggerBtn.title = 'Open AI Assistant';
    triggerBtn.innerHTML = `
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
    `;

    const chatWindow = document.createElement('div');
    chatWindow.id = 'pnp-widget-container';
    chatWindow.className = 'pnp-widget-window';
    chatWindow.innerHTML = `
        <div class="pnp-header">
            <div class="pnp-header-info">
                <div class="pnp-avatar">${avatarUrl ? '' : avatarText}</div>
                <div>
                    <div class="pnp-header-title">${botTitle}</div>
                    <div class="pnp-header-status">
                        <span class="pnp-status-dot"></span>
                        <span>${t.active}</span>
                    </div>
                </div>
            </div>
            <div class="pnp-header-actions">
                <button class="pnp-escalate-btn" id="pnp-btn-escalate" title="Request Live Support Agent">
                    <span>${t.support}</span>
                </button>
                <button class="pnp-close-btn" id="pnp-close-btn" title="Close chat">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>
        </div>
        <div class="pnp-messages" id="pnp-msg-list">
            <div class="pnp-msg pnp-msg-asst">
                <div>${welcomeMsg}</div>
                <div class="pnp-starter-chips" id="pnp-chips-container"></div>
            </div>
        </div>
        <div class="pnp-input-area">
            <button class="pnp-icon-btn pnp-mic-btn" id="pnp-mic-btn" title="Click to speak (Voice Input)">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                    <line x1="12" y1="19" x2="12" y2="23"></line>
                    <line x1="8" y1="23" x2="16" y2="23"></line>
                </svg>
            </button>
            <input type="text" class="pnp-input" id="pnp-input-field" placeholder="${t.placeholder}" />
            <button class="pnp-send-btn" id="pnp-send-btn" title="${t.send}">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="22" y1="2" x2="11" y2="13"></line>
                    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                </svg>
            </button>
        </div>
        ${showBranding ? `<div class="pnp-branding">${t.poweredBy}</div>` : ''}
    `;

    document.body.appendChild(triggerBtn);
    document.body.appendChild(chatWindow);

    // Elements & State
    const msgList = document.getElementById('pnp-msg-list');
    const inputField = document.getElementById('pnp-input-field');
    const sendBtn = document.getElementById('pnp-send-btn');
    const micBtn = document.getElementById('pnp-mic-btn');
    const escalateBtn = document.getElementById('pnp-btn-escalate');
    const closeBtn = document.getElementById('pnp-close-btn');
    const chipsContainer = document.getElementById('pnp-chips-container');

    // Populate Starter Prompt Chips
    starterPrompts.forEach(promptText => {
        const chip = document.createElement('button');
        chip.type = 'button';
        chip.className = 'pnp-chip';
        chip.innerText = promptText;
        chip.onclick = () => {
            inputField.value = promptText;
            handleSend();
        };
        chipsContainer.appendChild(chip);
    });

    // --- Session Persistence ---
    if (persistSession) {
        const savedSession = localStorage.getItem('pnp_session_' + agentId);
        if (savedSession) {
            try {
                const s = JSON.parse(savedSession);
                sessionToken = s.token;
                activeSessionId = s.sessionId;
            } catch (e) {}
        }
    }

    let isOpen = false;
    function toggleChat() {
        isOpen = !isOpen;
        chatWindow.style.display = isOpen ? 'flex' : 'none';
        if (isOpen) {
            inputField.focus();
            ensureSession();
        }
    }

    triggerBtn.onclick = toggleChat;
    closeBtn.onclick = toggleChat;

    // --- Auto-Open ---
    if (autoOpenMs > 0) {
        setTimeout(() => { if (!isOpen) toggleChat(); }, autoOpenMs);
    }

    // --- Web Speech API (Speech-to-Text) ---
    let isRecording = false;
    let recognition = null;

    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRec();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = lang === 'hi' ? 'hi-IN' : lang === 'es' ? 'es-ES' : lang === 'fr' ? 'fr-FR' : 'en-US';

        recognition.onstart = () => {
            isRecording = true;
            micBtn.classList.add('recording');
            inputField.placeholder = t.listening;
        };

        recognition.onresult = (event) => {
            let transcript = '';
            for (let i = event.resultIndex; i < event.results.length; ++i) {
                transcript += event.results[i][0].transcript;
            }
            inputField.value = transcript;
        };

        recognition.onend = () => {
            isRecording = false;
            micBtn.classList.remove('recording');
            inputField.placeholder = t.placeholder;
            if (inputField.value.trim()) {
                handleSend();
            }
        };

        recognition.onerror = (e) => {
            isRecording = false;
            micBtn.classList.remove('recording');
            inputField.placeholder = t.placeholder;
        };
    }

    micBtn.onclick = () => {
        if (!recognition) {
            alert(t.noVoice);
            return;
        }
        if (isRecording) {
            recognition.stop();
        } else {
            recognition.start();
        }
    };

    // --- Clean Markdown & Asterisks Formatter ---
    function formatBotMessage(text) {
        if (!text) return '';
        let formatted = text;
        // 1. Remove standalone decorative triple asterisks or hyphens (e.g. *** or ---)
        formatted = formatted.replace(/^\s*[\*\-]{3,}\s*$/gm, '');
        // 2. Convert ***bold italic*** to <strong>$1</strong>
        formatted = formatted.replace(/\*\*\*(.*?)\*\*\*/g, '<strong>$1</strong>');
        // 3. Convert **bold** to <strong>$1</strong>
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // 4. Convert *italic* to <em>$1</em> (excluding double/triple remaining asterisks)
        formatted = formatted.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, '<em>$1</em>');
        // 5. Clean up any remaining stray asterisks like *** or **
        formatted = formatted.replace(/\*{2,}/g, '');
        // 6. Convert markdown list bullets * or - to clean bullets •
        formatted = formatted.replace(/^[\*\-]\s+(.+)$/gm, '• $1');
        // 7. Convert markdown links [title](url) to clickable safe links
        formatted = formatted.replace(/\[([^\]]+)\]\((https?:\/\/[^\s\)]+)\)/g, '<a href="$2" target="_blank" rel="noopener" style="color:inherit;text-decoration:underline;">$1</a>');
        // 8. Convert newlines to <br>
        formatted = formatted.replace(/\n/g, '<br>');
        return formatted;
    }

    // --- Text-to-Speech (TTS) with Play / Stop Toggle ---
    let currentSpeakingBtn = null;

    function stopSpeaking() {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
        }
        if (currentSpeakingBtn) {
            currentSpeakingBtn.innerHTML = `<span>${t.read}</span>`;
            currentSpeakingBtn.classList.remove('pnp-tts-speaking');
            currentSpeakingBtn = null;
        }
    }

    function toggleSpeakText(text, btnElement) {
        if (!('speechSynthesis' in window)) return;

        // If clicking on the currently playing button, stop immediately!
        if (currentSpeakingBtn === btnElement) {
            stopSpeaking();
            return;
        }

        // Otherwise stop any other speech first
        stopSpeaking();

        const cleanText = text.replace(/[*_#`~|•]/g, ' ');
        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.rate = 1.05;
        utterance.lang = lang === 'hi' ? 'hi-IN' : lang === 'es' ? 'es-ES' : lang === 'fr' ? 'fr-FR' : 'en-US';

        currentSpeakingBtn = btnElement;
        btnElement.innerHTML = `<span>${t.stop}</span>`;
        btnElement.classList.add('pnp-tts-speaking');

        utterance.onend = () => {
            if (currentSpeakingBtn === btnElement) {
                btnElement.innerHTML = `<span>${t.read}</span>`;
                btnElement.classList.remove('pnp-tts-speaking');
                currentSpeakingBtn = null;
            }
        };

        utterance.onerror = () => {
            if (currentSpeakingBtn === btnElement) {
                btnElement.innerHTML = `<span>${t.read}</span>`;
                btnElement.classList.remove('pnp-tts-speaking');
                currentSpeakingBtn = null;
            }
        };

        window.speechSynthesis.speak(utterance);
    }

    // --- Human Escalation Handler ---
    escalateBtn.onclick = async () => {
        await ensureSession();
        if (!activeSessionId) {
            alert('Session is initializing. Please try in a moment.');
            return;
        }
        try {
            escalateBtn.disabled = true;
            escalateBtn.innerText = t.connecting;
            const res = await fetch(`${apiHost}/api/v1/chat/escalate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: activeSessionId,
                    reason: 'User clicked Support button in widget',
                    user_contact: userId
                })
            });
            const data = await res.json();
            
            const noticeDiv = document.createElement('div');
            noticeDiv.className = 'pnp-msg pnp-msg-asst';
            noticeDiv.style.borderColor = 'rgba(239, 68, 68, 0.4)';
            noticeDiv.innerHTML = `
                <div style="color: #f87171; font-weight: 700; font-size: 11.5px; margin-bottom: 4px;">${t.escalated}</div>
                <div>${t.escalatedDesc}</div>
            `;
            msgList.appendChild(noticeDiv);
            msgList.scrollTop = msgList.scrollHeight;
            escalateBtn.innerText = t.alertSent;
        } catch (e) {
            alert('Could not escalate session: ' + e.message);
            escalateBtn.disabled = false;
            escalateBtn.innerText = t.support;
        }
    };

    async function ensureSession() {
        if (sessionToken && activeSessionId) return sessionToken;
        try {
            const sRes = await fetch(`${apiHost}/api/v1/chat/sessions/create`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    agent_id: agentId,
                    external_user_id: userId,
                    user_role: userRole
                })
            });
            if (sRes.ok) {
                const sData = await sRes.json();
                sessionToken = sData.session_token;
                activeSessionId = sData.session_id;
                if (persistSession) {
                    localStorage.setItem('pnp_session_' + agentId, JSON.stringify({ token: sessionToken, sessionId: activeSessionId }));
                }
            }
        } catch (e) {
            console.warn('[Plug-N-Play AI] Session auto-init fallback:', e);
        }
        return sessionToken;
    }

    async function sendFeedback(messageId, rating, btnEl) {
        try {
            await fetch(`${apiHost}/api/v1/chat/feedback`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message_id: messageId, rating: rating })
            });
            const parent = btnEl.parentElement;
            parent.querySelectorAll('.pnp-fb-btn').forEach(b => b.classList.remove('active'));
            btnEl.classList.add('active');
        } catch (e) {
            console.warn('Feedback failed:', e);
        }
    }

    function renderActionProposalCard(container, proposal) {
        const card = document.createElement('div');
        card.className = 'pnp-action-card';

        const header = document.createElement('div');
        header.className = 'pnp-action-card-header';
        header.innerHTML = `<span>Proposed Action:</span> <strong>${proposal.display_name || proposal.name}</strong>`;
        card.appendChild(header);

        const paramsDiv = document.createElement('div');
        paramsDiv.className = 'pnp-action-params';
        const params = proposal.parameters || {};
        const keys = Object.keys(params);
        if (keys.length === 0) {
            paramsDiv.innerHTML = `<span style="opacity: 0.6; font-style: italic;">No extra parameters required.</span>`;
        } else {
            keys.forEach(k => {
                const row = document.createElement('div');
                row.className = 'pnp-action-param-row';
                row.innerHTML = `<span class="pnp-action-param-key">${k.replace(/_/g, ' ')}:</span><span class="pnp-action-param-val">${params[k]}</span>`;
                paramsDiv.appendChild(row);
            });
        }
        card.appendChild(paramsDiv);

        const btnRow = document.createElement('div');
        btnRow.className = 'pnp-action-btns';
        
        const confirmBtn = document.createElement('button');
        confirmBtn.className = 'pnp-action-btn-confirm';
        confirmBtn.innerHTML = `<span>✓ Confirm &amp; Execute</span>`;
        
        const dismissBtn = document.createElement('button');
        dismissBtn.className = 'pnp-action-btn-dismiss';
        dismissBtn.innerHTML = `<span>✕ Dismiss</span>`;

        btnRow.appendChild(confirmBtn);
        btnRow.appendChild(dismissBtn);
        card.appendChild(btnRow);

        const isBrowserRelay = (proposal.execution_target === 'browser') || (typeof proposal.endpoint_url === 'string' && proposal.endpoint_url.startsWith('/'));

        confirmBtn.onclick = async () => {
            confirmBtn.disabled = true;
            dismissBtn.disabled = true;
            confirmBtn.innerHTML = isBrowserRelay 
                ? `<span>⏳ Executing via active session...</span>`
                : `<span>⏳ Executing on secure server...</span>`;

            const startTime = Date.now();
            try {
                let isSuccess = false;
                let confirmationText = '';
                let errorMessage = '';

                if (isBrowserRelay) {
                    // --- BROWSER RELAY MODE ---
                    // 1. Dispatch custom event for host apps using WebSockets/event listeners
                    const eventName = proposal.client_event_name || 'pnp:action:execute';
                    const customEvt = new CustomEvent(eventName, {
                        detail: {
                            action_id: proposal.action_id,
                            name: proposal.name,
                            display_name: proposal.display_name,
                            parameters: proposal.parameters || {}
                        },
                        bubbles: true,
                        cancelable: true
                    });
                    window.dispatchEvent(customEvt);

                    // 2. Perform in-browser fetch with credentials: 'include' (inherits ambient cookies & sessions)
                    let responseStatus = 200;
                    let responseJson = null;
                    let rawText = '';

                    const endpoint = proposal.endpoint_url || '';
                    if (endpoint) {
                        try {
                            const bRes = await fetch(endpoint, {
                                method: proposal.http_method || 'POST',
                                credentials: 'include',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify(proposal.parameters || {})
                            });
                            responseStatus = bRes.status;
                            rawText = await bRes.text();
                            try { responseJson = JSON.parse(rawText); } catch (_) {}
                            isSuccess = (responseStatus >= 200 && responseStatus < 300);
                            if (!isSuccess) {
                                errorMessage = rawText || `HTTP ${responseStatus} error`;
                            }
                        } catch (fErr) {
                            responseStatus = 500;
                            rawText = fErr.message;
                            errorMessage = fErr.message;
                            isSuccess = false;
                        }
                    } else {
                        // Event-only dispatch handled by host app listener
                        isSuccess = true;
                        rawText = 'Handled by client-side event listener';
                    }

                    // 3. Report telemetry back to backend for audit logging & BLUF response
                    const execLatency = Date.now() - startTime;
                    try {
                        await ensureSession();
                        const reportRes = await fetch(`${apiHost}/api/v1/actions/report-browser-execution`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'Authorization': sessionToken ? `Bearer ${sessionToken}` : ''
                            },
                            body: JSON.stringify({
                                action_id: proposal.action_id,
                                session_id: activeSessionId,
                                parameters: proposal.parameters || {},
                                response_status: responseStatus,
                                response_data: responseJson,
                                raw_response: rawText,
                                execution_time_ms: execLatency
                            })
                        });
                        if (reportRes.ok) {
                            const reportData = await reportRes.json();
                            confirmationText = reportData.natural_confirmation;
                        }
                    } catch (_) {
                        // Keep optimistic confirmation if reporting fails
                    }

                    if (!confirmationText) {
                        confirmationText = isSuccess 
                            ? `Your request for **${proposal.display_name || proposal.name}** was completed successfully via your active session.`
                            : `Could not complete **${proposal.display_name || proposal.name}**: ${errorMessage}`;
                    }

                } else {
                    // --- SERVER WEBHOOK MODE (Backend HMAC) ---
                    await ensureSession();
                    const res = await fetch(`${apiHost}/api/v1/actions/execute`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': sessionToken ? `Bearer ${sessionToken}` : ''
                        },
                        body: JSON.stringify({
                            action_id: proposal.action_id,
                            parameters: proposal.parameters || {},
                            session_id: activeSessionId
                        })
                    });
                    const data = await res.json();
                    isSuccess = (res.ok && data.status === 'success');
                    confirmationText = data.natural_confirmation || '';
                    errorMessage = data.error_message || data.detail || 'Execution error encountered on server.';
                }

                if (isSuccess) {
                    card.innerHTML = `
                        <div class="pnp-action-status-success">
                            <span>✓</span> <span>${proposal.display_name || proposal.name} Executed Successfully</span>
                            ${isBrowserRelay ? '<span style="font-size: 9px; opacity: 0.8; margin-left: auto;">(Browser Session)</span>' : ''}
                        </div>
                        <div style="font-size: 12.5px; line-height: 1.45; margin-top: 6px;">
                            ${formatBotMessage(confirmationText)}
                        </div>
                    `;
                } else {
                    card.innerHTML = `
                        <div class="pnp-action-status-error">
                            <span>⚠️</span> <span>Action Failed</span>
                        </div>
                        <div style="font-size: 12px; margin-top: 6px; color: #f87171;">
                            ${errorMessage}
                        </div>
                    `;
                }
            } catch (err) {
                card.innerHTML = `
                    <div class="pnp-action-status-error">
                        <span>⚠️</span> <span>Network Connection Error</span>
                    </div>
                    <div style="font-size: 12px; margin-top: 6px; color: #f87171;">
                        ${err.message}
                    </div>
                `;
            }
            msgList.scrollTop = msgList.scrollHeight;
        };

        dismissBtn.onclick = () => {
            card.innerHTML = `<div style="font-size: 11px; opacity: 0.6; font-style: italic; padding: 4px;">Action dismissed.</div>`;
            msgList.scrollTop = msgList.scrollHeight;
        };

        container.appendChild(card);
        msgList.scrollTop = msgList.scrollHeight;
    }

    async function handleSend() {
        const text = inputField.value.trim();
        if (!text) return;
        inputField.value = '';
        if (chipsContainer) chipsContainer.style.display = 'none';

        // Add user message
        const userDiv = document.createElement('div');
        userDiv.className = 'pnp-msg pnp-msg-user';
        userDiv.innerText = text;
        msgList.appendChild(userDiv);
        msgList.scrollTop = msgList.scrollHeight;

        // Add assistant placeholder
        const asstDiv = document.createElement('div');
        asstDiv.className = 'pnp-msg pnp-msg-asst';
        
        const badgeContainer = document.createElement('div');
        const textContainer = document.createElement('div');
        textContainer.innerHTML = `<span style="opacity: 0.6;">${t.thinking}</span>`;
        
        asstDiv.appendChild(badgeContainer);
        asstDiv.appendChild(textContainer);
        msgList.appendChild(asstDiv);
        msgList.scrollTop = msgList.scrollHeight;

        try {
            await ensureSession();

            const res = await fetch(`${apiHost}/api/v1/chat/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': sessionToken ? `Bearer ${sessionToken}` : ''
                },
                body: JSON.stringify({ query: text, stream: true })
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                textContainer.innerHTML = `<span style="color: #f87171;">${errData.detail || 'Error processing request.'}</span>`;
                return;
            }

            const reader = res.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';
            let fullText = '';
            let currentMsgId = null;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop(); // keep partial trailing line

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    const jsonStr = line.slice(6).trim();
                    if (!jsonStr || jsonStr === '[DONE]') continue;

                    try {
                        const eventData = JSON.parse(jsonStr);

                        if (eventData.event === 'meta') {
                            const r = eventData.route || 'DIRECT';
                            let badgeClass = 'pnp-badge-sql';
                            if (r === 'RAG') badgeClass = 'pnp-badge-rag';
                            if (r === 'HYBRID') badgeClass = 'pnp-badge-hybrid';
                            if (r === 'GUARDRAIL_BLOCKED') badgeClass = 'pnp-badge-blocked';
                            if (r === 'ACTION_PROPOSAL' || r === 'ACTION_EXECUTED') badgeClass = 'pnp-badge-action';

                            const cached = eventData.cached ? '<span class="pnp-badge-route pnp-badge-cached">CACHED</span>' : '';
                            badgeContainer.innerHTML = `<span class="pnp-badge-route ${badgeClass}">${r}</span> ${cached}`;
                            textContainer.innerHTML = '';
                        } else if (eventData.event === 'action_proposal') {
                            renderActionProposalCard(asstDiv, eventData);
                        } else if (eventData.event === 'token') {
                            fullText += eventData.token;
                            textContainer.innerHTML = formatBotMessage(fullText);
                            msgList.scrollTop = msgList.scrollHeight;
                        } else if (eventData.event === 'done') {
                            currentMsgId = eventData.message_id;
                        }
                    } catch (e) {
                        // ignore malformed chunk
                    }
                }
            }

            // Append feedback bar with TTS audio button
            const fbBar = document.createElement('div');
            fbBar.className = 'pnp-feedback-bar';
            fbBar.innerHTML = `
                <div class="pnp-fb-actions">
                    <span style="font-size: 10.5px; color: ${cTextDim};">${t.helpful}</span>
                    <button class="pnp-fb-btn" title="Helpful"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path></svg></button>
                    <button class="pnp-fb-btn" title="Unhelpful"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3"></path></svg></button>
                </div>
                <button class="pnp-fb-btn pnp-tts-btn" title="Read Aloud" style="display: flex; align-items: center; gap: 4px;">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>
                    <span>${t.read}</span>
                </button>
            `;
            const upBtn = fbBar.querySelectorAll('.pnp-fb-btn')[0];
            const downBtn = fbBar.querySelectorAll('.pnp-fb-btn')[1];
            const ttsBtn = fbBar.querySelector('.pnp-tts-btn');

            upBtn.onclick = () => sendFeedback(currentMsgId, 1, upBtn);
            downBtn.onclick = () => sendFeedback(currentMsgId, -1, downBtn);
            ttsBtn.onclick = () => toggleSpeakText(fullText, ttsBtn);

            asstDiv.appendChild(fbBar);
            msgList.scrollTop = msgList.scrollHeight;

        } catch (err) {
            textContainer.innerHTML = '<span style="color: #f87171;">Connection error. Please verify backend is running.</span>';
        }
    }

    // --- Live Escalation to Human Support ---
    if (escalateBtn) {
        escalateBtn.onclick = async () => {
            if (!activeSessionId) {
                await ensureSession();
            }
            if (!activeSessionId) return;

            escalateBtn.disabled = true;
            escalateBtn.innerHTML = '<span>Connecting...</span>';

            // Add user bubble
            const userDiv = document.createElement('div');
            userDiv.className = 'pnp-msg pnp-msg-user';
            userDiv.innerText = 'Requesting Human Support...';
            msgList.appendChild(userDiv);
            msgList.scrollTop = msgList.scrollHeight;

            try {
                const res = await fetch(`${baseUrl}/api/v1/chat/escalate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: activeSessionId,
                        reason: 'User clicked Support button in widget',
                        user_contact: extUserId || 'Website Visitor'
                    })
                });
                const data = await res.json();
                
                const asstDiv = document.createElement('div');
                asstDiv.className = 'pnp-msg pnp-msg-asst';
                asstDiv.innerHTML = `
                    <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 6px;">
                        <span class="pnp-badge-route" style="background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4);">SUPPORT ALERT</span>
                    </div>
                    <div>${formatBotMessage(data.message || 'A live support representative has been notified and will follow up shortly.')}</div>
                `;
                msgList.appendChild(asstDiv);
                msgList.scrollTop = msgList.scrollHeight;

                escalateBtn.innerHTML = '<span>✓ Notified</span>';
                escalateBtn.style.background = 'rgba(34, 197, 94, 0.15)';
                escalateBtn.style.color = '#4ade80';
                escalateBtn.style.borderColor = 'rgba(34, 197, 94, 0.3)';
            } catch (err) {
                escalateBtn.disabled = false;
                escalateBtn.innerHTML = `<span>${t.support}</span>`;
            }
        };
    }

    sendBtn.onclick = handleSend;
    inputField.onkeydown = (e) => {
        if (e.key === 'Enter') handleSend();
    };
})();
