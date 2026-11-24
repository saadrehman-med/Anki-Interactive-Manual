"""Qt6 main-thread marshalling, native widget locators, and window capture."""

from __future__ import annotations

import threading
import time
from typing import Any

import aqt
from aqt import mw
from aqt.qt import (
    QApplication,
    QBuffer,
    QDialog,
    QIODevice,
    QMenu,
    QObject,
    QPainter,
    QPoint,
    QTabWidget,
    QWidget,
    pyqtSignal,
)


class _MainThreadDispatcher(QObject):
    """Marshals arbitrary callables onto the Qt GUI thread safely."""

    invoke_signal = pyqtSignal(object)

    def __init__(self) -> None:
        super().__init__()
        self.invoke_signal.connect(self._run, aqt.qt.Qt.ConnectionType.QueuedConnection)

    def _run(self, payload: tuple[Any, threading.Event, dict[str, Any]]) -> None:
        fn, done_ev, box = payload
        try:
            box["result"] = fn()
        except Exception as exc:  # noqa: BLE001
            box["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            done_ev.set()

    def call(self, fn: Any, timeout: float = 20.0) -> Any:
        if QApplication.instance() is None:
            raise RuntimeError("QApplication not initialized")
        if threading.current_thread() is threading.main_thread():
            return fn()
        done_ev = threading.Event()
        box: dict[str, Any] = {}
        self.invoke_signal.emit((fn, done_ev, box))
        if not done_ev.wait(timeout=timeout):
            raise TimeoutError(f"Qt main thread call timed out after {timeout}s")
        if "error" in box:
            raise RuntimeError(box["error"])
        return box.get("result")


_DISPATCHER: _MainThreadDispatcher | None = None
OPEN_MENUS: list[QMenu] = []
_LAST_OPENED_WINDOW: QWidget | None = None


def get_dispatcher() -> _MainThreadDispatcher:
    global _DISPATCHER
    if _DISPATCHER is None:
        _DISPATCHER = _MainThreadDispatcher()
    return _DISPATCHER


def process_events(ms: int = 80) -> None:
    """Pump Qt events for `ms` milliseconds so UI & WebEngine paints settle."""
    deadline = time.monotonic() + (ms / 1000.0)
    app = QApplication.instance()
    while time.monotonic() < deadline:
        if app:
            app.processEvents()
        time.sleep(0.015)


def mark_opened(w: QWidget) -> QWidget:
    global _LAST_OPENED_WINDOW
    _LAST_OPENED_WINDOW = w
    return w


def close_all_dialogs_and_menus() -> int:
    """Close open popups and dialogs cleanly without modal save prompts."""
    global _LAST_OPENED_WINDOW
    _LAST_OPENED_WINDOW = None
    for m in OPEN_MENUS:
        try:
            m.hide()
            m.close()
        except Exception:  # noqa: BLE001
            pass
    OPEN_MENUS.clear()

    try:
        aqt.dialogs.closeAll()
    except Exception:  # noqa: BLE001
        pass

    app = QApplication.instance()
    closed = 0
    for w in list(app.topLevelWidgets()):
        if w is not mw and w.isVisible():
            if isinstance(w, QDialog):
                w.done(0)
            else:
                w.close()
            closed += 1
    process_events(120)
    try:
        mw.activateWindow()
    except Exception:  # noqa: BLE001
        pass
    return closed


def find_target_window(window_spec: str = "active_dialog") -> QWidget:
    """Resolve target top-level window ('main', 'active_dialog', or title substring)."""
    global _LAST_OPENED_WINDOW
    if window_spec == "main":
        return mw

    app = QApplication.instance()
    top_widgets = [w for w in app.topLevelWidgets() if w.isVisible() and not isinstance(w, QMenu)]

    if window_spec == "active_dialog":
        if _LAST_OPENED_WINDOW is not None:
            try:
                if _LAST_OPENED_WINDOW is not mw and _LAST_OPENED_WINDOW.isVisible():
                    return _LAST_OPENED_WINDOW
            except RuntimeError:
                _LAST_OPENED_WINDOW = None
        active = app.activeWindow()
        if active is not None and active is not mw and active.isVisible() and not isinstance(active, QMenu):
            return active
        dialogs = [w for w in top_widgets if w is not mw and isinstance(w, QDialog)]
        if dialogs:
            return dialogs[-1]
        others = [w for w in top_widgets if w is not mw and w.width() > 200 and w.height() > 150]
        if others:
            return others[-1]
        return mw

    for w in top_widgets:
        if window_spec.lower() in (w.windowTitle() or "").lower():
            return w
    return mw


def locate_qt_widget(
    target_win: QWidget,
    object_name: str | None = None,
    class_name: str | None = None,
    text: str | None = None,
    tab_text: str | None = None,
    padding: int = 6,
) -> dict[str, Any] | None:
    """Locate a native QWidget (or specific QTabBar tab) inside `target_win`."""
    if tab_text:
        for tw in target_win.findChildren(QTabWidget):
            if not tw.isVisible():
                continue
            tb = tw.tabBar()
            for i in range(tb.count()):
                if tab_text.lower() in tb.tabText(i).lower():
                    r = tb.tabRect(i)
                    origin = tb.mapTo(target_win, r.topLeft())
                    return {
                        "x": float(origin.x() - padding),
                        "y": float(origin.y() - padding),
                        "width": float(r.width() + padding * 2),
                        "height": float(r.height() + padding * 2),
                        "class_name": "QTabBarTab",
                        "tab_text": tb.tabText(i),
                    }
        return None

    for w in target_win.findChildren(QWidget):
        if not w.isVisible():
            continue
        if object_name and w.objectName() != object_name:
            continue
        if class_name and w.metaObject().className() != class_name:
            continue
        if text:
            w_text = ""
            if hasattr(w, "text") and callable(w.text):
                try:
                    w_text = str(w.text())
                except Exception:  # noqa: BLE001
                    w_text = ""
            clean_w = w_text.replace("&", "").strip().lower()
            if text.lower() not in clean_w:
                continue
        origin = w.mapTo(target_win, QPoint(0, 0))
        return {
            "x": float(origin.x() - padding),
            "y": float(origin.y() - padding),
            "width": float(w.width() + padding * 2),
            "height": float(w.height() + padding * 2),
            "class_name": w.metaObject().className(),
            "object_name": w.objectName(),
        }
    return None


def wait_for_dialog_visible(exclude: set[int] | None = None, timeout: float = 8.0) -> QWidget:
    exclude = exclude or set()
    deadline = time.monotonic() + timeout
    app = QApplication.instance()
    while time.monotonic() < deadline:
        process_events(45)
        for w in reversed(app.topLevelWidgets()):
            if w is not mw and not isinstance(w, QMenu) and w.isVisible() and id(w) not in exclude:
                if w.width() > 150 and w.height() > 100:
                    process_events(90)
                    return mark_opened(w)
    raise RuntimeError("Timed out waiting for dialog to appear")


def grab_window_png(target_win: QWidget) -> tuple[bytes, float, int, int]:
    """Capture `target_win` (+ any open menus) at full devicePixelRatio."""
    target_win.raise_()
    target_win.activateWindow()
    process_events(70)
    pixmap = target_win.grab()
    dpr = float(pixmap.devicePixelRatio()) if pixmap.devicePixelRatio() else 1.0

    visible_menus = [m for m in OPEN_MENUS if m.isVisible()]
    if visible_menus:
        painter = QPainter(pixmap)
        win_global = target_win.mapToGlobal(QPoint(0, 0))
        for m in visible_menus:
            m_pix = m.grab()
            m_pos = m.pos() - win_global
            painter.drawPixmap(m_pos, m_pix)
        painter.end()

    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(buf, "PNG")
    data = bytes(buf.data())
    buf.close()
    return data, dpr, pixmap.width(), pixmap.height()
