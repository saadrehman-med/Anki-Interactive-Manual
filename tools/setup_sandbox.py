"""Bootstrap an isolated Anki Desktop sandbox in `sandbox-anki/` with DemoUser,
AnkiConnect, `tutorial_capturer`, and clean medical science sample flashcards.

NEVER touches `%APPDATA%\\Anki2` or any personal profile.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent.parent
SANDBOX_DIR = (ROOT / "sandbox-anki").resolve()
PID_FILE = SANDBOX_DIR / ".sandbox_pid"
PROFILE_NAME = "DemoUser"
ANKICONNECT_ADDON_ID = "2055492159"
ANKICONNECT_URL = "http://127.0.0.1:8765"
CAPTURER_URL = "http://127.0.0.1:8766"
ANKICONNECT_REPO = "https://github.com/FooSoft/anki-connect.git"

_HTTP = requests.Session()

SAMPLE_NOTES = [
    {
        "deckName": "Demo deck",
        "modelName": "Basic",
        "fields": {
            "Front": "What is the chemical symbol for Gold?",
            "Back": "Au (from the Latin word aurum).",
        },
        "tags": ["demo", "chemistry"],
    },
    {
        "deckName": "Demo deck",
        "modelName": "Basic",
        "fields": {
            "Front": "Which planet in the Solar System has the most confirmed moons?",
            "Back": "Saturn.",
        },
        "tags": ["demo", "astronomy"],
    },
    {
        "deckName": "Demo deck",
        "modelName": "Basic",
        "fields": {
            "Front": "What is the capital city of Japan?",
            "Back": "Tokyo.",
        },
        "tags": ["demo", "geography"],
    },
    {
        "deckName": "Demo deck",
        "modelName": "Basic",
        "fields": {
            "Front": "Who wrote the play 'Romeo and Juliet'?",
            "Back": "William Shakespeare.",
        },
        "tags": ["demo", "literature"],
    },
    {
        "deckName": "Demo deck",
        "modelName": "Cloze",
        "fields": {
            "Text": "The {{c1::mitochondrion}} is known as the {{c2::powerhouse}} of the cell.",
            "Back Extra": "Mitochondria generate most of the cell's supply of ATP.",
        },
        "tags": ["demo", "biology"],
    },
    {
        "deckName": "Demo deck",
        "modelName": "Cloze",
        "fields": {
            "Text": "Water boils at {{c1::100 °C}} ({{c2::212 °F}}) at standard atmospheric pressure.",
            "Back Extra": "1 atmosphere = 101.325 kPa.",
        },
        "tags": ["demo", "physics"],
    },
]


def find_anki_exe() -> Path:
    """Locate Anki Desktop executable on Windows; fail clearly if not found."""
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Anki" / "anki.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Anki" / "anki.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Anki" / "anki.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "AnkiProgramFiles" / ".venv" / "Scripts" / "anki.exe",
    ]
    for cand in candidates:
        if cand.is_file():
            return cand.resolve()
    which_anki = shutil.which("anki")
    if which_anki:
        return Path(which_anki).resolve()
    raise FileNotFoundError(
        "Anki Desktop (anki.exe) was not found in standard Windows paths or PATH. "
        "Please install Anki Desktop and re-run setup_sandbox.py."
    )


def assert_sandbox_isolation() -> None:
    """Verify sandbox path never overlaps %APPDATA%\\Anki2."""
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        real_anki2 = (Path(appdata) / "Anki2").resolve()
        if SANDBOX_DIR == real_anki2 or real_anki2 in SANDBOX_DIR.parents:
            raise RuntimeError(f"Refusing unsafe sandbox path: {SANDBOX_DIR}")
    if SANDBOX_DIR.name != "sandbox-anki":
        raise RuntimeError(f"Expected sandbox dir named 'sandbox-anki', got {SANDBOX_DIR}")


def init_demouser_profile(anki_exe: Path) -> None:
    """Pre-create DemoUser profile & English locale in sandbox-anki/prefs21.db."""
    app_packages = anki_exe.parent / "app_packages"
    if not app_packages.is_dir():
        # Check launcher layout if installed under AnkiProgramFiles
        alt = Path(os.environ.get("LOCALAPPDATA", "")) / "AnkiProgramFiles" / ".venv" / "Lib" / "site-packages"
        if alt.is_dir():
            app_packages = alt

    for sub in ("", "win32", "win32\\lib", "Pythonwin"):
        p = app_packages / sub if sub else app_packages
        if p.is_dir() and str(p) not in sys.path:
            sys.path.insert(0, str(p))
    pywin_sys = app_packages / "pywin32_system32"
    if hasattr(os, "add_dll_directory") and pywin_sys.is_dir():
        os.add_dll_directory(str(pywin_sys))

    import aqt.profiles  # noqa: PLC0415

    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    pm = aqt.profiles.ProfileManager(SANDBOX_DIR)
    pm.setupMeta()
    pm.setLang("en")
    if PROFILE_NAME not in pm.profiles():
        pm.create(PROFILE_NAME)
    pm.openProfile(PROFILE_NAME)
    pm.save()
    print(f"[sandbox] Initialized profile {PROFILE_NAME!r} in {SANDBOX_DIR}")


def install_ankiconnect() -> None:
    """Install AnkiConnect add-on into sandbox-anki/addons21/2055492159."""
    addons_dir = SANDBOX_DIR / "addons21"
    addons_dir.mkdir(parents=True, exist_ok=True)
    target = addons_dir / ANKICONNECT_ADDON_ID

    if not (target / "__init__.py").is_file():
        print("[sandbox] Downloading AnkiConnect from GitHub (FooSoft/anki-connect)...")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp) / "anki-connect"
            subprocess.run(
                ["git", "clone", "--depth", "1", ANKICONNECT_REPO, str(tmp_path)],
                check=True,
            )
            plugin_src = tmp_path / "plugin"
            if not plugin_src.is_dir():
                raise RuntimeError("AnkiConnect repository missing plugin/ directory")
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(plugin_src, target)

    # Configure AnkiConnect strictly on 127.0.0.1:8765
    cfg = {
        "apiKey": None,
        "apiLogPath": None,
        "ignoreOriginList": [],
        "webBindAddress": "127.0.0.1",
        "webBindPort": 8765,
        "webCorsOriginList": ["http://127.0.0.1"],
    }
    (target / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    meta = {"name": "AnkiConnect", "mod": 0, "config": cfg}
    (target / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"[sandbox] Configured AnkiConnect in {target}")


def install_tutorial_capturer() -> None:
    """Sync tools/tutorial_capturer into sandbox-anki/addons21/tutorial_capturer."""
    src = ROOT / "tools" / "tutorial_capturer"
    dst = SANDBOX_DIR / "addons21" / "tutorial_capturer"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    print(f"[sandbox] Installed tutorial_capturer into {dst}")


def source_capturer_fingerprint() -> str:
    """Compute a short content hash of `tools/tutorial_capturer/*.py`."""
    pkg_dir = ROOT / "tools" / "tutorial_capturer"
    h = hashlib.sha256()
    for fp in sorted(pkg_dir.glob("*.py")):
        h.update(fp.name.encode("utf-8"))
        h.update(fp.read_bytes())
    return h.hexdigest()[:12]


def probe_live_sandbox() -> dict[str, Any] | None:
    """Return `/health` payload if isolated sandbox AnkiConnect + capturer are alive."""
    try:
        r_ac = _HTTP.post(ANKICONNECT_URL, json={"action": "version", "version": 6}, timeout=1.0)
        if r_ac.status_code != 200 or r_ac.json().get("error") is not None:
            return None
        r_cap = _HTTP.get(f"{CAPTURER_URL}/health", timeout=1.0)
        if r_cap.status_code != 200:
            return None
        data = r_cap.json()
        if not data.get("ok"):
            return None
        base_resolved = str(Path(data["base"]).resolve()).lower()
        if "sandbox-anki" not in base_resolved or data.get("profile") != PROFILE_NAME:
            return None
        return data
    except requests.RequestException:
        return None


def stop_sandbox_if_running() -> bool:
    """Stop any previously detached sandbox Anki process tracked in `.sandbox_pid`."""
    if not PID_FILE.is_file():
        return False
    try:
        pid = int(PID_FILE.read_text(encoding="utf-8").strip())
    except ValueError:
        PID_FILE.unlink(missing_ok=True)
        return False

    stopped = False
    try:
        if os.name == "nt":
            res = subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            stopped = res.returncode == 0
        else:
            os.kill(pid, signal.SIGTERM)
            stopped = True
    except OSError:
        stopped = False

    PID_FILE.unlink(missing_ok=True)
    if stopped:
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline and probe_live_sandbox() is not None:
            time.sleep(0.15)
        print(f"[sandbox] Stopped previous sandbox Anki process (pid={pid}).")
    return stopped


def launch_sandbox_anki(anki_exe: Path, detached: bool = False) -> subprocess.Popen[bytes]:
    """Launch Anki strictly isolated to sandbox-anki and DemoUser."""
    env = os.environ.copy()
    env["ANKI_BASE"] = str(SANDBOX_DIR)
    env["ANKI_TUTORIAL_SANDBOX"] = "1"
    cmd = [str(anki_exe), "-b", str(SANDBOX_DIR), "-p", PROFILE_NAME]
    print(f"[sandbox] Launching isolated Anki: {cmd}")
    kwargs: dict[str, Any] = {"env": env}
    if detached:
        kwargs["stdin"] = subprocess.DEVNULL
        kwargs["stdout"] = subprocess.DEVNULL
        kwargs["stderr"] = subprocess.DEVNULL
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        else:
            kwargs["start_new_session"] = True
    proc = subprocess.Popen(cmd, **kwargs)
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(proc.pid), encoding="utf-8")
    return proc


def wait_for_sandbox_apis(timeout: float = 45.0) -> None:
    """Wait for both AnkiConnect and tutorial_capturer HTTP servers."""
    deadline = time.monotonic() + timeout
    ac_ready = False
    cap_ready = False
    while time.monotonic() < deadline:
        if not ac_ready:
            try:
                r = _HTTP.post(
                    ANKICONNECT_URL,
                    json={"action": "version", "version": 6},
                    timeout=1.5,
                )
                if r.status_code == 200 and r.json().get("error") is None:
                    ac_ready = True
            except requests.RequestException:
                pass
        if not cap_ready:
            try:
                r = _HTTP.get(f"{CAPTURER_URL}/health", timeout=1.5)
                if r.status_code == 200 and r.json().get("ok"):
                    data = r.json()
                    base_resolved = str(Path(data["base"]).resolve()).lower()
                    if "sandbox-anki" not in base_resolved or data.get("profile") != PROFILE_NAME:
                        raise RuntimeError(
                            f"SAFETY ABORT: Unexpected Anki base/profile: {data}"
                        )
                    cap_ready = True
            except requests.RequestException:
                pass
        if ac_ready and cap_ready:
            print("[sandbox] Both AnkiConnect (8765) and tutorial_capturer (8766) are ready.")
            return
        time.sleep(0.25)
    raise TimeoutError(
        f"Timed out waiting for sandbox APIs (AnkiConnect={ac_ready}, capturer={cap_ready})"
    )


def ankiconnect(action: str, **params: Any) -> Any:
    resp = _HTTP.post(
        ANKICONNECT_URL,
        json={"action": action, "version": 6, "params": params},
        timeout=10.0,
    )
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("error"):
        raise RuntimeError(f"AnkiConnect {action} failed: {payload['error']}")
    return payload.get("result")


def seed_demo_cards() -> None:
    """Idempotently ensure DemoUser has ONLY `Demo deck` with clean general cards."""
    # Remove any legacy non-Demo decks (e.g. MBBS*) so screenshots only ever show Demo deck
    all_decks: list[str] = ankiconnect("deckNames")
    legacy_decks = [d for d in all_decks if d not in ("Default", "Demo deck") and not d.startswith("Demo deck::")]
    for d in sorted(legacy_decks, key=len):
        try:
            ankiconnect("deleteDecks", decks=[d], cardsToo=True)
        except RuntimeError:
            pass
    if legacy_decks:
        print(f"[sandbox] Removed legacy decks: {legacy_decks}")

    decks = sorted({n["deckName"] for n in SAMPLE_NOTES})
    for d in decks:
        ankiconnect("createDeck", deck=d)

    sample_csv = SANDBOX_DIR / "sample-import.csv"
    if not sample_csv.is_file():
        sample_csv.write_text(
            "Question,Answer\nWhat is the capital of France?,Paris\nWhat is the chemical formula for water?,H2O\n",
            encoding="utf-8",
        )

    existing_ids = ankiconnect("findNotes", query='deck:"Demo deck" tag:demo')
    if len(existing_ids) < len(SAMPLE_NOTES):
        added = 0
        for note in SAMPLE_NOTES:
            try:
                ankiconnect(
                    "addNote",
                    note={
                        "deckName": note["deckName"],
                        "modelName": note["modelName"],
                        "fields": note["fields"],
                        "options": {"allowDuplicate": False},
                        "tags": note["tags"],
                    },
                )
                added += 1
            except RuntimeError:
                pass
        print(f"[sandbox] Seeded {added} clean Demo deck notes via AnkiConnect.")
    else:
        print(f"[sandbox] Demo notes already present ({len(existing_ids)} notes).")

    demo_apkg = SANDBOX_DIR / "demo-deck.apkg"
    if not demo_apkg.is_file():
        ankiconnect("exportPackage", deck="Demo deck", path=str(demo_apkg), includeSched=True)
        print(f"[sandbox] Exported sample package to {demo_apkg.name}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap isolated Anki tutorial sandbox.")
    parser.add_argument("--no-launch", action="store_true", help="Prepare files only without launching Anki.")
    parser.add_argument("--keep-open", action="store_true", help="Leave Anki running after seeding.")
    args = parser.parse_args()

    assert_sandbox_isolation()
    anki_exe = find_anki_exe()
    print(f"[sandbox] Found Anki Desktop: {anki_exe}")

    init_demouser_profile(anki_exe)
    install_ankiconnect()
    install_tutorial_capturer()

    if args.no_launch:
        return

    proc = launch_sandbox_anki(anki_exe)
    try:
        wait_for_sandbox_apis()
        seed_demo_cards()
        if not args.keep_open:
            print("[sandbox] Bootstrap verified. Stopping sandbox Anki cleanly...")
            proc.terminate()
            proc.wait(timeout=10)
    except Exception:
        proc.terminate()
        raise


if __name__ == "__main__":
    main()
