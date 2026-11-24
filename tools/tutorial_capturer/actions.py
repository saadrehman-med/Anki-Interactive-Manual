"""Action registry for `tutorial_capturer` using declarative `@register_action`."""

from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Any, Callable

import aqt
from aqt import deckoptions, fields as aqt_fields, mw
from aqt.qt import (
    QApplication,
    QCheckBox,
    QComboBox,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPoint,
    QSpinBox,
    QTabWidget,
    QTimer,
    QWidget,
)

from .qt_helpers import (
    OPEN_MENUS,
    close_all_dialogs_and_menus,
    find_target_window,
    grab_window_png,
    locate_qt_widget,
    mark_opened,
    process_events,
    wait_for_dialog_visible,
)
from .safety import addon_fingerprint, resolve_sandbox_path
from .web_helpers import (
    find_webview,
    locate_web_element,
    run_js_sync,
    wait_for_dialog_webview,
    wait_for_web,
    web_click,
    web_select,
    web_toggle,
)

ActionHandler = Callable[[dict[str, Any]], dict[str, Any]]
_REGISTRY: dict[str, ActionHandler] = {}


def register_action(name: str) -> Callable[[ActionHandler], ActionHandler]:
    """Register an action handler under `name`."""

    def _decorator(fn: ActionHandler) -> ActionHandler:
        _REGISTRY[name] = fn
        return fn

    return _decorator


def handle_action(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("action") or "")
    handler = _REGISTRY.get(name)
    if handler is None:
        raise ValueError(f"Unknown action: {name!r}")
    return handler(payload)


def _locate_from_spec(win: QWidget, default_win_spec: str, locate_spec: dict[str, Any]) -> dict[str, Any] | None:
    mode = locate_spec.get("mode", "web")
    padding = int(locate_spec.get("padding", 6))
    if mode == "web":
        bbox = locate_web_element(
            win,
            selector=locate_spec.get("selector"),
            text=locate_spec.get("text"),
            js_expr=locate_spec.get("js"),
            web_spec=locate_spec.get("web", "auto"),
            scroll_into_view=bool(locate_spec.get("scroll", True)),
            padding=padding,
        )
    elif mode == "qt_widget":
        bbox = locate_qt_widget(
            win,
            object_name=locate_spec.get("object_name"),
            class_name=locate_spec.get("class_name"),
            text=locate_spec.get("text"),
            tab_text=locate_spec.get("tab_text"),
            padding=padding,
        )
    elif mode == "menu_item":
        res = handle_action(
            {
                "action": "open_menu_and_locate",
                "window": locate_spec.get("window", default_win_spec),
                "menu": locate_spec["menu"],
                "item": locate_spec["item"],
                "padding": padding,
            }
        )
        bbox = res["bbox"]
    else:
        raise ValueError(f"Unsupported locate mode: {mode!r}")

    if locate_spec.get("required", False) and bbox is None:
        raise RuntimeError(f"Required locator did not match any element: {locate_spec}")
    return bbox


@register_action("health")
def _health(_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "profile": mw.pm.name if mw and mw.pm else None,
        "base": str(mw.pm.base) if mw and mw.pm else None,
        "state": mw.state if mw else None,
        "code_hash": addon_fingerprint(),
    }


@register_action("inspect_qt")
def _inspect_qt(payload: dict[str, Any]) -> dict[str, Any]:
    win = find_target_window(payload.get("window", "active_dialog"))
    widgets = []
    for w in win.findChildren(QWidget):
        if not w.isVisible():
            continue
        txt = ""
        if hasattr(w, "text") and callable(w.text):
            try:
                txt = str(w.text())
            except Exception:  # noqa: BLE001
                pass
        widgets.append({"cls": w.metaObject().className(), "name": w.objectName(), "text": txt[:60]})
    return {"title": win.windowTitle(), "cls": win.metaObject().className(), "widgets": widgets[:80]}


@register_action("close_dialogs")
def _close_dialogs(_payload: dict[str, Any]) -> dict[str, Any]:
    return {"closed": close_all_dialogs_and_menus()}


@register_action("reset_to_decks")
def _reset_to_decks(_payload: dict[str, Any]) -> dict[str, Any]:
    close_all_dialogs_and_menus()
    mw.moveToState("deckBrowser")
    wait_for_web(mw, web_spec="bottom", selector="button", text="Create Deck", timeout=3.0)
    return {"state": mw.state}


@register_action("open_deck_overview")
def _open_deck_overview(payload: dict[str, Any]) -> dict[str, Any]:
    deck_name = payload["deck"]
    did = mw.col.decks.id_for_name(deck_name)
    if did is None:
        raise ValueError(f"Deck not found: {deck_name!r}")
    mw.col.decks.select(did)
    mw.moveToState("overview")
    wait_for_web(mw, web_spec="bottom", selector="button", text="Options", timeout=3.0)
    return {"deck": deck_name, "did": did, "state": mw.state}


@register_action("start_study_session")
def _start_study_session(payload: dict[str, Any]) -> dict[str, Any]:
    deck_name = payload.get("deck", "Demo deck")
    did = mw.col.decks.id_for_name(deck_name)
    if did is None:
        raise ValueError(f"Deck not found: {deck_name!r}")
    mw.col.decks.select(did)
    mw.moveToState("review")
    wait_for_web(mw, web_spec="bottom", selector="button", text="Show Answer", timeout=3.0)
    return {"deck": deck_name, "state": mw.state}


@register_action("show_answer")
def _show_answer(_payload: dict[str, Any]) -> dict[str, Any]:
    if mw.state == "review" and mw.reviewer is not None:
        mw.reviewer._showAnswer()
        wait_for_web(mw, web_spec="bottom", selector="button", text="Good", timeout=2.5)
    return {"state": mw.state}


@register_action("open_deck_options")
def _open_deck_options(payload: dict[str, Any]) -> dict[str, Any]:
    deck_name = payload.get("deck")
    if deck_name:
        did = mw.col.decks.id_for_name(deck_name)
        if did is None:
            raise ValueError(f"Deck not found: {deck_name!r}")
        mw.col.decks.select(did)
        deckoptions.display_options_for_deck_id(did)
    else:
        mw.onDeckConf()
    dlg = wait_for_dialog_webview()
    return {"title": dlg.windowTitle(), "width": dlg.width(), "height": dlg.height()}


@register_action("open_dialog")
def _open_dialog(payload: dict[str, Any]) -> dict[str, Any]:
    name = payload["name"]
    existing = {id(w) for w in QApplication.instance().topLevelWidgets() if w.isVisible()}
    if name == "AddCards":
        mw.onAddCard()
    elif name == "Browser":
        mw.onBrowse()
    elif name == "Preferences":
        mw.onPrefs()
    elif name == "AddonsDialog":
        aqt.dialogs.open("AddonsDialog", mw.addonManager)
    elif name == "FilteredDeck":
        mw.onCram()
    elif name == "Stats":
        mw.onStats()
        dlg = wait_for_dialog_webview()
        return {"title": dlg.windowTitle(), "width": dlg.width(), "height": dlg.height()}
    elif name == "Export":
        mw.onExport()
    elif name == "NoteTypes":
        mw.onNoteTypes()
    elif name == "Import":
        resolved = resolve_sandbox_path(str(payload["file_path"]))
        mw.handleImport(str(resolved))
        dlg = wait_for_dialog_webview()
        return {"title": dlg.windowTitle(), "width": dlg.width(), "height": dlg.height()}
    else:
        raise ValueError(f"Unknown dialog: {name!r}")
    dlg = wait_for_dialog_visible(exclude=existing)
    dlg.raise_()
    dlg.activateWindow()
    process_events(120)
    return {"title": dlg.windowTitle(), "width": dlg.width(), "height": dlg.height()}


@register_action("setup_add_cards")
def _setup_add_cards(payload: dict[str, Any]) -> dict[str, Any]:
    close_all_dialogs_and_menus()
    addcards = aqt.dialogs.open("AddCards", mw)
    mark_opened(addcards)
    addcards.show()
    addcards.raise_()
    addcards.activateWindow()
    process_events(200)
    deck_name = payload.get("deck", "Demo deck")
    model_name = payload.get("model", "Basic")
    did = mw.col.decks.id_for_name(deck_name)
    if did is not None:
        mw.col.decks.select(did)
        addcards.deck_chooser.selected_deck_id = did
    nt = mw.col.models.by_name(model_name)
    if nt is None:
        raise ValueError(f"Note type not found: {model_name!r}")
    mw.col.models.set_current(nt)
    addcards.notetype_chooser.selected_notetype_id = nt["id"]
    note = mw.col.new_note(nt)
    fields = payload.get("fields") or {}
    for k, v in fields.items():
        if k in note:
            note[k] = v
    addcards.editor.set_note(note)
    wait_for_web(addcards, js_expr="Boolean(document.querySelector('.note-editor button'))", timeout=8.0)
    process_events(120)
    return {"title": addcards.windowTitle(), "model": model_name, "deck": deck_name}


@register_action("open_card_layout")
def _open_card_layout(_payload: dict[str, Any]) -> dict[str, Any]:
    addcards = aqt.dialogs._dialogs.get("AddCards", [None, None])[1]
    if addcards is None:
        raise RuntimeError("AddCards dialog is not open")
    addcards.editor.onCardLayout()
    deadline = time.monotonic() + 8.0
    dlg = None
    while time.monotonic() < deadline:
        process_events(50)
        for w in reversed(QApplication.instance().topLevelWidgets()):
            if w is not mw and w.isVisible() and "card types" in (w.windowTitle() or "").lower():
                dlg = mark_opened(w)
                break
        if dlg is not None:
            break
    if dlg is None:
        raise RuntimeError("Timed out waiting for Card Types dialog")
    dlg.raise_()
    dlg.activateWindow()
    process_events(180)
    return {"title": dlg.windowTitle(), "width": dlg.width(), "height": dlg.height()}


@register_action("trigger_fields_dialog")
def _trigger_fields_dialog(_payload: dict[str, Any]) -> dict[str, Any]:
    addcards = aqt.dialogs._dialogs.get("AddCards", [None, None])[1]
    if addcards is None:
        raise RuntimeError("AddCards dialog is not open")
    nt = addcards.editor.note.note_type()
    QTimer.singleShot(0, lambda: aqt_fields.FieldDialog(mw, nt, parent=addcards))
    return {"triggered": True}


@register_action("find_visible_dialog")
def _find_visible_dialog(payload: dict[str, Any]) -> dict[str, Any]:
    title_sub = str(payload["title"]).lower()
    for w in reversed(QApplication.instance().topLevelWidgets()):
        if w is not mw and w.isVisible() and title_sub in (w.windowTitle() or "").lower():
            mark_opened(w)
            return {"found": True, "title": w.windowTitle(), "width": w.width(), "height": w.height()}
    return {"found": False}


@register_action("open_profiles_dialog")
def _open_profiles_dialog(_payload: dict[str, Any]) -> dict[str, Any]:
    existing = {id(w) for w in QApplication.instance().topLevelWidgets()}
    QTimer.singleShot(0, mw.showProfileManager)
    dlg = wait_for_dialog_visible(exclude=existing)
    return {"title": dlg.windowTitle(), "width": dlg.width(), "height": dlg.height()}


@register_action("open_sync_conflict_dialog")
def _open_sync_conflict_dialog(_payload: dict[str, Any]) -> dict[str, Any]:
    box = QMessageBox(mw)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle("Anki")
    box.setText(
        "There is a conflict between decks on this device and AnkiWeb. "
        "You must choose which version to keep:\n\n"
        "• Select Download from AnkiWeb to replace decks here with AnkiWeb's version. "
        "You will lose any changes you made on this device since your last sync.\n\n"
        "• Select Upload to AnkiWeb to overwrite AnkiWeb's versions with decks from this device, "
        "and delete any changes on AnkiWeb.\n\n"
        "Once the conflict is resolved, syncing will work as usual."
    )
    box.addButton("Upload to AnkiWeb", QMessageBox.ButtonRole.AcceptRole)
    box.addButton("Download from AnkiWeb", QMessageBox.ButtonRole.RejectRole)
    box.addButton("Cancel", QMessageBox.ButtonRole.DestructiveRole)
    box.show()
    QApplication.processEvents()
    mark_opened(box)
    return {"title": box.windowTitle(), "width": box.width(), "height": box.height()}


@register_action("click_qt_widget")
def _click_qt_widget(payload: dict[str, Any]) -> dict[str, Any]:
    win = find_target_window(payload.get("window", "active_dialog"))
    obj_name = payload.get("object_name")
    text_q = payload.get("text")
    for w in win.findChildren(QWidget):
        if not w.isVisible():
            continue
        if obj_name and w.objectName() != obj_name:
            continue
        if text_q and text_q.lower() not in (getattr(w, "text", lambda: "")() or "").lower():
            continue
        if hasattr(w, "click") and callable(w.click):
            w.click()
            process_events(120)
            return {"clicked": obj_name or text_q}
    raise ValueError(f"Clickable QWidget not found: object_name={obj_name!r}, text={text_q!r}")


@register_action("set_filtered_deck_fields")
def _set_filtered_deck_fields(payload: dict[str, Any]) -> dict[str, Any]:
    dlg = find_target_window("active_dialog")
    for le in dlg.findChildren(QLineEdit):
        if le.objectName() == "name" and "name" in payload:
            le.setText(str(payload["name"]))
        elif le.objectName() == "search" and "search" in payload:
            le.setText(str(payload["search"]))
    if "limit" in payload:
        spinboxes = [sb for sb in dlg.findChildren(QSpinBox) if sb.isVisible()]
        target_sb = next(
            (sb for sb in spinboxes if sb.objectName() == "limit"),
            spinboxes[0] if spinboxes else None,
        )
        if target_sb is not None:
            target_sb.setValue(int(payload["limit"]))
    if "order" in payload:
        needle = str(payload["order"]).lower()
        for cb in [c for c in dlg.findChildren(QComboBox) if c.isVisible()]:
            for i in range(cb.count()):
                if needle in cb.itemText(i).lower():
                    cb.setCurrentIndex(i)
                    break
    if "resched" in payload:
        for chk in dlg.findChildren(QCheckBox):
            if chk.objectName() == "resched":
                chk.setChecked(bool(payload["resched"]))
    process_events(100)
    return {"ok": True}


@register_action("ensure_deck")
def _ensure_deck(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload["name"])
    did = mw.col.decks.id(name)
    mw.col.decks.save(mw.col.decks.get(did))
    mw.reset()
    process_events(120)
    return {"deck": name, "did": did}


@register_action("delete_deck")
def _delete_deck(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload["name"])
    did = mw.col.decks.id_for_name(name)
    if did is not None:
        mw.col.decks.remove([did])
        mw.reset()
        process_events(120)
    return {"deleted": name, "did": did}


@register_action("setup_browser")
def _setup_browser(payload: dict[str, Any]) -> dict[str, Any]:
    browser = aqt.dialogs.open("Browser", mw)
    mark_opened(browser)
    process_events(200)
    search = payload.get("search")
    if search is not None:
        browser.search_for(search)
        process_events(180)
    if payload.get("select_first", True):
        model = browser.table._model
        if model.rowCount() > 0:
            idx = model.index(0, 0)
            browser.table._view.selectRow(0)
            browser.table._view.setCurrentIndex(idx)
            process_events(180)
    return {"title": browser.windowTitle(), "width": browser.width(), "height": browser.height()}


@register_action("select_preferences_tab")
def _select_preferences_tab(payload: dict[str, Any]) -> dict[str, Any]:
    tab_name = payload["tab"]
    found_tabs: list[str] = []
    for w in QApplication.instance().topLevelWidgets():
        if w is not mw and w.isVisible() and "preferences" in (w.windowTitle() or "").lower():
            for tw in w.findChildren(QTabWidget):
                for i in range(tw.count()):
                    t = tw.tabText(i)
                    found_tabs.append(t)
                    if tab_name.lower() in t.lower():
                        tw.setCurrentIndex(i)
                        mark_opened(w)
                        w.raise_()
                        w.activateWindow()
                        process_events(120)
                        return {"tab": t, "index": i}
    raise ValueError(f"Preferences tab not found: {tab_name!r} (available={found_tabs})")


@register_action("open_menu_and_locate")
def _open_menu_and_locate(payload: dict[str, Any]) -> dict[str, Any]:
    win = find_target_window(payload.get("window", "main"))
    menu_name = payload["menu"].replace("&", "").lower()
    action_query = payload["item"].replace("&", "").lower()
    menubar = win.menuBar()
    target_menu: QMenu | None = None
    target_bar_action = None
    for bar_act in menubar.actions():
        clean = bar_act.text().replace("&", "").strip().lower()
        if clean == menu_name:
            target_menu = bar_act.menu()
            target_bar_action = bar_act
            break
    if target_menu is None or target_bar_action is None:
        raise ValueError(f"Menu not found: {payload['menu']!r}")

    act_rect = menubar.actionGeometry(target_bar_action)
    popup_global = menubar.mapToGlobal(QPoint(act_rect.left(), act_rect.bottom()))
    target_menu.popup(popup_global)
    OPEN_MENUS.append(target_menu)
    process_events(140)

    win_global = win.mapToGlobal(QPoint(0, 0))
    for m_act in target_menu.actions():
        clean_item = m_act.text().replace("&", "").strip().lower()
        if action_query in clean_item:
            r = target_menu.actionGeometry(m_act)
            rel = target_menu.pos() - win_global
            padding = int(payload.get("padding", 4))
            return {
                "bbox": {
                    "x": float(rel.x() + r.left() - padding),
                    "y": float(rel.y() + r.top() - padding),
                    "width": float(r.width() + padding * 2),
                    "height": float(r.height() + padding * 2),
                    "item": m_act.text(),
                }
            }
    raise ValueError(f"Menu item {payload['item']!r} not found in {payload['menu']!r}")


@register_action("resize_window")
def _resize_window(payload: dict[str, Any]) -> dict[str, Any]:
    win = find_target_window(payload.get("window", "active_dialog"))
    win.resize(int(payload["width"]), int(payload["height"]))
    process_events(100)
    return {"width": win.width(), "height": win.height()}


@register_action("wait")
def _wait(payload: dict[str, Any]) -> dict[str, Any]:
    ms = int(payload.get("ms", 150))
    process_events(ms)
    return {"waited_ms": ms}


@register_action("wait_for")
def _wait_for(payload: dict[str, Any]) -> dict[str, Any]:
    """Poll until a web element/predicate or Qt widget is ready."""
    mode = payload.get("mode", "web")
    timeout = float(payload.get("timeout_ms", 5000)) / 1000.0
    win = find_target_window(payload.get("window", "active_dialog"))
    if mode == "web":
        ok = wait_for_web(
            win,
            selector=payload.get("selector"),
            text=payload.get("text"),
            js_expr=payload.get("js"),
            web_spec=payload.get("web", "auto"),
            timeout=timeout,
        )
        if not ok:
            raise TimeoutError(f"Timed out waiting for web target: {payload}")
        return {"ok": True, "mode": "web"}
    if mode == "qt_widget":
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            bbox = locate_qt_widget(
                win,
                object_name=payload.get("object_name"),
                class_name=payload.get("class_name"),
                text=payload.get("text"),
                tab_text=payload.get("tab_text"),
            )
            if bbox is not None:
                return {"ok": True, "mode": "qt_widget"}
            process_events(35)
        raise TimeoutError(f"Timed out waiting for qt_widget: {payload}")
    raise ValueError(f"Unsupported wait_for mode: {mode!r}")


@register_action("web_eval")
def _web_eval(payload: dict[str, Any]) -> dict[str, Any]:
    win = find_target_window(payload.get("window", "active_dialog"))
    web = find_webview(win, payload.get("web", "auto"))
    if web is None:
        raise RuntimeError("No QWebEngineView found")
    res = run_js_sync(web, payload["js"], timeout=float(payload.get("timeout", 8.0)))
    process_events(int(payload.get("settle_ms", 80)))
    return {"result": res}


@register_action("web_select")
def _web_select_action(payload: dict[str, Any]) -> dict[str, Any]:
    win = find_target_window(payload.get("window", "active_dialog"))
    return web_select(win, label=str(payload["label"]), value=str(payload["value"]), web_spec=payload.get("web", "auto"))


@register_action("web_toggle")
def _web_toggle_action(payload: dict[str, Any]) -> dict[str, Any]:
    win = find_target_window(payload.get("window", "active_dialog"))
    return web_toggle(
        win,
        label=str(payload["label"]),
        checked=payload.get("checked"),
        web_spec=payload.get("web", "auto"),
    )


@register_action("web_click")
def _web_click_action(payload: dict[str, Any]) -> dict[str, Any]:
    win = find_target_window(payload.get("window", "active_dialog"))
    return web_click(
        win,
        selector=payload.get("selector"),
        text=payload.get("text"),
        web_spec=payload.get("web", "auto"),
    )


@register_action("web_expand")
def _web_expand_action(payload: dict[str, Any]) -> dict[str, Any]:
    win = find_target_window(payload.get("window", "active_dialog"))
    return web_click(win, selector=payload.get("selector"), text=str(payload["text"]), web_spec=payload.get("web", "auto"))


@register_action("set_col_config")
def _set_col_config(payload: dict[str, Any]) -> dict[str, Any]:
    key = payload["key"]
    val = payload["value"]
    mw.col.set_config(key, val)
    return {"key": key, "value": val}


@register_action("locate")
def _locate(payload: dict[str, Any]) -> dict[str, Any]:
    win_spec = payload.get("window", "active_dialog")
    win = find_target_window(win_spec)
    bbox = _locate_from_spec(win, win_spec, payload)
    return {"bbox": bbox}


@register_action("capture")
def _capture(payload: dict[str, Any]) -> dict[str, Any]:
    win_spec = payload.get("window", "active_dialog")
    win = find_target_window(win_spec)
    bbox = None
    locate_spec = payload.get("locate")
    if locate_spec:
        bbox = _locate_from_spec(win, win_spec, locate_spec)

    png_bytes, dpr, pw, ph = grab_window_png(win)
    phys_bbox = None
    if bbox is not None:
        phys_bbox = {
            "x": round(bbox["x"] * dpr),
            "y": round(bbox["y"] * dpr),
            "width": round(bbox["width"] * dpr),
            "height": round(bbox["height"] * dpr),
            "meta": bbox,
        }

    return {
        "image_png_b64": base64.b64encode(png_bytes).decode("ascii"),
        "dpr": dpr,
        "logical_width": win.width(),
        "logical_height": win.height(),
        "physical_width": pw,
        "physical_height": ph,
        "bbox": phys_bbox,
        "window_title": win.windowTitle(),
    }


@register_action("execute_step")
def _execute_step(payload: dict[str, Any]) -> dict[str, Any]:
    """Run `pre_actions`, capture with `locate`, and run `post_actions` in one round-trip."""
    for pre in payload.get("pre_actions") or []:
        handle_action(pre)

    cap = handle_action(
        {
            "action": "capture",
            "window": payload.get("window", "active_dialog"),
            **({"locate": payload["locate"]} if payload.get("locate") else {}),
        }
    )

    for post in payload.get("post_actions") or []:
        handle_action(post)

    return cap
