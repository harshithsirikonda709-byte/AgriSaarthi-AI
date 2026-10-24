"""
Lightweight Farmer Voice Demo Web Server for AgriSaarthi AI.
Provides a browser interface with Web Speech API for Telugu & English speech-to-text
and text-to-speech, directly hooked into AgriSaarthi's ACP conversational decision logic.
Uses Python standard library (http.server) — zero external dependencies.
"""

import os
import sys
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agrisaarthi.chat_protocol import process_chat_message

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("agrisaarthi.ui_server")

PORT = int(os.getenv("AGRI_UI_PORT", "8080"))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")


class AgriFarmerUIHandler(BaseHTTPRequestHandler):
    """Handles static web requests and /api/chat decision calls."""

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            index_path = os.path.join(WEB_DIR, "index.html")
            if os.path.exists(index_path):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                with open(index_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "index.html not found")
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        if self.path == "/api/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                text = data.get("text", "")
                sender = data.get("sender", "farmer_voice_demo")

                logger.info(f"Received query from UI: '{text[:60]}...' (sender={sender})")
                reply = process_chat_message(text=text, sender=sender)

                response_bytes = json.dumps({"reply": reply}, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(response_bytes)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(response_bytes)
            except Exception as e:
                logger.exception(f"Error handling UI chat request: {e}")
                err_bytes = json.dumps({"error": str(e)}).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(err_bytes)
        else:
            self.send_error(404, "Endpoint Not Found")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        logger.debug("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))


def run_server(port=PORT):
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, AgriFarmerUIHandler)
    logger.info(f"🌾 AgriSaarthi Farmer Voice Web Interface running at: http://127.0.0.1:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping UI server...")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
