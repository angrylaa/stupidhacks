from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 47616


@dataclass
class WebTriggerRequest:
    payload: dict[str, Any]
    completed: threading.Event = field(default_factory=threading.Event)
    error: str | None = None
    completed_ok: bool = False

    def succeed(self) -> None:
        self.completed_ok = True
        self.completed.set()

    def fail(self, error: str) -> None:
        self.error = error
        self.completed.set()


class LoopbackBridge:
    def __init__(self, controller, host: str = BRIDGE_HOST, port: int = BRIDGE_PORT) -> None:
        self.controller = controller
        self.host = host
        self.port = port
        self.httpd: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.last_error: str | None = None

    def start(self) -> bool:
        if self.httpd is not None:
            return True

        handler = self._make_handler()
        try:
            self.httpd = ThreadingHTTPServer((self.host, self.port), handler)
        except OSError as exc:
            self.last_error = str(exc)
            self.httpd = None
            return False

        self.httpd.daemon_threads = True
        self.thread = threading.Thread(
            target=self.httpd.serve_forever,
            name="QuitTokLoopbackBridge",
            daemon=True,
        )
        self.thread.start()
        self.last_error = None
        return True

    def stop(self) -> None:
        if self.httpd is None:
            return
        self.httpd.shutdown()
        self.httpd.server_close()
        self.httpd = None
        self.thread = None

    def is_live(self) -> bool:
        return self.httpd is not None

    def _make_handler(self):
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            def do_OPTIONS(self):
                self._send_json(204, {"ok": True})

            def do_POST(self):
                if self.path != "/api/web-trigger":
                    self._send_json(404, {"ok": False, "error": "not-found"})
                    return

                length = int(self.headers.get("Content-Length", "0") or "0")
                raw = self.rfile.read(length) if length > 0 else b"{}"
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    self._send_json(400, {"ok": False, "error": "invalid-json"})
                    return

                if not isinstance(payload, dict):
                    self._send_json(400, {"ok": False, "error": "invalid-payload"})
                    return

                request = WebTriggerRequest(payload=payload)
                accepted, error = bridge.controller.submit_web_trigger_request(request)
                if not accepted:
                    self._send_json(503, {"ok": False, "error": error or "bridge-unavailable"})
                    return

                if not request.completed.wait(timeout=90):
                    self._send_json(504, {"ok": False, "error": "timeout"})
                    return

                if request.error:
                    self._send_json(503, {"ok": False, "error": request.error})
                    return

                self._send_json(200, {"ok": True, "completed": True})

            def _send_json(self, status: int, payload: dict[str, Any]) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(body)

            def log_message(self, format: str, *args) -> None:
                return

        return Handler
