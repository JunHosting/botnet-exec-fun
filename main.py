import os
import sys
import subprocess
import time
import requests
import json
import base64
import socket
import threading
import re
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==================== KONFIGURASI ====================
BOT_TOKEN = "8570951657:AAEXSCkLBeuYQfs8VtT5nwU-VanqmffUbbI"
CHAT_ID = "8268185735"
PORT = 8081
CLOUDFLARED_PATH = "/root/botme/cloudflared"
AUTH_USER = "admin"
AUTH_PASS = "root"

# ==================== FUNGSI TELEGRAM ====================
def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": text[:4000]}, timeout=10)
    except Exception as e:
        print(f"Gagal kirim: {e}")

def log_telegram(text):
    send_telegram(f"[LOG] {text}")

# ==================== FUNGSI UTILITY ====================
def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('0.0.0.0', port)) == 0

def find_free_port(start_port):
    port = start_port
    while is_port_in_use(port):
        log_telegram(f"Port {port} sibuk, coba {port+1}")
        port += 1
    log_telegram(f"Port kosong: {port}")
    return port

def kill_process(name):
    try:
        subprocess.run(["pkill", "-f", name], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    except FileNotFoundError:
        try:
            subprocess.run(["killall", name], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        except FileNotFoundError:
            try:
                output = subprocess.check_output(["ps", "aux"], text=True)
                for line in output.splitlines():
                    if name in line and "grep" not in line:
                        pid = line.split()[1]
                        subprocess.run(["kill", "-9", pid], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            except:
                pass

# ==================== HTML TERMINAL ====================
HTML_TERMINAL = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>WebTerm</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm/css/xterm.min.css" />
    <style>
        body { margin: 0; padding: 10px; background: #0a0a0a; height: 100vh; overflow: hidden; }
        #terminal { height: 100%; width: 100%; border-radius: 8px; overflow: hidden; }
        .xterm { height: 100%; }
        .xterm-screen { padding: 8px; }
    </style>
</head>
<body>
    <div id="terminal"></div>
    <script src="https://cdn.jsdelivr.net/npm/xterm/lib/xterm.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit/lib/xterm-addon-fit.min.js"></script>
    <script>
        (function() {
            const term = new Terminal({
                cursorBlink: true,
                fontSize: 14,
                fontFamily: 'Courier New, monospace',
                theme: {
                    background: '#0a0a0a',
                    foreground: '#00ff00',
                    cursor: '#00ff00',
                    black: '#000000',
                    red: '#ff4444',
                    green: '#44ff44',
                    yellow: '#ffaa00',
                    blue: '#4444ff',
                    magenta: '#ff44ff',
                    cyan: '#44ffff',
                    white: '#ffffff'
                },
                scrollback: 1000,
                convertEol: true
            });

            const fitAddon = new FitAddon.FitAddon();
            term.loadAddon(fitAddon);
            term.open(document.getElementById('terminal'));
            fitAddon.fit();

            let cwd = '/root/botme';
            let currentLine = '';
            let prompt = '$ ';

            function updatePrompt() {
                term.write('\\r\\n' + prompt);
                currentLine = '';
            }

            term.write('\\x1b[1;32m⬛ WebTerm\\x1b[0m\\r\\n');
            term.write('\\x1b[2;37mType commands below\\x1b[0m\\r\\n\\r\\n');
            updatePrompt();

            async function execCmd(cmd) {
                try {
                    const resp = await fetch('/api/exec', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ cmd, cwd })
                    });
                    const data = await resp.json();
                    if (data.output) {
                        term.write('\\r\\n' + data.output);
                    }
                    if (data.cwd) {
                        cwd = data.cwd;
                    }
                } catch (e) {
                    term.write('\\r\\n\\x1b[1;31mError: ' + e.message + '\\x1b[0m');
                }
                updatePrompt();
            }

            term.onKey((e) => {
                const char = e.key;
                const code = e.domEvent.keyCode;

                if (code === 13) { // Enter
                    const cmd = currentLine.trim();
                    if (cmd) {
                        term.write('\\r\\n');
                        if (cmd === 'clear') {
                            term.clear();
                            term.write('\\x1b[1;32m⬛ WebTerm\\x1b[0m\\r\\n');
                            updatePrompt();
                            return;
                        }
                        execCmd(cmd);
                    } else {
                        term.write('\\r\\n');
                        updatePrompt();
                    }
                    return;
                }

                if (code === 8) { // Backspace
                    if (currentLine.length > 0) {
                        currentLine = currentLine.slice(0, -1);
                        term.write('\\b \\b');
                    }
                    return;
                }

                if (char && char.length === 1 && char.charCodeAt(0) >= 32) {
                    currentLine += char;
                    term.write(char);
                }
            });

            // Auto run ls
            setTimeout(() => {
                term.write('\\r\\n');
                execCmd('ls -la');
            }, 500);

            // Resize
            window.addEventListener('resize', () => fitAddon.fit());
        })();
    </script>
</body>
</html>'''

# ==================== HTTP HANDLER ====================
class SecureExecHandler(BaseHTTPRequestHandler):
    def check_auth(self):
        auth_header = self.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Basic '):
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

# ==================== CLOUDFLARED TUNNEL ====================
def run_tunnel(port):
    kill_process("cloudflared")
    log_telegram(f"Menjalankan tunnel ke port {port}")
    cmd = [CLOUDFLARED_PATH, "tunnel", "--url", f"http://localhost:{port}"]
    
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    
    url = None
    url_pattern = re.compile(r'https://[a-z0-9-]+\.trycloudflare\.com')
    
    def read_output(pipe, prefix):
        nonlocal url
        for line in iter(pipe.readline, ''):
            if line:
                send_telegram(f"[{prefix}] {line.strip()}")
                # Cari URL dari log
                if not url:
                    match = url_pattern.search(line)
                    if match:
                        url = match.group(0)
                        log_telegram(f"✅ URL ditemukan dari log: {url}")
        pipe.close()

    threading.Thread(target=read_output, args=(proc.stdout, "STDOUT"), daemon=True).start()
    threading.Thread(target=read_output, args=(proc.stderr, "STDERR"), daemon=True).start()

    # Tunggu sampe URL ketemu (maks 30 detik)
    for _ in range(30):
        if url:
            break
        time.sleep(1)
    
    return proc, url

# ==================== MAIN ====================
def main():
    send_telegram("🔄 Memulai Web Terminal...")
    
    port = find_free_port(PORT)
    
    # Download cloudflared
    if not os.path.exists(CLOUDFLARED_PATH):
        log_telegram("Mengunduh cloudflared...")
        os.makedirs(os.path.dirname(CLOUDFLARED_PATH), exist_ok=True)
        subprocess.run(["curl", "-L", "-o", CLOUDFLARED_PATH,
                       "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"], check=True)
        os.chmod(CLOUDFLARED_PATH, 0o755)
        log_telegram("cloudflared terunduh.")
    else:
        log_telegram("cloudflared sudah ada.")

    # START WEB SERVER DULU
    log_telegram(f"Menjalankan web server di port {port}")
    server = HTTPServer(('0.0.0.0', port), SecureExecHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(2)
 
    # BARU START TUNNEL
    cf_proc, tunnel_url = run_tunnel(port)

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

    # JAGA PROSES TETEP JALAN
    try:
        while True:
            time.sleep(10)
            if cf_proc.poll() is not None:
                log_telegram("⚠️ Tunnel mati, restart...")
                cf_proc, tunnel_url = run_tunnel(port)
                if tunnel_url:
                    send_telegram(f"✅ Tunnel restart: {tunnel_url}")
    except KeyboardInterrupt:
        pass
    finally:
        cf_proc.terminate()
        server.shutdown()

if __name__ == "__main__":
    main()