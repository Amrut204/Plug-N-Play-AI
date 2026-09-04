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
        {/* 🔌 PASTE YOUR Next.js <Script> TAG FROM AGENT STUDIO BELOW:        */}
        {/* Example:
        <Script
          src="https://plug-n-play-rag.onrender.com/static/pnp-widget.js"
          data-api-host="https://plug-n-play-rag.onrender.com"
          data-agent-id="YOUR_AGENT_ID"
          strategy="afterInteractive"
        />
        */}
        {/* ================================================================= */}
      </body>
    </html>
  );
}
