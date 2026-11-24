"""Sandboxed PyQt6 / QtWebEngine automation & capture add-on for Anki tutorials.

Runs ONLY when Anki is launched against the isolated `sandbox-anki` base folder.
"""

from __future__ import annotations

from .server import register_hooks

register_hooks()
