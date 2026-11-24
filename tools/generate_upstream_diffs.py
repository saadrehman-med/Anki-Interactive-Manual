"""Generate normalized upstream-vs-local Git diff JSON for the Anki Manual.

Shallow sparse-clones `ankitects/anki` (`docs-site/manual`), normalizes upstream
`.mdx` files through `convert_docs.convert_markdown()` so Mintlify syntax
conversions do not create noise, strips `<!-- tutorial:... -->` blocks into
separate collapsible entries, and writes changed-hunks-only JSON to
`quartz/static/upstream-diffs.json`.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path
from typing import Any

import convert_docs

ROOT = Path(__file__).resolve().parent.parent
DOCS_MANUAL_DIR = ROOT / "docs" / "manual"
OUT_PATH = ROOT / "quartz" / "static" / "upstream-diffs.json"
DEFAULT_REPO = "https://github.com/ankitects/anki.git"
REPO_WEB_URL = "https://github.com/ankitects/anki"

TUTORIAL_BLOCK_RE = re.compile(
    r"<!--\s*tutorial:([A-Za-z0-9_-]+):start\s*-->\r?\n([\s\S]*?)<!--\s*tutorial:\1:end\s*-->",
    re.MULTILINE,
)


def _handle_remove_readonly(func: Any, path: str, _exc: Any) -> None:
    os.chmod(path, stat.S_IWRITE)
    func(path)


def safe_rmtree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, onerror=_handle_remove_readonly)


def clone_upstream_manual(repo_url: str, tmp_dir: Path) -> tuple[str, str, str]:
    """Shallow sparse-clone only `docs-site/manual` and return (sha, short_sha, date)."""
    safe_rmtree(tmp_dir)
    subprocess.run(
        [
            "git",
            "clone",
            "--depth=1",
            "--filter=blob:none",
            "--sparse",
            repo_url,
            str(tmp_dir),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_dir), "sparse-checkout", "set", "docs-site/manual"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return read_git_head(tmp_dir)


def read_git_head(repo_dir: Path) -> tuple[str, str, str]:
    res = subprocess.run(
        ["git", "-C", str(repo_dir), "log", "-1", "--format=%H%n%h%n%cs"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    lines = res.stdout.strip().splitlines()
    return lines[0].strip(), lines[1].strip(), lines[2].strip()


def extract_tutorials(markdown_text: str) -> tuple[str, list[dict[str, Any]]]:
    """Strip embedded `<!-- tutorial:... -->` blocks and return them separately."""
    tutorials: list[dict[str, Any]] = []

    def repl(match: re.Match[str]) -> str:
        tid = match.group(1)
        full_lines = match.group(0).splitlines()
        tutorials.append(
            {
                "id": tid,
                "added": len(full_lines),
                "lines": full_lines,
            }
        )
        return ""

    stripped = TUTORIAL_BLOCK_RE.sub(repl, markdown_text)
    return stripped, tutorials


def normalize_spacing(text: str) -> list[str]:
    cleaned = text.replace("\r\n", "\n")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned.splitlines() if cleaned else []


def parse_unified_hunks(diff_lines: list[str]) -> tuple[list[dict[str, Any]], int, int]:
    """Convert `difflib.unified_diff` output into structured changed-only hunks."""
    hunks: list[dict[str, Any]] = []
    current_hunk: dict[str, Any] | None = None
    added = 0
    removed = 0

    for line in diff_lines:
        if line.startswith(("--- ", "+++ ")):
            continue
        if line.startswith("@@ "):
            if current_hunk is not None:
                hunks.append(current_hunk)
            current_hunk = {"header": line, "lines": []}
            continue
        if current_hunk is None:
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1
        current_hunk["lines"].append(line)

    if current_hunk is not None:
        hunks.append(current_hunk)

    return hunks, added, removed


def build_diff_payload(upstream_root: Path, sha: str, short_sha: str, commit_date: str) -> dict[str, Any]:
    docs_site = upstream_root / "docs-site"
    convert_docs.SRC = docs_site
    existing_slugs = convert_docs.collect_manual_slugs()

    upstream_manual_dir = docs_site / "manual"
    upstream_files: dict[str, Path] = {}
    for fp in upstream_manual_dir.rglob("*"):
        if fp.is_file() and fp.suffix in (".mdx", ".md"):
            slug = fp.relative_to(docs_site).with_suffix("").as_posix()
            upstream_files[slug] = fp

    pages: dict[str, Any] = {}
    for local_fp in sorted(DOCS_MANUAL_DIR.rglob("*.md")):
        rel_docs = local_fp.relative_to(ROOT / "docs")
        slug = rel_docs.with_suffix("").as_posix()
        upstream_fp = upstream_files.get(slug)
        if upstream_fp is None:
            continue

        upstream_rel_from_site = upstream_fp.relative_to(docs_site)
        upstream_raw = upstream_fp.read_text(encoding="utf-8")
        upstream_converted = convert_docs.convert_markdown(
            upstream_raw, upstream_rel_from_site, existing_slugs
        )

        local_raw = local_fp.read_text(encoding="utf-8")
        local_prose, tutorials = extract_tutorials(local_raw)

        upstream_lines = normalize_spacing(upstream_converted)
        local_lines = normalize_spacing(local_prose)

        diff_iter = difflib.unified_diff(
            upstream_lines,
            local_lines,
            fromfile=f"a/docs-site/{upstream_rel_from_site.as_posix()}",
            tofile=f"b/docs/{rel_docs.as_posix()}",
            n=3,
            lineterm="",
        )
        hunks, added, removed = parse_unified_hunks(list(diff_iter))

        pages[slug] = {
            "upstreamPath": f"docs-site/{upstream_rel_from_site.as_posix()}",
            "added": added,
            "removed": removed,
            "hunks": hunks,
            "tutorials": tutorials,
        }

    return {
        "ok": True,
        "repoUrl": REPO_WEB_URL,
        "commit": sha,
        "shortCommit": short_sha,
        "commitDate": commit_date,
        "pages": pages,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate upstream Anki Manual diff JSON.")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="Upstream git repository URL.")
    parser.add_argument(
        "--upstream-dir",
        type=Path,
        default=None,
        help="Optional existing clone directory containing `docs-site/manual`.",
    )
    parser.add_argument(
        "--keep-tmp",
        action="store_true",
        help="Keep temporary `_tmp_anki` directory instead of removing it.",
    )
    parser.add_argument(
        "--allow-offline",
        action="store_true",
        help="Write `{ok: false}` fallback JSON instead of failing if git clone fails.",
    )
    parser.add_argument("--out", type=Path, default=OUT_PATH, help="Output JSON path.")
    args = parser.parse_args()

    tmp_dir = ROOT / "_tmp_anki"
    using_temp = args.upstream_dir is None
    repo_dir = args.upstream_dir if args.upstream_dir is not None else tmp_dir

    try:
        if using_temp:
            sha, short_sha, commit_date = clone_upstream_manual(args.repo, repo_dir)
        else:
            sha, short_sha, commit_date = read_git_head(repo_dir)
        payload = build_diff_payload(repo_dir, sha, short_sha, commit_date)
    except Exception as exc:
        if not args.allow_offline:
            raise
        print(f"[upstream-diff] Fallback offline payload due to: {exc}")
        payload = {
            "ok": False,
            "repoUrl": REPO_WEB_URL,
            "commit": "",
            "shortCommit": "",
            "commitDate": "",
            "pages": {},
        }
    finally:
        if using_temp and not args.keep_tmp:
            safe_rmtree(tmp_dir)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    page_count = len(payload.get("pages", {}))
    changed_pages = sum(
        1 for p in payload.get("pages", {}).values() if p["added"] > 0 or p["removed"] > 0
    )
    print(
        f"Wrote {args.out.relative_to(ROOT)} (ok={payload['ok']}, commit={payload.get('shortCommit')}, "
        f"pages={page_count}, prose_changed={changed_pages})"
    )


if __name__ == "__main__":
    main()
