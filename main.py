#!/usr/bin/env python3
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

BOT_TOKEN = "8570951657:AAEXSCkLBeuYQfs8VtT5nwU-VanqmffUbbI"
CHAT_ID = "8268185735"
PORT = 8081
CLOUDFLARED_PATH = "/root/botme/cloudflared"
AUTH_USER = "admin"
AUTH_PASS = "root"

def send_telegram(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text[:4000]},
            timeout=10
        )
    except:
        pass

def log_telegram(text):
    send_telegram(f"[LOG] {text}")

def kill_process(name):
    try:
        subprocess.run(["pkill", "-f", name], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    except:
        pass
    try:
        subprocess.run(["killall", name], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    except:
        pass
    try:
        output = subprocess.check_output(["ps", "aux"], text=True)
        for line in output.splitlines():
            if name in line and "grep" not in line:
                pid = line.split()[1]
                subprocess.run(["kill", "-9", pid], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    except:
        pass

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
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>WebTerm</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        html,body{height:100%;overflow:hidden;background:#0a0a0a;color:#00ff00;font-family:'Courier New',monospace}
        body{display:flex;flex-direction:column;padding:8px;padding-bottom:60px}
        #header{display:flex;justify-content:space-between;padding:6px 12px;background:#111;border-bottom:1px solid #00ff00;border-radius:5px 5px 0 0;flex-shrink:0;font-size:13px}
        #header .cwd{color:#888}
        #output{flex:1;background:#0a0a0a;padding:8px;overflow-y:auto;white-space:pre-wrap;word-break:break-all;font-size:14px;border:1px solid #00ff00;border-top:none;border-radius:0 0 5px 5px;margin-bottom:0;-webkit-overflow-scrolling:touch}
        #input-line{position:fixed;bottom:0;left:0;right:0;display:flex;gap:8px;align-items:center;background:#0a0a0a;padding:8px;z-index:999;border-top:1px solid #00ff00}
        #cmd-input{flex:1;background:#111;color:#00ff00;border:1px solid #00ff00;border-radius:4px;padding:10px 12px;font-family:monospace;font-size:16px;outline:none;-webkit-appearance:none;appearance:none}
        #send-btn{background:#00ff00;color:#000;border:none;border-radius:4px;padding:10px 20px;font-weight:bold;font-size:16px;cursor:pointer;touch-action:manipulation}
        #send-btn:active{background:#00cc00}
        .status{color:#666;font-size:11px;text-align:center;flex-shrink:0;margin-top:4px}
        .status .online{color:#44ff44}
    </style>
</head>
<body>
    <div id="header">
        <span>⬛ WebTerm</span>
        <span class="cwd" id="cwd">/root/botme</span>
    </div>
    <div id="output">⬛ WebTerm v3.0 · Ready\nType 'help' or 'ls'\n</div>
    <div id="input-line">
        <input id="cmd-input" type="text" placeholder="command..." autofocus autocomplete="off" autocorrect="off" autocapitalize="none" spellcheck="false">
        <button id="send-btn">⏎</button>
    </div>
    <div class="status">● <span class="online">Online</span> &nbsp;|&nbsp; <span id="timestamp"></span></div>

    <script>
        (function() {
            const output = document.getElementById('output');
            const input = document.getElementById('cmd-input');
            const sendBtn = document.getElementById('send-btn');
            const cwdSpan = document.getElementById('cwd');
            const tsSpan = document.getElementById('timestamp');
            let cwd = '/root/botme';
            let history = [];
            let histIdx = -1;

            function append(text) {
                output.textContent += text + '\\n';
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
                    if (data.output) append(data.output);
                    if (data.cwd) {
                        cwd = data.cwd;
                        cwdSpan.textContent = cwd;
                    }
                } catch (e) {
                    append('❌ ' + e.message);
                }
            }

            function handleCommand() {
                const cmd = input.value.trim();
                if (!cmd) return;
                append('$ ' + cmd);
                history.push(cmd);
                histIdx = history.length;
                input.value = '';
                if (cmd === 'clear') {
                    output.textContent = '';
                    return;
                }
                execCmd(cmd);
            }

            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    handleCommand();
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    if (histIdx > 0) {
                        histIdx--;
                        input.value = history[histIdx];
                    }
                } else if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    if (histIdx < history.length - 1) {
                        histIdx++;
                        input.value = history[histIdx];
                    } else {
                        histIdx = history.length;
                        input.value = '';
                    }
                }
            });

            sendBtn.addEventListener('click', handleCommand);
            
            output.addEventListener('click', function() {
                input.focus();
            });

            setTimeout(function() { execCmd('ls -la'); }, 600);
            setInterval(function() {
                const now = new Date();
                tsSpan.textContent = now.toLocaleTimeString();
            }, 1000);

            window.addEventListener('resize', function() {
                input.focus();
            });
        })();
    </script>
</body>
</html>'''

class TermHandler(BaseHTTPRequestHandler):
    def check_auth(self):
        auth = self.headers.get('Authorization')
        if not auth or not auth.startswith('Basic '):
            return False
        try:
            encoded = auth.split(' ')[1]
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
            self.wfile.write(b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">\xe2\x96\xa0</text></svg>')
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
                    raise ValueError('Empty command')
                if os.path.exists(cwd):
                    os.chdir(cwd)
                proc = subprocess.run(cmd, shell=True, cwd=os.getcwd(), capture_output=True, text=True, timeout=60)
                output = proc.stdout or proc.stderr or '\u2705 Selesai'
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'output': output, 'cwd': os.getcwd()}).encode())
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

def run_tunnel(port):
    kill_process('cloudflared')
    cmd = [CLOUDFLARED_PATH, 'tunnel', '--url', f'http://localhost:{port}']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    url = None
    pattern = re.compile(r'https://[a-z0-9-]+\.trycloudflare\.com')

    def reader(pipe):
        nonlocal url
        for line in iter(pipe.readline, ''):
            if not url:
                match = pattern.search(line)
                if match:
                    url = match.group(0)
        pipe.close()

    threading.Thread(target=reader, args=(proc.stdout,), daemon=True).start()
    threading.Thread(target=reader, args=(proc.stderr,), daemon=True).start()

    for _ in range(30):
        if url:
            break
        time.sleep(1)

    return proc, url

def main():
    send_telegram('\U0001f504 Memulai Web Terminal...')
    port = find_free_port(PORT)

    if not os.path.exists(CLOUDFLARED_PATH):
        log_telegram('Mengunduh cloudflared...')
        os.makedirs(os.path.dirname(CLOUDFLARED_PATH), exist_ok=True)
        subprocess.run(['curl', '-L', '-o', CLOUDFLARED_PATH,
                        'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64'], check=True)
        os.chmod(CLOUDFLARED_PATH, 0o755)
        log_telegram('cloudflared terunduh.')
    else:
        log_telegram('cloudflared sudah ada.')

    server = HTTPServer(('0.0.0.0', port), TermHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    log_telegram(f'Web server berjalan di port {port}')

    time.sleep(2)
    cf_proc, tunnel_url = run_tunnel(port)

    if tunnel_url:
        send_telegram(
            f'\u2705 Web Terminal siap!\n'
            f'\U0001f517 {tunnel_url}\n\n'
            f'\U0001f510 Auth: admin / root\n'
            f'\U0001f4e1 Endpoint: /api/exec\n'
            f'\U0001f4a1 Command: ls, cd, npm, python, dll.'
        )
    else:
        send_telegram('\u274c Gagal mendapatkan URL Cloudflare Tunnel.')

    try:
        while True:
            time.sleep(15)
            if cf_proc.poll() is not None:
                log_telegram('\u26a0\ufe0f Tunnel mati, restart...')
                cf_proc, tunnel_url = run_tunnel(port)
                if tunnel_url:
                    send_telegram(f'\u2705 Tunnel restart: {tunnel_url}')
    except KeyboardInterrupt:
        log_telegram('\U0001f6d1 Shutdown...')
        cf_proc.terminate()
        server.shutdown()

if __name__ == '__main__':
    main()