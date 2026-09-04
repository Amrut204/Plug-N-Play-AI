// app/layout.tsx (Next.js 13/14/15 App Router)
import Script from 'next/script';
import './globals.css';

export const metadata = {
  title: 'OmniCloud — Next.js Enterprise Hub',
  description: 'Sample Next.js App Router website with embedded Plug-N-Play AI Assistant',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        {children}

        {/* ================================================================= */}
        {/* 🔌 JUST ADD THIS <Script> TAG INSIDE YOUR <body>:                  */}
        {/* ================================================================= */}
        <Script
  src="http://127.0.0.1:8000/static/pnp-widget.js"
  data-api-host="http://127.0.0.1:8000"
  data-agent-id="9b7f7f22-a73c-472a-8f14-0b97c6e0e63d"
  data-title="customersupport"
  data-primary-color="#09090b"
  data-accent-color="#318c52"
  data-bg-color="#09090b"
  data-header-bg="#121215"
  data-text-color="#f8fafc"
  data-user-bubble="#ffffff"
  data-position="bottom-right"
  data-widget-size="medium"
  data-btn-shape="circle"
  data-border-radius="24"
  data-theme="dark"
  data-welcome="Hello! I am your AI Assistant. Ask me anything or tap the mic to speak:"
  data-show-branding="true"
          strategy="afterInteractive"
        />
      </body>
    </html>
  );
}
