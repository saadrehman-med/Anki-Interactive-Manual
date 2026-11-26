"""Local-only HTTP server and Qt lifecycle hooks for `tutorial_capturer`."""

from __future__ import annotations

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from aqt import gui_hooks, mw
from aqt.qt import QTimer

from .actions import handle_action
from .qt_helpers import close_all_dialogs_and_menus, get_dispatcher
from .safety import is_sandbox_profile

HOST = "127.0.0.1"
PORT = int(os.environ.get("ANKI_TUTORIAL_CAPTURER_PORT", "8766"))

_SERVER: ThreadingHTTPServer | None = None


def _run_open_fields_dialog() -> dict[str, Any]:
    """Trigger modal FieldDialog asynchronously and poll from the HTTP thread."""
    disp = get_dispatcher()
    disp.call(lambda: handle_action({"action": "trigger_fields_dialog"}))
    deadline = time.monotonic() + 8.0
    found_res = None
    while time.monotonic() < deadline:
        time.sleep(0.08)
        check = disp.call(lambda: handle_action({"action": "find_visible_dialog", "title": "Fields for"}))
        if check.get("found"):
            found_res = check
            break
    if not found_res:
        raise TimeoutError("Timed out waiting for Fields dialog")
    time.sleep(0.15)
    return found_res


class _RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, status: int, body: dict[str, Any]) -> None:
        raw = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            try:
                res = get_dispatcher().call(lambda: handle_action({"action": "health"}))
                self._send_json(200, res)
            except Exception as exc:  # noqa: BLE001
                self._send_json(500, {"ok": False, "error": str(exc)})
            return
        if self.path.startswith("/inspect"):
            try:
                window = "main" if "window=main" in self.path else "active_dialog"
                res = get_dispatcher().call(lambda: handle_action({"action": "inspect_ui", "window": window}))
                self._send_json(200, res)
            except Exception as exc:  # noqa: BLE001
                self._send_json(500, {"ok": False, "error": str(exc)})
            return
        self._send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path not in ("/action", "/step"):
            self._send_json(404, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))

            if self.path == "/action" and payload.get("action") == "open_fields_dialog":
                res = _run_open_fields_dialog()
                self._send_json(200, {"ok": True, "data": res})
                return

            if self.path == "/step":
                pre_actions = payload.get("pre_actions") or []
                has_modal_fields = any(a.get("action") == "open_fields_dialog" for a in pre_actions)
                if not has_modal_fields:
                    res = get_dispatcher().call(
                        lambda: handle_action({"action": "execute_step", **payload}),
                        timeout=float(payload.get("timeout", 30.0)),
                    )
                    self._send_json(200, {"ok": True, "data": res})
                    return

                disp = get_dispatcher()
                for pre in pre_actions:
                    if pre.get("action") == "open_fields_dialog":
                        _run_open_fields_dialog()
                    else:
                        disp.call(lambda a=pre: handle_action(a))
                res = disp.call(
                    lambda: handle_action(
                        {
                            "action": "execute_step",
                            "window": payload.get("window", "active_dialog"),
                            **({"locate": payload["locate"]} if payload.get("locate") else {}),
                            "post_actions": payload.get("post_actions") or [],
                        }
                    ),
                    timeout=float(payload.get("timeout", 30.0)),
                )
                self._send_json(200, {"ok": True, "data": res})
                return

            res = get_dispatcher().call(
                lambda: handle_action(payload),
                timeout=float(payload.get("timeout", 20.0)),
            )
            self._send_json(200, {"ok": True, "data": res})
        except Exception as exc:  # noqa: BLE001
            self._send_json(500, {"ok": False, "error": str(exc)})


def start_server() -> None:
    global _SERVER
    if not is_sandbox_profile():
        print("[tutorial_capturer] Refusing to start outside sandbox-anki profile.")
        return
    if _SERVER is not None:
        return

    get_dispatcher()
    _SERVER = ThreadingHTTPServer((HOST, PORT), _RequestHandler)
    t = threading.Thread(target=_SERVER.serve_forever, daemon=True, name="tutorial-capturer-http")
    t.start()
    # Dismiss any add-on update prompts on startup so captures stay clean
    QTimer.singleShot(2000, close_all_dialogs_and_menus)
    print(f"[tutorial_capturer] Listening on http://{HOST}:{PORT} for profile={mw.pm.name!r}")


def stop_server() -> None:
    global _SERVER
    if _SERVER is not None:
        _SERVER.shutdown()
        _SERVER.server_close()
        _SERVER = None


def register_hooks() -> None:
    gui_hooks.main_window_did_init.append(start_server)
    gui_hooks.profile_will_close.append(stop_server)
