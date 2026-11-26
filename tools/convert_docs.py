"""Convert Mintlify Anki Manual docs (`docs-site/manual`) into Quartz-ready Markdown in `docs/`.

Only processes the Anki Manual (`manual/`) + `media/` assets, preserves original
prose verbatim, and routes any links outside `manual/` (such as `/faqs/...`,
`/addons/...`, `/ankimobile/...`, `/releases/...`, `/translators/...`) to the
official documentation site at `https://docs.ankiweb.net`.
"""

from __future__ import annotations

import posixpath
import re
import shutil
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "_tmp_anki" / "docs-site"
DST = ROOT / "docs"

OFFICIAL_DOCS_BASE = "https://docs.ankiweb.net"

ADMONITION_MAP = {
    "Note": "note",
    "Warning": "warning",
    "Info": "info",
    "Danger": "danger",
    "Tip": "tip",
}

STANDARD_HTML_TAGS = {
    "a",
    "b",
    "br",
    "code",
    "details",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "img",
    "kbd",
    "li",
    "ol",
    "p",
    "pre",
    "rb",
    "rt",
    "ruby",
    "script",
    "source",
    "span",
    "strong",
    "sub",
    "summary",
    "sup",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "u",
    "ul",
    "video",
}


def split_code_segments(text: str) -> list[tuple[bool, str]]:
    """Split markdown into (is_code, segment) chunks preserving fenced & inline code."""
    pattern = re.compile(r"(```[\s\S]*?```|`[^`\n]+`)")
    parts: list[tuple[bool, str]] = []
    pos = 0
    for m in pattern.finditer(text):
        if m.start() > pos:
            parts.append((False, text[pos : m.start()]))
        parts.append((True, m.group(0)))
        pos = m.end()
    if pos < len(text):
        parts.append((False, text[pos:]))
    return parts


def convert_admonitions(text: str) -> str:
    """Convert <Note>...</Note>, <Warning>...</Warning>, etc. into Obsidian callouts."""
    tag_re = re.compile(
        r"<(Note|Warning|Info|Danger|Tip)\b[^>]*>([\s\S]*?)</\1>",
        re.MULTILINE,
    )

    def repl(match: re.Match[str]) -> str:
        tag = match.group(1)
        inner = textwrap.dedent(match.group(2)).strip()
        callout_type = ADMONITION_MAP[tag]
        lines = inner.splitlines()
        out_lines = [f"> [!{callout_type}]"]
        for line in lines:
            if line.strip() == "---":
                if out_lines and out_lines[-1].strip() != ">":
                    out_lines.append(">")
                out_lines.append("> ---")
            elif line.strip() == "":
                out_lines.append(">")
            else:
                out_lines.append(f"> {line}")
        return "\n".join(out_lines)

    return tag_re.sub(repl, text)


def resolve_doc_target(raw_url: str, rel_dir: str, existing_manual_slugs: set[str]) -> str:
    """Resolve manual links relatively; route non-manual official links to docs.ankiweb.net."""
    if raw_url.startswith(("http://", "https://", "mailto:", "#")):
        return raw_url

    if "#" in raw_url:
        path_part, anchor = raw_url.split("#", 1)
        anchor_suffix = f"#{anchor}"
    else:
        path_part, anchor_suffix = raw_url, ""

    # Strip Mintlify query params like ?highlight=FSRS
    if "?" in path_part:
        path_part = path_part.split("?", 1)[0]

    if path_part in ("", "."):
        return anchor_suffix or "."

    # Image / media asset inside docs/media/
    if path_part.startswith("/media/"):
        target_from_docs = path_part.lstrip("/")
        return posixpath.relpath(target_from_docs, rel_dir or ".") + anchor_suffix

    # Upstream typo `/media` -> `manual/media`
    if path_part == "/media":
        return posixpath.relpath("manual/media", rel_dir or ".") + anchor_suffix

    if path_part.startswith("/"):
        clean = path_part.lstrip("/").rstrip("/")
        if clean.endswith(".mdx"):
            clean = clean[:-4]
        elif clean.endswith(".md"):
            clean = clean[:-3]

        if clean.startswith("manual/"):
            if f"{clean}/intro" in existing_manual_slugs and clean not in existing_manual_slugs:
                clean = f"{clean}/intro"
            rel = posixpath.relpath(clean, rel_dir or ".")
            return rel + anchor_suffix

        # Non-manual official documentation links -> preserve to official docs site
        return f"{OFFICIAL_DOCS_BASE}/{clean}{anchor_suffix}"

    # Relative path inside manual/
    if path_part.endswith(".mdx"):
        path_part = path_part[:-4]
    elif path_part.endswith(".md"):
        path_part = path_part[:-3]
    if path_part == "./":
        return anchor_suffix or "./intro"
    return path_part + anchor_suffix


def escape_non_html_tags(text: str) -> str:
    """Escape placeholder angle-bracket tokens like <deck> or <https://...> outside code."""
    tag_re = re.compile(r"<(/?)([A-Za-z][A-Za-z0-9_-]*)([^>]*)>")

    def repl(match: re.Match[str]) -> str:
        slash, name, rest = match.group(1), match.group(2), match.group(3)
        if name.lower() in STANDARD_HTML_TAGS:
            return match.group(0)
        if name.lower() in ("http", "https"):
            url = f"{name}{rest}"
            return f"[{url}]({url})"
        return f"&lt;{slash}{name}{rest}&gt;"

    return tag_re.sub(repl, text)


def convert_markdown(content: str, rel_path: Path, existing_manual_slugs: set[str]) -> str:
    """Transform a single Mintlify manual MDX file into Quartz Markdown."""
    rel_dir = rel_path.parent.as_posix()
    if rel_dir == ".":
        rel_dir = ""

    fm = ""
    body = content
    if content.startswith("---\n"):
        end = content.find("\n---\n", 4)
        if end != -1:
            fm = content[: end + 5]
            body = content[end + 5 :]

    segments = split_code_segments(body)
    converted_parts: list[str] = []

    angle_link_re = re.compile(r"(!?\[[^\]]*\])\(<(https?://[^>\s]+)>\)")
    link_re = re.compile(r"(!?\[[^\]]*\])\(([^)\s]+)\)")
    heading_id_re = re.compile(r"^(#{1,6}\s+.*?)\s*\{#[^}]+\}\s*$", re.MULTILINE)
    src_re = re.compile(r'(<img\b[^>]*\bsrc=["\'])(/media/[^"\']+)(["\'])')

    for is_code, seg in segments:
        if is_code:
            converted_parts.append(seg)
            continue
        seg = convert_admonitions(seg)
        seg = heading_id_re.sub(r"\1", seg)
        seg = angle_link_re.sub(
            lambda m: f"{m.group(1)}({m.group(2).replace('(', '%28').replace(')', '%29')})",
            seg,
        )
        seg = link_re.sub(
            lambda m: f"{m.group(1)}({resolve_doc_target(m.group(2), rel_dir, existing_manual_slugs)})",
            seg,
        )
        seg = src_re.sub(
            lambda m: f"{m.group(1)}{posixpath.relpath(m.group(2).lstrip('/'), rel_dir or '.')}{m.group(3)}",
            seg,
        )
        seg = escape_non_html_tags(seg)
        converted_parts.append(seg)

    return fm + "".join(converted_parts)


def collect_manual_slugs() -> set[str]:
    slugs: set[str] = set()
    manual_dir = SRC / "manual"
    for fp in manual_dir.rglob("*"):
        if fp.is_file() and fp.suffix in (".mdx", ".md"):
            rel = fp.relative_to(SRC).with_suffix("")
            slugs.add(rel.as_posix())
    return slugs


def write_vanilla_index() -> None:
    """Write a clean, notice-free landing page focused strictly on the Anki Manual."""
    index_md = """---
title: "Anki Manual"
---

Welcome to the Anki Manual for the desktop application.

- **[Introduction](manual/intro)** — Overview, mobile clients, and translations.
- **[Getting Started](manual/getting-started)** — Core concepts: decks, cards, notes, and card types.
- **[Studying](manual/studying)** — Reviewing cards, answer buttons, and keyboard shortcuts.
- **[Adding / Editing](manual/editing)** — Creating notes, Cloze deletions, and Image Occlusion.
- **[Browsing](manual/browsing)** & **[Searching](manual/searching)** — Finding, filtering, flagging, and managing cards.
- **[Deck Options](manual/deck-options)** — Daily limits, presets, and FSRS scheduling.
- **[Filtered Decks & Cramming](manual/filtered-decks)** — Temporary study and cramming decks.
- **[Card Templates](manual/templates/intro)** — Fields, card generation, and styling.
- **[Statistics](manual/stats)** — Review graphs, card info, and intervals.
- **[Importing](manual/importing/intro)** & **[Exporting](manual/exporting)** — `.apkg` packages and text/CSV files.
- **[Backups](manual/backups)** & **[Managing Files](manual/files)** — Automatic backups and checking the database.
- **[Add-ons](manual/addons)**, **[Preferences](manual/preferences)** & **[Profiles](manual/profiles)** — Extending and configuring Anki.

Other official documentation:

- [AnkiMobile Manual](https://docs.ankiweb.net/ankimobile/intro)
- [AnkiDroid Manual](https://docs.ankidroid.org/)
- [Official FAQs](https://docs.ankiweb.net/faqs/intro)
- [Add-on Author Documentation](https://docs.ankiweb.net/addons/intro)
"""
    (DST / "index.md").write_text(index_md, encoding="utf-8")


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"Source docs directory not found: {SRC}")

    # Preserve already-generated tutorial assets and custom guides if present
    existing_tutorials = None
    tut_dir = DST / "assets" / "tutorials"
    if tut_dir.exists():
        existing_tutorials = ROOT / "_tmp_tutorials_backup"
        if existing_tutorials.exists():
            shutil.rmtree(existing_tutorials)
        shutil.copytree(tut_dir, existing_tutorials)

    existing_guides = None
    guides_dir = DST / "guides"
    if guides_dir.exists():
        existing_guides = ROOT / "_tmp_guides_backup"
        if existing_guides.exists():
            shutil.rmtree(existing_guides)
        shutil.copytree(guides_dir, existing_guides)

    if DST.exists():
        shutil.rmtree(DST)
    DST.mkdir(parents=True, exist_ok=True)

    src_media = SRC / "media"
    if src_media.exists():
        shutil.copytree(src_media, DST / "media")

    if existing_tutorials and existing_tutorials.exists():
        shutil.copytree(existing_tutorials, DST / "assets" / "tutorials")
        shutil.rmtree(existing_tutorials)
    else:
        (DST / "assets" / "tutorials").mkdir(parents=True, exist_ok=True)

    if existing_guides and existing_guides.exists():
        shutil.copytree(existing_guides, DST / "guides")
        shutil.rmtree(existing_guides)

    existing_manual_slugs = collect_manual_slugs()
    converted_count = 0

    manual_dir = SRC / "manual"
    for fp in manual_dir.rglob("*"):
        if fp.is_file() and fp.suffix in (".mdx", ".md"):
            rel = fp.relative_to(SRC)
            out_file = (DST / rel).with_suffix(".md")
            out_file.parent.mkdir(parents=True, exist_ok=True)
            txt = fp.read_text(encoding="utf-8")
            out_file.write_text(convert_markdown(txt, rel, existing_manual_slugs), encoding="utf-8")
            converted_count += 1

    write_vanilla_index()
    print(f"Converted {converted_count} Anki Manual pages into {DST / 'manual'}")


if __name__ == "__main__":
    main()
