"""Automated sandboxed Anki tutorial generator.

Reads declarative JSON/YAML recipes from `recipes/`, drives the isolated
`sandbox-anki` instance via AnkiConnect + `tutorial_capturer`, annotates high-DPI
screenshots with crisp highlight rings + step badges, saves optimized `.webp`
images into `docs/assets/tutorials/<recipe-id>/`, and embeds/updates the
interactive `> [!mimik]` walkthrough in the target manual Markdown file.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import posixpath
import re
from pathlib import Path
from typing import Any

import requests
import yaml
from PIL import Image, ImageDraw, ImageFont

from setup_sandbox import (
    ANKICONNECT_URL,
    CAPTURER_URL,
    ankiconnect,
    assert_sandbox_isolation,
    find_anki_exe,
    init_demouser_profile,
    install_ankiconnect,
    install_tutorial_capturer,
    launch_sandbox_anki,
    probe_live_sandbox,
    seed_demo_cards,
    source_capturer_fingerprint,
    stop_sandbox_if_running,
    wait_for_sandbox_apis,
)

ROOT = Path(__file__).resolve().parent.parent
RECIPES_DIR = ROOT / "recipes"
TUTORIALS_ASSETS_DIR = ROOT / "docs" / "assets" / "tutorials"

_SESSION = requests.Session()


def call_capturer(action: str, **params: Any) -> dict[str, Any]:
    """Invoke an action on the sandboxed `tutorial_capturer` HTTP server."""
    resp = _SESSION.post(
        f"{CAPTURER_URL}/action",
        json={"action": action, **params},
        timeout=30.0,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"tutorial_capturer {action!r} failed ({resp.status_code}): {resp.text}")
    body = resp.json()
    if not body.get("ok"):
        raise RuntimeError(f"tutorial_capturer {action!r} error: {body.get('error')}")
    return body.get("data", {})


def call_step(step_payload: dict[str, Any]) -> dict[str, Any]:
    """Execute pre_actions + locate + capture + post_actions in a single `/step` call."""
    resp = _SESSION.post(
        f"{CAPTURER_URL}/step",
        json=step_payload,
        timeout=45.0,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"tutorial_capturer /step failed ({resp.status_code}): {resp.text}")
    body = resp.json()
    if not body.get("ok"):
        raise RuntimeError(f"tutorial_capturer /step error: {body.get('error')}")
    return body.get("data", {})


def execute_action_list(actions: list[dict[str, Any]]) -> None:
    """Execute a sequence of `capturer` or `ankiconnect` actions."""
    for item in actions:
        kind = item.get("via", "capturer")
        if kind == "ankiconnect":
            action = item["action"]
            params = {k: v for k, v in item.items() if k not in ("via", "action")}
            ankiconnect(action, **params)
        else:
            action = item["action"]
            params = {k: v for k, v in item.items() if k not in ("via", "action")}
            call_capturer(action, **params)


def _hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (r, g, b, alpha)


def annotate_screenshot(
    png_bytes: bytes,
    bbox: dict[str, Any] | None,
    dpr: float = 1.0,
    ring_color: str = "#FF5A36",
    badge_text: str | None = None,
    badge_position: str = "top-left",
) -> Image.Image:
    """Render an anti-aliased highlight ring & optional step badge onto a screenshot."""
    base = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    if not bbox:
        return base.convert("RGB")

    scale = max(1.0, float(dpr))
    x = int(bbox["x"])
    y = int(bbox["y"])
    w = int(bbox["width"])
    h = int(bbox["height"])

    # Clamp safely inside image bounds
    x0 = max(2, x)
    y0 = max(2, y)
    x1 = min(base.width - 3, x + w)
    y1 = min(base.height - 3, y + h)

    if x1 <= x0 or y1 <= y0:
        return base.convert("RGB")

    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    radius = max(8, round(10 * scale))
    stroke = max(3, round(3.5 * scale))

    # Subtle outer halo + crisp rounded highlight ring
    halo_pad = max(3, round(3 * scale))
    draw.rounded_rectangle(
        [x0 - halo_pad, y0 - halo_pad, x1 + halo_pad, y1 + halo_pad],
        radius=radius + halo_pad,
        outline=_hex_to_rgba(ring_color, 75),
        width=stroke + round(3 * scale),
    )
    draw.rounded_rectangle(
        [x0, y0, x1, y1],
        radius=radius,
        fill=_hex_to_rgba(ring_color, 22),
        outline=_hex_to_rgba(ring_color, 245),
        width=stroke,
    )

    # Optional step badge pill near top-left of highlight box
    if badge_text:
        font_size = max(13, round(14 * scale))
        try:
            font = ImageFont.truetype("segoeui.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

        pad_x = round(8 * scale)
        pad_y = round(3 * scale)
        tb = draw.textbbox((0, 0), badge_text, font=font)
        tw = tb[2] - tb[0]
        th = tb[3] - tb[1]
        bw = max(tw + pad_x * 2, th + pad_y * 2)
        bh = th + pad_y * 2

        bx0 = max(4, x0 - round(4 * scale))
        by0 = y0 - bh - round(6 * scale)
        if badge_position == "auto":
            if by0 >= 4:
                pass
            elif x1 + bw + round(12 * scale) <= base.width - 4:
                bx0 = min(base.width - bw - 4, x1 + round(8 * scale))
                by0 = max(4, y0 + (y1 - y0 - bh) // 2)
            elif y1 + bh + round(10 * scale) <= base.height - 4:
                bx0 = min(base.width - bw - 4, x1 - bw + round(4 * scale))
                by0 = min(base.height - bh - 4, y1 + round(6 * scale))
            else:
                bx0 = max(4, min(base.width - bw - 4, x1 - bw - round(4 * scale)))
                by0 = max(4, y0 + round(4 * scale))
        elif badge_position == "right":
            bx0 = min(base.width - bw - 4, x1 + round(8 * scale))
            by0 = max(4, y0 + (y1 - y0 - bh) // 2)
        elif badge_position == "top-right":
            bx0 = min(base.width - bw - 4, x1 - bw + round(4 * scale))
            if by0 < 4:
                by0 = min(base.height - bh - 4, y1 + round(6 * scale))
        elif badge_position == "bottom-right":
            bx0 = min(base.width - bw - 4, x1 - bw + round(4 * scale))
            by0 = min(base.height - bh - 4, y1 + round(6 * scale))
        else:
            if by0 < 4:
                by0 = min(base.height - bh - 4, y1 + round(6 * scale))
        bx1 = min(base.width - 4, bx0 + bw)
        by1 = by0 + bh

        draw.rounded_rectangle(
            [bx0, by0, bx1, by1],
            radius=bh // 2,
            fill=_hex_to_rgba(ring_color, 250),
            outline=(255, 255, 255, 235),
            width=max(1, round(1.5 * scale)),
        )
        tx = bx0 + (bw - tw) // 2 - tb[0]
        ty = by0 + (bh - th) // 2 - tb[1]
        draw.text((tx, ty), badge_text, fill=(255, 255, 255, 255), font=font)

    composited = Image.alpha_composite(base, overlay)
    return composited.convert("RGB")


def format_walkthrough_markdown(recipe: dict[str, Any], target_doc_path: Path) -> str:
    """Build a Quartz-safe `> [!mimik]` walkthrough block with blank `>` before `> ---`."""
    recipe_id = recipe["id"]
    title = recipe["title"]
    intro = (recipe.get("intro") or "").strip()

    doc_dir = target_doc_path.parent
    assets_dir = TUTORIALS_ASSETS_DIR / recipe_id
    rel_assets = posixpath.relpath(assets_dir.as_posix(), doc_dir.as_posix())

    lines: list[str] = [f"> [!mimik] {title}"]
    if intro:
        for ln in intro.splitlines():
            lines.append(f"> {ln}" if ln.strip() else ">")

    for idx, step in enumerate(recipe["steps"], start=1):
        # Rule guard: always ensure a blank `>` line precedes `> ---`
        if lines[-1].strip() != ">":
            lines.append(">")
        lines.append("> ---")
        lines.append(">")

        step_title = step["title"]
        if not re.match(r"^Step\s+\d+", step_title, re.IGNORECASE):
            step_title = f"Step {idx:02d}: {step_title}"
        lines.append(f"> ## {step_title}")
        lines.append(">")

        img_name = step["output"]
        alt = step.get("alt") or step_title
        lines.append(f"> ![{alt}]({rel_assets}/{img_name})")
        lines.append(">")

        caption = step["caption"].strip()
        for ln in caption.splitlines():
            lines.append(f"> {ln}" if ln.strip() else ">")

    return "\n".join(lines)


def embed_into_doc(recipe: dict[str, Any], snippet: str) -> Path:
    """Idempotently insert/update the walkthrough snippet inside `target_doc`."""
    target_doc = ROOT / recipe["target_doc"]
    if not target_doc.is_file():
        raise FileNotFoundError(f"Target manual doc not found: {target_doc}")

    recipe_id = recipe["id"]
    start_marker = f"<!-- tutorial:{recipe_id}:start -->"
    end_marker = f"<!-- tutorial:{recipe_id}:end -->"
    block = f"{start_marker}\n\n{snippet}\n\n{end_marker}"

    content = target_doc.read_text(encoding="utf-8")
    pattern = re.compile(
        re.escape(start_marker) + r"[\s\S]*?" + re.escape(end_marker),
        re.MULTILINE,
    )

    if pattern.search(content):
        updated = pattern.sub(block, content, count=1)
    else:
        anchor = recipe.get("insert_after")
        if anchor and anchor in content:
            idx = content.index(anchor) + len(anchor)
            # Advance to end of line
            eol = content.find("\n", idx)
            if eol == -1:
                eol = len(content)
            updated = content[:eol] + "\n\n" + block + "\n" + content[eol:]
        else:
            updated = content.rstrip() + "\n\n" + block + "\n"

    target_doc.write_text(updated, encoding="utf-8")
    return target_doc


def load_recipe(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(raw)
    return yaml.safe_load(raw)


def _has_ankiconnect_actions(actions: list[dict[str, Any]] | None) -> bool:
    return any((a or {}).get("via") == "ankiconnect" for a in (actions or []))


def run_recipe(recipe_path: Path, update_docs: bool = True, fast: bool = False) -> dict[str, Any]:
    recipe = load_recipe(recipe_path)
    recipe_id = recipe["id"]
    out_dir = TUTORIALS_ASSETS_DIR / recipe_id
    out_dir.mkdir(parents=True, exist_ok=True)

    webp_quality = 75 if fast else 82
    webp_method = 1 if fast else 6

    print(f"\n[recipe] Running {recipe_id!r} ({recipe['title']})")
    if recipe.get("setup"):
        execute_action_list(recipe["setup"])

    saved_files: list[Path] = []
    for idx, step in enumerate(recipe["steps"], start=1):
        print(f"  -> {step['title']}")
        if step.get("static_image"):
            src = ROOT / step["static_image"]
            out_file = out_dir / step["output"]
            out_file.parent.mkdir(parents=True, exist_ok=True)
            if src.resolve() != out_file.resolve():
                out_file.write_bytes(src.read_bytes())
            saved_files.append(out_file)
            print(f"     copied static {out_file.relative_to(ROOT)}")
            continue
        pre = step.get("pre_actions") or []
        post = step.get("post_actions") or []
        can_batch = not _has_ankiconnect_actions(pre) and not _has_ankiconnect_actions(post)

        if can_batch:
            step_payload: dict[str, Any] = {
                "pre_actions": pre,
                "window": step.get("window", "active_dialog"),
                "post_actions": post,
            }
            if step.get("locate"):
                step_payload["locate"] = step["locate"]
            cap = call_step(step_payload)
        else:
            if pre:
                execute_action_list(pre)
            capture_params: dict[str, Any] = {
                "window": step.get("window", "active_dialog"),
            }
            if step.get("locate"):
                capture_params["locate"] = step["locate"]
            cap = call_capturer("capture", **capture_params)
            if post:
                execute_action_list(post)

        png_bytes = base64.b64decode(cap["image_png_b64"])

        hl = step.get("highlight") or {}
        ring_color = hl.get("color", "#FF5A36")
        badge = hl.get("badge", str(idx)) if hl.get("show_badge", True) else None
        badge_pos = hl.get("badge_position", "top-left")

        img = annotate_screenshot(
            png_bytes=png_bytes,
            bbox=cap.get("bbox"),
            dpr=float(cap.get("dpr", 1.0)),
            ring_color=ring_color,
            badge_text=badge,
            badge_position=badge_pos,
        )

        out_file = out_dir / step["output"]
        img.save(out_file, format="WEBP", quality=webp_quality, method=webp_method)
        saved_files.append(out_file)
        print(f"     saved {out_file.relative_to(ROOT)} ({img.width}x{img.height}, bbox={cap.get('bbox') is not None})")

    call_capturer("close_dialogs")
    call_capturer("reset_to_decks")

    target_doc = ROOT / recipe["target_doc"]
    snippet = format_walkthrough_markdown(recipe, target_doc)

    if update_docs and recipe.get("target_doc"):
        embed_into_doc(recipe, snippet)
        print(f"[recipe] Embedded walkthrough into {recipe['target_doc']}")
        snippet_rel = str(target_doc.relative_to(ROOT))
    else:
        snippet_path = out_dir / "walkthrough.md"
        snippet_path.write_text(snippet + "\n", encoding="utf-8")
        snippet_rel = str(snippet_path.relative_to(ROOT))

    return {
        "id": recipe_id,
        "images": [str(p.relative_to(ROOT)) for p in saved_files],
        "snippet": snippet_rel,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Anki interactive tutorials from recipes.")
    parser.add_argument("recipes", nargs="*", help="Specific recipe IDs or paths (defaults to all in recipes/).")
    parser.add_argument("--no-embed", action="store_true", help="Do not modify docs/*.md; only generate .webp and walkthrough.md.")
    parser.add_argument("--reuse-running", action="store_true", help="Reuse an already-running sandboxed Anki instance.")
    parser.add_argument("--keep-alive", action="store_true", help="Keep the sandbox Anki instance running after finishing so subsequent recipes start fast.")
    parser.add_argument("--restart", action="store_true", help="Force-restart sandbox Anki even if already running.")
    parser.add_argument("--stop-sandbox", action="store_true", help="Stop any running background sandbox Anki instance (runs after recipes if provided).")
    parser.add_argument("--fast", action="store_true", help="Use fast WebP compression (quality=75, method=1) for rapid iteration.")
    args = parser.parse_args()

    assert_sandbox_isolation()

    if args.stop_sandbox and not args.recipes:
        if not stop_sandbox_if_running():
            print("[sandbox] No tracked background sandbox process running.")
        return

    if args.recipes:
        recipe_files: list[Path] = []
        for item in args.recipes:
            p = Path(item)
            if p.is_file():
                recipe_files.append(p)
            else:
                matches = list(RECIPES_DIR.glob(f"{item}.*"))
                if not matches:
                    raise FileNotFoundError(f"Recipe not found: {item}")
                recipe_files.append(matches[0])
    else:
        recipe_files = sorted(
            [p for p in RECIPES_DIR.iterdir() if p.suffix.lower() in (".yaml", ".yml", ".json")]
        )

    if not recipe_files:
        raise SystemExit(f"No recipes found in {RECIPES_DIR}")

    expected_hash = source_capturer_fingerprint()
    live_health = None if args.restart else probe_live_sandbox()
    reusing_live = False

    if live_health is not None and (args.reuse_running or live_health.get("code_hash") == expected_hash):
        reusing_live = True
        print(f"[sandbox] Reusing live sandbox Anki (code_hash={live_health.get('code_hash')}).")
    elif live_health is not None:
        print("[sandbox] Live sandbox add-on code changed; restarting sandbox cleanly...")
        stop_sandbox_if_running()

    proc = None
    if not reusing_live and not args.reuse_running:
        anki_exe = find_anki_exe()
        init_demouser_profile(anki_exe)
        install_ankiconnect()
        install_tutorial_capturer()
        proc = launch_sandbox_anki(anki_exe, detached=args.keep_alive)

    try:
        wait_for_sandbox_apis()
        seed_demo_cards()
        if not reusing_live:
            # Allow any background startup checks (e.g. add-on update dialog) to settle & dismiss
            call_capturer("wait", ms=2200)
        call_capturer("close_dialogs")
        results = [run_recipe(rf, update_docs=not args.no_embed, fast=args.fast) for rf in recipe_files]
        print("\n[done] Generated tutorials:", json.dumps(results, indent=2))
    finally:
        if args.stop_sandbox:
            if proc is not None:
                proc.terminate()
                proc.wait(timeout=10)
            stop_sandbox_if_running()
        elif proc is not None and not args.keep_alive:
            proc.terminate()
            proc.wait(timeout=10)
        elif proc is not None and args.keep_alive:
            print(f"[sandbox] Keeping sandbox Anki alive (pid={proc.pid}) for fast follow-up runs.")


if __name__ == "__main__":
    main()
