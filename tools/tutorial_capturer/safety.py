"""Strict sandbox isolation guards for `tutorial_capturer`.

Ensures automation ONLY runs when Anki's base directory resolves inside
`sandbox-anki` and never accesses personal `%APPDATA%\\Anki2` data.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from aqt import mw


def is_sandbox_profile() -> bool:
    """Return True only if Anki's base path resolves inside `sandbox-anki`."""
    if not mw or not mw.pm:
        return False
    base_str = str(Path(mw.pm.base).resolve()).lower()
    return "sandbox-anki" in base_str


def resolve_sandbox_path(file_path: str | Path) -> Path:
    """Resolve `file_path` strictly inside `mw.pm.base`."""
    base = Path(mw.pm.base).resolve()
    p = Path(file_path)
    resolved = p.resolve() if p.is_absolute() else (base / p).resolve()
    if resolved != base and base not in resolved.parents:
        raise ValueError(f"Refusing path outside sandbox-anki: {resolved}")
    return resolved


def addon_fingerprint() -> str:
    """Compute a short content hash of `tutorial_capturer/*.py` for hot-reuse checks."""
    pkg_dir = Path(__file__).resolve().parent
    h = hashlib.sha256()
    for fp in sorted(pkg_dir.glob("*.py")):
        h.update(fp.name.encode("utf-8"))
        h.update(fp.read_bytes())
    return h.hexdigest()[:12]
