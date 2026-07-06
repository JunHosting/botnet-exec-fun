import os, sys, subprocess, time, requests, json, base64, socket, threading, re
from http.server import HTTPServer, BaseHTTPRequestHandler

BOT_TOKEN = "8570951657:AAEXSCkLBeuYQfs8VtT5nwU-VanqmffUbbI"
CHAT_ID = "8268185735"
PORT = 8081
CLOUDFLARED_PATH = "/root/botme/cloudflared"
AUTH_USER = "admin"
AUTH_PASS = "root"

def send_telegram(text):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      json={"chat_id": CHAT_ID, "text": text[:4000]}, timeout=10)
    except: pass

def log_telegram(text): send_telegram(f"[LOG] {text}")

def kill_process(name):
    try:
        subprocess.run(["pkill", "-f", name], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    except:
        try:
            subprocess.run(["killall", name], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        except:
            try:
                out = subprocess.check_output(["ps", "aux"], text=True)
                for line in out.splitlines():
                    if name in line and "grep" not in line:
                        subprocess.run(["kill", "-9", line.split()[1]], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            except: pass

def find_free_port(start):
    port = start
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('0.0.0.0', port)) != 0:
                return port
        port += 1

HTML_TERMINAL = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>WebTerm</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #0a0a0a; color: #00ff00; font-family: monospace; height: 100vh; display: flex; flex-direction: column; padding: 8px; overflow: hidden; }
        #output { flex: 1; background: #0a0a0a; padding: 8px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; font-size: 14px; border: 1px solid #00ff00; border-radius: 5px; margin-bottom: 8px; }
        #input-line { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }
        #cmd-input { flex: 1; background: #111; color: #00ff00; border: 1px solid #00ff00; border-radius: 4px; padding: 10px; font-family: monospace; font-size: 16px; outline: none; }
        #send-btn { background: #00ff00; color: #000; border: none; border-radius: 4px; padding: 10px 20px; font-weight: bold; font-size: 16px; cursor: pointer; }
        #send-btn:active { background: #00cc00; }
        .status { color: #666; font-size: 12px; margin-top: 4px; text-align: center; }
        @media (max-width: 480px) { #cmd-input { font-size: 16px; padding: 12px; } }
    </style>
</head>
<body>
    <div id="output">⬛ WebTerm v2.0\nType commands below...\n</div>
    <div id="input-line">
        <input id="cmd-input" type="text" placeholder="command..." autofocus>
        <button id="send-btn">⏎</button>
    </div>
    <div class="status">● Online</div>
    <script>
        (function() {
            const output = document.getElementById('output');
            const input = document.getElementById('cmd-input');
            const sendBtn = document.getElementById('send-btn');
            let cwd = '/root/botme';

            function append(text) {
                output.textContent += text + '\n';
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
                        append(data.output);
                    }
                    if (data.cwd) {
                        cwd = data.cwd;
                    }
                } catch (e) {
                    append('❌ ' + e.message);
                }
            }

            function handleCommand() {
                const cmd = input.value.trim();
                if (!cmd) return;
                append('$ ' + cmd);
                input.value = '';
                if (cmd === 'clear') {
                    output.textContent = '';
                    return;
                }
                execCmd(cmd);
            }

            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    handleCommand();
                }
            });

            sendBtn.addEventListener('click', handleCommand);
            input.focus();

            // Auto run ls
            setTimeout(() => execCmd('ls -la'), 500);
        })();
    </script>
</body>
</html>'''

class Handler(BaseHTTPRequestHandler):
    def check_auth(self):
        h = self.headers.get('Authorization')
        if not h or not h.startswith('Basic '): return False
        try:
            u,p = base64.b64decode(h.split(' ')[1]).decode().split(':',1)
            return u == AUTH_USER and p == AUTH_PASS
        except: return False

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
            self.wfile.write(b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">⬛</text></svg>')
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
                    raise Exception("Empty command")

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

    def log_message(self, *args, **kwargs): pass

def run_tunnel(port):
    kill_process("cloudflared")
    cmd = [CLOUDFLARED_PATH, "tunnel", "--url", f"http://localhost:{port}"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    url = None
    pattern = re.compile(r'https://[a-z0-9-]+\.trycloudflare\.com')
    def reader(pipe):
        nonlocal url
        for line in iter(pipe.readline, ''):
            if not url:
                match = pattern.search(line)
                if match: url = match.group(0)
        pipe.close()
    threading.Thread(target=reader, args=(proc.stdout,), daemon=True).start()
    threading.Thread(target=reader, args=(proc.stderr,), daemon=True).start()
    for _ in range(30):
        if url: break
        time.sleep(1)
    return proc, url

def main():
    send_telegram("🔄 Memulai Web Terminal...")
    port = find_free_port(PORT)
    if not os.path.exists(CLOUDFLARED_PATH):
        os.makedirs(os.path.dirname(CLOUDFLARED_PATH), exist_ok=True)
        subprocess.run(["curl", "-L", "-o", CLOUDFLARED_PATH,
                       "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"], check=True)
        os.chmod(CLOUDFLARED_PATH, 0o755)
    server = HTTPServer(('0.0.0.0', port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(2)
    cf, url = run_tunnel(port)
    if url:
        send_telegram(f"✅ Web Terminal siap!\n🔗 {url}\n\n🔐 Auth: admin/root\n📡 /api/exec")
    else:
        send_telegram("❌ Gagal dapat URL. Cek log.")
    try:
        while True:
            time.sleep(10)
            if cf.poll() is not None:
                send_telegram("⚠️ Tunnel mati, restart...")
                cf, url = run_tunnel(port)
                if url: send_telegram(f"✅ Restart: {url}")
    except KeyboardInterrupt:
        cf.terminate()
        server.shutdown()

if __name__ == "__main__":
    main()