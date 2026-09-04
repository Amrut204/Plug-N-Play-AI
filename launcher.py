# launcher.py — Multi-Framework Sample Sites Unified Launcher & Hub
import os
import sys
import time
import socket
import threading
import subprocess
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Dict, Any

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLES_DIR = os.path.join(ROOT_DIR, "samplesites")

# Ports Configuration
SITES = [
    {
        "id": 1,
        "name": "HTML / WordPress / Webflow",
        "badge": "🌐 Pure HTML5",
        "tag": "Storefront (Aura Gear)",
        "port": 8081,
        "dir": os.path.join(SAMPLES_DIR, "1-html-wordpress"),
        "type": "static"
    },
    {
        "id": 2,
        "name": "React (TypeScript TSX)",
        "badge": "⚛️ React 18 + TS",
        "tag": "SaaS Cloud Analytics Dashboard",
        "port": 5173,
        "dir": os.path.join(SAMPLES_DIR, "2-react-tsx"),
        "type": "static"
    },
    {
        "id": 3,
        "name": "React (JavaScript JSX)",
        "badge": "⚛️ React 18 + JSX",
        "tag": "Private Banking Web App",
        "port": 5174,
        "dir": os.path.join(SAMPLES_DIR, "3-react-jsx"),
        "type": "static"
    },
    {
        "id": 4,
        "name": "Next.js (App Router)",
        "badge": "⚡ Next.js 14/15",
        "tag": "OmniCloud Serverless Hub",
        "port": 3001,
        "dir": os.path.join(SAMPLES_DIR, "4-nextjs-app-router"),
        "type": "static"
    },
    {
        "id": 5,
        "name": "Angular (TS Component)",
        "badge": "🅰️ Angular 17+",
        "tag": "Apex Institute Student ERP",
        "port": 4200,
        "dir": os.path.join(SAMPLES_DIR, "5-angular-ts", "src"),
        "type": "static"
    },
    {
        "id": 6,
        "name": "Vue 3 / Nuxt 3",
        "badge": "🟢 Vue 3 Composition",
        "tag": "MetroHealth Patient Portal",
        "port": 5175,
        "dir": os.path.join(SAMPLES_DIR, "6-vue3-nuxt3"),
        "type": "static"
    },
    {
        "id": 7,
        "name": "Svelte / SvelteKit",
        "badge": "🟠 Svelte 4/5",
        "tag": "Pacific Freight Logistics Hub",
        "port": 5176,
        "dir": os.path.join(SAMPLES_DIR, "7-svelte-kit"),
        "type": "static"
    },
    {
        "id": 8,
        "name": "Node.js Bridge (Zero-Knowledge)",
        "badge": "🟢 Node.js Express",
        "tag": "Private VPC Backend Bridge",
        "port": 3000,
        "dir": os.path.join(SAMPLES_DIR, "8-nodejs-bridge"),
        "type": "node_server"
    },
    {
        "id": 9,
        "name": "Python Bridge (FastAPI)",
        "badge": "🐍 Python FastAPI",
        "tag": "Firewalled SQL Bridge Server",
        "port": 5000,
        "dir": os.path.join(SAMPLES_DIR, "9-python-bridge"),
        "type": "python_server"
    },
    {
        "id": 10,
        "name": "PHP Bridge (Laravel)",
        "badge": "🐘 PHP / Laravel",
        "tag": "MySQL / SQLite Bridge Client",
        "port": 8082,
        "dir": os.path.join(SAMPLES_DIR, "10-php-laravel-bridge", "public"),
        "type": "static"
    },
]


from functools import partial

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


class CORSHTTPRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

    def log_message(self, format, *args):
        pass  # Suppress noisy HTTP logs


def start_static_server(directory: str, port: int):
    handler = partial(CORSHTTPRequestHandler, directory=directory)
    server = HTTPServer(('127.0.0.1', port), handler)
    print(f"  [Static Server] Serving {directory} at http://127.0.0.1:{port}")
    server.serve_forever()


def start_hub_server(port: int = 8080):
    html_content = generate_hub_html()
    hub_dir = os.path.join(SAMPLES_DIR, ".hub")
    os.makedirs(hub_dir, exist_ok=True)
    with open(os.path.join(hub_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_content)

    handler = partial(CORSHTTPRequestHandler, directory=hub_dir)
    server = HTTPServer(('127.0.0.1', port), handler)
    print("\n=======================================================")
    print(f">> MASTER LAUNCHPAD ACTIVE AT: http://127.0.0.1:{port}")
    print("=======================================================\n")
    server.serve_forever()


def generate_hub_html() -> str:
    cards_html = ""
    for s in SITES:
        cards_html += f"""
        <div class="site-card">
          <div class="card-top">
            <span class="badge">{s['badge']}</span>
            <span class="port-tag">Port {s['port']}</span>
          </div>
          <div class="card-title">{s['name']}</div>
          <div class="card-desc">{s['tag']}</div>
          <div class="card-actions">
            <a href="http://127.0.0.1:{s['port']}" target="_blank" class="btn-open">
              Open Sample Site ↗
            </a>
          </div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Plug-N-Play AI — Multi-Framework Sample Sites Launchpad</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #09090b;
      --surface: #121215;
      --surface-hover: #18181b;
      --border: rgba(255, 255, 255, 0.08);
      --border-hover: rgba(255, 255, 255, 0.2);
      --text: #f8fafc;
      --muted: #a1a1aa;
      --accent: #22c55e;
      --accent-blue: #38bdf8;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', -apple-system, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
      padding: 48px 24px;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    header {{
      text-align: center;
      margin-bottom: 48px;
      padding-bottom: 32px;
      border-bottom: 1px solid var(--border);
    }}
    .header-badge {{
      display: inline-block;
      font-size: 11px;
      font-weight: 700;
      color: var(--accent);
      background: rgba(34, 197, 94, 0.12);
      border: 1px solid rgba(34, 197, 94, 0.3);
      padding: 4px 12px;
      border-radius: 99px;
      margin-bottom: 14px;
    }}
    h1 {{ font-size: 36px; font-weight: 800; letter-spacing: -0.03em; margin-bottom: 12px; }}
    p.lead {{ color: var(--muted); font-size: 16px; max-width: 680px; margin: 0 auto; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
      gap: 20px;
    }}
    .site-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 24px;
      display: flex;
      flex-direction: column;
      transition: all 0.2s;
    }}
    .site-card:hover {{
      transform: translateY(-3px);
      border-color: var(--border-hover);
      box-shadow: 0 16px 36px -8px rgba(0, 0, 0, 0.6);
    }}
    .card-top {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }}
    .badge {{
      font-size: 11px;
      font-weight: 700;
      color: #ffffff;
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid var(--border);
      padding: 3px 9px;
      border-radius: 6px;
    }}
    .port-tag {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: var(--accent-blue);
      background: rgba(56, 189, 248, 0.1);
      padding: 2px 8px;
      border-radius: 4px;
    }}
    .card-title {{
      font-size: 18px;
      font-weight: 700;
      margin-bottom: 6px;
    }}
    .card-desc {{
      font-size: 13px;
      color: var(--muted);
      margin-bottom: 20px;
      flex: 1;
    }}
    .btn-open {{
      display: block;
      width: 100%;
      text-align: center;
      background: #ffffff;
      color: #09090b;
      text-decoration: none;
      font-weight: 700;
      font-size: 13px;
      padding: 10px;
      border-radius: 8px;
      transition: all 0.2s;
    }}
    .btn-open:hover {{
      background: #e4e4e7;
      transform: scale(1.02);
    }}
    .footer-bar {{
      margin-top: 60px;
      text-align: center;
      padding-top: 24px;
      border-top: 1px solid var(--border);
      color: var(--muted);
      font-size: 13px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <span class="header-badge">✓ 10 Sample Environments Active</span>
      <h1>Multi-Framework Verification Hub</h1>
      <p class="lead">Click any sample website below to test your Plug-N-Play AI widget or zero-knowledge backend bridge live in your browser.</p>
    </header>

    <div class="grid">
      {cards_html}
    </div>

    <div class="footer-bar">
      Plug-N-Play AI Master Studio running on <a href="http://127.0.0.1:8000" target="_blank" style="color: var(--accent); text-decoration: none; font-weight: 700;">http://127.0.0.1:8000</a>
    </div>
  </div>
</body>
</html>
"""


def main():
    threads = []

    # 1. Start Node.js Bridge Server
    node_dir = os.path.join(SAMPLES_DIR, "8-nodejs-bridge")
    if not is_port_in_use(3000):
        print("Starting Node.js Bridge on port 3000...")
        subprocess.Popen(["node", "server.js"], cwd=node_dir, shell=True)

    # 2. Start Python FastAPI Bridge Server
    python_dir = os.path.join(SAMPLES_DIR, "9-python-bridge")
    if not is_port_in_use(5000):
        print("Starting Python Bridge on port 5000...")
        subprocess.Popen([sys.executable, "main.py"], cwd=python_dir)

    # 3. Start Static HTTP Servers for all frontend sites
    for s in SITES:
        if s["type"] == "static":
            if not is_port_in_use(s["port"]):
                d = s["dir"]
                p = s["port"]
                t = threading.Thread(target=start_static_server, args=(d, p), daemon=True)
                t.start()
                threads.append(t)

    # 4. Start Central Master Launchpad (Port 8888 if 8080 is in use)
    time.sleep(1)
    hub_port = 8888 if is_port_in_use(8080) else 8080
    start_hub_server(port=hub_port)


if __name__ == "__main__":
    main()
