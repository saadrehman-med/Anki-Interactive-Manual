"""QtWebEngine DOM locators, readiness polling, and high-level Svelte controls."""

from __future__ import annotations

import json
import time
from typing import Any

from aqt import mw
from aqt.qt import QEventLoop, QPoint, QTimer, QWebEngineView, QWidget

from .qt_helpers import find_target_window, mark_opened, process_events


def find_webview(target_win: QWidget, web_spec: str = "auto") -> QWebEngineView | None:
    """Find the target QWebEngineView inside `target_win`."""
    if target_win is mw and web_spec in ("main", "deckBrowser", "overview", "reviewer"):
        if hasattr(mw, "web") and mw.web is not None:
            return mw.web
    if target_win is mw and web_spec == "toolbar":
        if hasattr(mw, "toolbar") and getattr(mw.toolbar, "web", None) is not None:
            return mw.toolbar.web
    if target_win is mw and web_spec == "bottom":
        if hasattr(mw, "bottomWeb") and mw.bottomWeb is not None:
            return mw.bottomWeb

    views = [v for v in target_win.findChildren(QWebEngineView) if v.isVisible()]
    if not views:
        views = target_win.findChildren(QWebEngineView)
    if not views:
        return None
    if web_spec == "auto":
        if target_win is mw and hasattr(mw, "web") and mw.web in views:
            return mw.web
        views.sort(key=lambda v: v.width() * v.height(), reverse=True)
        return views[0]
    for v in views:
        if web_spec.lower() in (v.objectName() or "").lower():
            return v
    return views[0]


def run_js_sync(web: QWebEngineView, script: str, timeout: float = 8.0) -> Any:
    """Execute JavaScript on QWebEnginePage synchronously from the Qt main thread."""
    loop = QEventLoop()
    box: dict[str, Any] = {}

    def _cb(res: Any) -> None:
        box["result"] = res
        loop.quit()

    timer = QTimer()
    timer.setSingleShot(True)

    def _on_timeout() -> None:
        box["timeout"] = True
        loop.quit()

    timer.timeout.connect(_on_timeout)
    timer.start(int(timeout * 1000))
    web.page().runJavaScript(script, _cb)
    loop.exec()
    timer.stop()

    if box.get("timeout"):
        raise TimeoutError("runJavaScript timed out")
    return box.get("result")


def wait_for_web(
    target_win: QWidget,
    selector: str | None = None,
    text: str | None = None,
    js_expr: str | None = None,
    web_spec: str = "auto",
    timeout: float = 5.0,
    interval_ms: int = 35,
) -> bool:
    """Poll a WebEngine view every `interval_ms` until predicate/element appears."""
    sel_json = json.dumps(selector)
    txt_json = json.dumps(text)
    custom_js = js_expr or "null"
    probe_js = f"""
    (() => {{
      const custom = {custom_js};
      if (custom !== null && custom !== undefined) return Boolean(custom);
      const sel = {sel_json};
      const txt = {txt_json};
      if (sel && txt) {{
        return Array.from(document.querySelectorAll(sel)).some(
          c => (c.innerText || c.textContent || '').trim().toLowerCase().includes(txt.toLowerCase())
            && c.offsetParent !== null
        );
      }}
      if (sel) {{
        const el = document.querySelector(sel);
        return Boolean(el && el.offsetParent !== null);
      }}
      if (txt) {{
        return Boolean(document.body && (document.body.innerText || '').toLowerCase().includes(txt.toLowerCase()));
      }}
      return Boolean(document.body && (document.body.innerText || '').trim().length > 10);
    }})()
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        web = find_webview(target_win, web_spec)
        if web is not None:
            try:
                if run_js_sync(web, probe_js, timeout=1.5):
                    process_events(45)
                    return True
            except Exception:  # noqa: BLE001
                pass
        process_events(interval_ms)
    return False


def wait_for_dialog_webview(timeout: float = 10.0) -> QWidget:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        process_events(45)
        cand = find_target_window("active_dialog")
        if cand is not mw:
            web = find_webview(cand)
            if web is not None:
                try:
                    ready = run_js_sync(
                        web,
                        "Boolean(document.body && (document.body.innerText || '').trim().length > 10)",
                        timeout=1.5,
                    )
                    if ready:
                        process_events(90)
                        return mark_opened(cand)
                except Exception:  # noqa: BLE001
                    pass
    raise RuntimeError("Timed out waiting for dialog webview")


def locate_web_element(
    target_win: QWidget,
    selector: str | None = None,
    text: str | None = None,
    js_expr: str | None = None,
    web_spec: str = "auto",
    scroll_into_view: bool = True,
    padding: int = 6,
) -> dict[str, Any] | None:
    """Locate a DOM element inside QtWebEngine and map to top-level window coords."""
    web = find_webview(target_win, web_spec)
    if web is None:
        raise RuntimeError(f"No QWebEngineView found in {target_win.windowTitle()!r}")

    sel_json = json.dumps(selector)
    txt_json = json.dumps(text)
    custom_js = js_expr or "null"
    scroll_js = "el.scrollIntoView({block: 'center', inline: 'nearest'});" if scroll_into_view else ""

    js = f"""
    (() => {{
      const selector = {sel_json};
      const textQuery = {txt_json};
      let el = {custom_js};

      if (!el) {{
        if (selector && textQuery) {{
          const candidates = Array.from(document.querySelectorAll(selector));
          el = candidates.find(c => (c.innerText || c.textContent || '').trim().toLowerCase().includes(textQuery.toLowerCase())) || null;
        }} else if (selector) {{
          el = document.querySelector(selector);
        }} else if (textQuery) {{
          const all = Array.from(document.querySelectorAll('button, a, label, input, select, summary, [role="button"], [role="switch"], h1, h2, h3, span, div'));
          el = all.find(c => {{
            const t = (c.innerText || c.textContent || '').trim();
            return t && t.toLowerCase() === textQuery.toLowerCase() && c.offsetParent !== null;
          }}) || all.find(c => {{
            const t = (c.innerText || c.textContent || '').trim();
            return t && t.toLowerCase().includes(textQuery.toLowerCase()) && c.offsetParent !== null;
          }}) || null;
        }}
      }}

      if (!el) return null;
      {scroll_js}
      const r = el.getBoundingClientRect();
      return {{
        left: r.left,
        top: r.top,
        width: r.width,
        height: r.height,
        tag: el.tagName,
        text: (el.innerText || '').trim().slice(0, 120)
      }};
    }})()
    """
    if scroll_into_view:
        run_js_sync(web, js)
        process_events(70)
    rect = run_js_sync(web, js)
    if not rect:
        return None

    origin = web.mapTo(target_win, QPoint(0, 0))
    zoom = float(web.zoomFactor())
    return {
        "x": origin.x() + float(rect["left"]) * zoom - padding,
        "y": origin.y() + float(rect["top"]) * zoom - padding,
        "width": float(rect["width"]) * zoom + padding * 2,
        "height": float(rect["height"]) * zoom + padding * 2,
        "tag": rect.get("tag"),
        "matched_text": rect.get("text"),
    }


def web_select(target_win: QWidget, label: str, value: str, web_spec: str = "auto") -> dict[str, Any]:
    """Select an option by text/value inside the smallest container matching `label`."""
    web = find_webview(target_win, web_spec)
    if web is None:
        raise RuntimeError("No QWebEngineView found")
    js = f"""
    (() => {{
      const lbl = {json.dumps(label)}.toLowerCase();
      const target = {json.dumps(value)}.toLowerCase();
      let best = null;
      let bestArea = Infinity;
      for (const el of document.querySelectorAll('div, label, tr')) {{
        const txt = (el.innerText || el.textContent || '').trim().toLowerCase();
        if (!txt.includes(lbl)) continue;
        const sel = el.querySelector('select');
        if (!sel) continue;
        const r = el.getBoundingClientRect();
        const area = r.width * r.height;
        if (r.width > 0 && r.height > 0 && area < bestArea) {{
          best = sel;
          bestArea = area;
        }}
      }}
      if (!best) return {{ ok: false, reason: 'select not found' }};
      const opt = Array.from(best.options).find(
        o => o.text.trim().toLowerCase() === target || o.value.trim().toLowerCase() === target
      ) || Array.from(best.options).find(o => o.text.trim().toLowerCase().includes(target));
      if (!opt) return {{ ok: false, reason: 'option not found' }};
      best.value = opt.value;
      best.dispatchEvent(new Event('change', {{ bubbles: true }}));
      return {{ ok: true, selected: opt.text.trim() }};
    }})()
    """
    res = run_js_sync(web, js)
    process_events(90)
    return res or {"ok": False}


def web_toggle(
    target_win: QWidget,
    label: str,
    checked: bool | None = None,
    web_spec: str = "auto",
) -> dict[str, Any]:
    """Toggle a checkbox/switch matching `label`, or set it explicitly to `checked`."""
    web = find_webview(target_win, web_spec)
    if web is None:
        raise RuntimeError("No QWebEngineView found")
    js = f"""
    (() => {{
      const lbl = {json.dumps(label)}.toLowerCase();
      const desired = {json.dumps(checked)};
      let best = null;
      let bestArea = Infinity;
      for (const el of document.querySelectorAll('div, label, tr')) {{
        const txt = (el.innerText || el.textContent || '').trim().toLowerCase();
        if (!txt.includes(lbl)) continue;
        const cb = el.querySelector('input[type="checkbox"], [role="switch"]');
        if (!cb) continue;
        const r = el.getBoundingClientRect();
        const area = r.width * r.height;
        if (r.width > 0 && r.height > 0 && area < bestArea) {{
          best = cb;
          bestArea = area;
        }}
      }}
      if (!best) return {{ ok: false, reason: 'toggle not found' }};
      const isOn = best.tagName === 'INPUT' ? Boolean(best.checked) : best.getAttribute('aria-checked') === 'true';
      if (desired === null || desired !== isOn) {{
        best.click();
      }}
      const after = best.tagName === 'INPUT' ? Boolean(best.checked) : best.getAttribute('aria-checked') === 'true';
      return {{ ok: true, checked: after }};
    }})()
    """
    res = run_js_sync(web, js)
    process_events(90)
    return res or {"ok": False}


def web_click(
    target_win: QWidget,
    selector: str | None = None,
    text: str | None = None,
    web_spec: str = "auto",
) -> dict[str, Any]:
    """Click a visible DOM element matching `selector` and/or `text`."""
    web = find_webview(target_win, web_spec)
    if web is None:
        raise RuntimeError("No QWebEngineView found")
    js = f"""
    (() => {{
      const sel = {json.dumps(selector)};
      const txt = {json.dumps(text)};
      let el = null;
      if (sel && txt) {{
        el = Array.from(document.querySelectorAll(sel)).find(
          c => (c.innerText || c.textContent || '').trim().toLowerCase().includes(txt.toLowerCase()) && c.offsetParent !== null
        ) || null;
      }} else if (sel) {{
        el = document.querySelector(sel);
      }} else if (txt) {{
        const low = txt.toLowerCase();
        const all = Array.from(document.querySelectorAll('button, a, summary, [role="button"], span, div'));
        el = all.find(c => (c.innerText || '').trim().toLowerCase() === low && c.offsetParent !== null)
          || all.find(c => (c.innerText || '').trim().toLowerCase().endsWith(low) && c.getBoundingClientRect().height < 64 && c.offsetParent !== null)
          || all.find(c => (c.innerText || '').trim().toLowerCase().includes(low) && c.getBoundingClientRect().height < 64 && c.offsetParent !== null)
          || null;
      }}
      if (!el) return {{ ok: false }};
      el.click();
      return {{ ok: true, clicked: (el.innerText || '').trim().slice(0, 80) }};
    }})()
    """
    res = run_js_sync(web, js)
    process_events(90)
    return res or {"ok": False}
