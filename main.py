import os
import sys
import subprocess
import time
import requests
import json
import base64
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

BOT_TOKEN = "8436257967:AAEsPJl35Ksw770gcLPd2tFq0SaEwcGj3Kc"
CHAT_ID = "8268185735"
PORT = 8081
CLOUDFLARED_PATH = "/root/botme/cloudflared"

AUTH_USER = "admin"
AUTH_PASS = "root"

def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except:
        pass

def kill_process(name):
    try:
        subprocess.run(["pkill", "-f", name], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    except:
        try:
            subprocess.run(["killall", name], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        except:
            pass

# ==================== HTML TERMINAL ====================
HTML_TERMINAL = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>WebTerm</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⬛</text></svg>">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #0a0a0a; color: #00ff00; font-family: 'Fira Code', 'Courier New', monospace; height: 100vh; display: flex; flex-direction: column; padding: 10px; }
        #header { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: #111; border-bottom: 1px solid #00ff00; border-radius: 5px 5px 0 0; flex-shrink: 0; }
        #header .title { color: #00ff00; font-weight: bold; font-size: 14px; }
        #header .cwd { color: #888; font-size: 12px; }
        #output { flex: 1; background: #0a0a0a; padding: 10px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; font-size: 14px; border: 1px solid #222; border-top: none; border-radius: 0 0 5px 5px; }
        #output .prompt { color: #00ff00; }
        #output .error { color: #ff4444; }
        #output .success { color: #44ff44; }
        #input-line { display: flex; align-items: center; padding: 8px 12px; background: #111; border: 1px solid #00ff00; border-top: none; border-radius: 0 0 5px 5px; flex-shrink: 0; margin-top: -1px; }
        #input-line .prompt { color: #00ff00; font-weight: bold; margin-right: 10px; font-size: 14px; }
        #cmd-input { flex: 1; background: transparent; color: #00ff00; border: none; outline: none; font-family: 'Fira Code', 'Courier New', monospace; font-size: 14px; padding: 4px 0; }
        #cmd-input::placeholder { color: #444; }
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #111; }
        ::-webkit-scrollbar-thumb { background: #00ff00; border-radius: 4px; }
        .status-bar { display: flex; justify-content: space-between; padding: 4px 12px; background: #111; color: #666; font-size: 11px; border-top: 1px solid #222; flex-shrink: 0; }
        .status-bar .online { color: #44ff44; }
    </style>
</head>
<body>
    <div id="header">
        <span class="title">⬛ WebTerm</span>
        <span class="cwd" id="cwd">/root/botme</span>
    </div>
    <div id="output"></div>
    <div id="input-line">
        <span class="prompt">$</span>
        <input id="cmd-input" type="text" placeholder="type command..." autofocus>
    </div>
    <div class="status-bar">
        <span>🔗 <span id="status" class="online">● Online</span></span>
        <span id="timestamp"></span>
    </div>

    <script>
        const output = document.getElementById('output');
        const input = document.getElementById('cmd-input');
        const cwdSpan = document.getElementById('cwd');
        const statusSpan = document.getElementById('status');
        const timestampSpan = document.getElementById('timestamp');
        let cwd = '/root/botme';
        let history = [];
        let historyIndex = -1;

        function appendOutput(text, type = '') {
            const div = document.createElement('div');
            div.textContent = text;
            if (type) div.className = type;
            output.appendChild(div);
            output.scrollTop = output.scrollHeight;
        }

        async function execCmd(cmd) {
            try {
                const resp = await fetch('/api/exec', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ cmd, cwd })
                });
                const data = await resp.json();
                if (data.output) {
                    const lines = data.output.split('\n');
                    lines.forEach(line => {
                        if (line.startsWith('❌') || line.startsWith('Error')) {
                            appendOutput(line, 'error');
                        } else if (line.startsWith('✅')) {
                            appendOutput(line, 'success');
                        } else {
                            appendOutput(line);
                        }
                    });
                }
                if (data.cwd) {
                    cwd = data.cwd;
                    cwdSpan.textContent = cwd;
                }
            } catch (e) {
                appendOutput('❌ ' + e.message, 'error');
            }
        }

        input.addEventListener('keydown', async (e) => {
            if (e.key === 'Enter') {
                const cmd = input.value.trim();
                if (!cmd) return;
                input.value = '';
                appendOutput('$ ' + cmd, 'prompt');
                history.push(cmd);
                historyIndex = history.length;
                if (cmd === 'clear') {
                    output.innerHTML = '';
                    return;
                }
                await execCmd(cmd);
                output.scrollTop = output.scrollHeight;
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (historyIndex > 0) {
                    historyIndex--;
                    input.value = history[historyIndex];
                }
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (historyIndex < history.length - 1) {
                    historyIndex++;
                    input.value = history[historyIndex];
                } else {
                    historyIndex = history.length;
                    input.value = '';
                }
            }
        });

        document.addEventListener('click', () => input.focus());
        input.focus();

        // Auto run 'ls' on load
        setTimeout(() => execCmd('ls -la'), 500);

        // Update timestamp
        setInterval(() => {
            const now = new Date();
            timestampSpan.textContent = now.toLocaleTimeString();
        }, 1000);
    </script>
</body>
</html>'''

# ==================== HTTP HANDLER ====================
class SecureExecHandler(BaseHTTPRequestHandler):
    def check_auth(self):
        auth_header = self.headers.get('Authorization')
        if not auth_header:
            return False
        if not auth_header.startswith('Basic '):
            return False
        try:
            encoded = auth_header.split(' ')[1]
            decoded = base64.b64decode(encoded).decode('utf-8')
            user, pwd = decoded.split(':', 1)
            return user == AUTH_USER and pwd == AUTH_PASS
        except:
            return False

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_TERMINAL.encode())
        elif self.path == '/favicon.ico':
            self.send_response(200)
            self.send_header('Content-Type', 'image/svg+xml')
            self.end_headers()
            self.wfile.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">⬛</text></svg>'.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if not self.check_auth():
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="Protected"')
            self.end_headers()
            self.wfile.write(b'{"error":"Unauthorized"}')
            return

        if self.path == '/api/exec':
            try:
                length = int(self.headers.get('Content-Length', 0))
                data = json.loads(self.rfile.read(length).decode())
                cmd = data.get('cmd', '')
                cwd = data.get('cwd', os.getcwd())

                if not cmd:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b'{"error":"Empty command"}')
                    return

                if os.path.exists(cwd):
                    os.chdir(cwd)

                proc = subprocess.run(
                    cmd, shell=True, cwd=os.getcwd(),
                    capture_output=True, text=True, timeout=30
                )
                output = proc.stdout or proc.stderr or "✅ Selesai"

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'output': output,
                    'cwd': os.getcwd()
                }).encode())

            except subprocess.TimeoutExpired:
                self.send_response(408)
                self.end_headers()
                self.wfile.write(b'{"error":"Timeout"}')
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args, **kwargs):
        pass

# ==================== TUNNEL ====================
def run_tunnel():
    kill_process("cloudflared")
    cmd = [CLOUDFLARED_PATH, "tunnel", "--url", f"http://localhost:{PORT}"]
    log = open("/tmp/cloudflared.log", "w")
    proc = subprocess.Popen(cmd, stdout=log, stderr=log)

    url = None
    for _ in range(30):
        time.sleep(1)
        try:
            resp = requests.get("http://localhost:4040/api/tunnels", timeout=2)
            if resp.status_code == 200:
                tunnels = resp.json().get('tunnels', [])
                if tunnels:
                    url = tunnels[0].get('public_url')
                    if url:
                        break
        except:
            pass
    return proc, url

# ==================== MAIN ====================
def main():
    # Download cloudflared
    if not os.path.exists(CLOUDFLARED_PATH):
        os.makedirs(os.path.dirname(CLOUDFLARED_PATH), exist_ok=True)
        subprocess.run(["curl", "-L", "-o", CLOUDFLARED_PATH,
                       "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"], check=True)
        os.chmod(CLOUDFLARED_PATH, 0o755)

    # Start tunnel
    cf_proc, tunnel_url = run_tunnel()

    # Send URL to Telegram
    if tunnel_url:
        send_telegram(
            f"✅ Web Terminal siap!\n"
            f"🔗 {tunnel_url}\n\n"
            f"📡 Endpoint: /api/exec\n"
            f"🔐 Auth: admin / root\n"
            f"📦 Payload: {{\"cmd\": \"perintah\"}}"
        )
    else:
        send_telegram("❌ Gagal mendapatkan URL Cloudflare Tunnel.")

    # Start web server
    server = HTTPServer(('0.0.0.0', PORT), SecureExecHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        cf_proc.terminate()
        server.server_close()

if __name__ == "__main__":
    main()