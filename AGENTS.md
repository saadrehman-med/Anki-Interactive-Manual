# Repository Guidelines & Tool Reference

## Safety, Privacy & Content Rules
- **Anki Isolation:** Never read, modify, sync, or launch personal Anki profiles. Always isolate automation to `./sandbox-anki` (`ANKI_BASE=./sandbox-anki`, `-b ./sandbox-anki -p DemoUser`).
- **Demo Data Only:** Keep only `Demo deck` with neutral general-knowledge cards in screenshots and recipes. Exclude `sandbox-anki/`, `tools/.venv/`, `node_modules/`, `public/`, and `quartz/static/upstream-diffs.json` via `.gitignore`.
- **No Leaks or Sensitive Info:** Never commit local OS user paths, API keys, tokens, personal profile data, or unverified claims anywhere in the repository (`docs/`, `recipes/`, `tools/`, `quartz/`, `AGENTS.md`).
- **Manual vs Custom Guides Separation:**
  - Keep `docs/manual/` prose strictly faithful to upstream `ankitects/anki` (`docs-site/manual/`), with links to non-manual official pages (`/faqs/...`, `/addons/...`, `/ankimobile/...`, `/releases/...`, `/translators/...`) routed to `https://docs.ankiweb.net/...`. Only insert `<!-- tutorial:<id>:start/end -->` walkthrough blocks inside `docs/manual/`.
  - Add custom tutorials and community workflows under `docs/guides/` (automatically preserved by `tools/convert_docs.py`). Always credit upstream/forum sources at the top.

## Creating a New Mimik Tutorial

### 1. Prepare the Target Markdown File
- **Manual page (`docs/manual/<slug>.md`):** Pick an existing heading as `insert_after` in your recipe (or add `<!-- tutorial:<id>:start -->` / `<!-- tutorial:<id>:end -->` markers) without editing surrounding manual prose.
- **Custom guide (`docs/guides/<slug>.md`):** Add frontmatter (`title: "..."`), original concise prose + attribution links, and `<!-- tutorial:<id>:start -->` / `<!-- tutorial:<id>:end -->` markers.

### 2. Author a Declarative Recipe (`recipes/<id>.yaml`)
- **Required fields:** `id`, `title`, `target_doc`, `steps` (optional: `intro`, `insert_after`, `setup`).
- **Step fields:**
  - `title` (`Step NN: ...`), `output` (`step-NN-<name>.webp`), `window` (`main` | `active_dialog`), `caption`
  - Optional: `pre_actions`, `post_actions`, `locate`, `highlight` (`color`, `badge`, `show_badge`, `badge_position`: `auto` | `top-left` | `right` | `top-right` | `bottom-right`)
- **Locator modes (`locate.mode`):**
  - `web`: `web` (`auto` | `deckBrowser` | `bottom`), `selector`, `text`, `js`, `scroll`, `padding`, `required`
  - `qt_widget`: `object_name`, `class_name`, `text`, `tab_text`, `padding`, `required`
  - `menu_item`: `menu`, `item`, `padding`, `required`
- **Supported `capturer` actions:** `close_dialogs`, `reset_to_decks`, `open_deck_overview`, `start_study_session`, `show_answer`, `open_deck_options`, `open_dialog` (`AddCards`, `Browser`, `Preferences`, `AddonsDialog`, `FilteredDeck`, `Stats`, `Export`, `NoteTypes`, `Import`), `setup_add_cards`, `open_card_layout`, `trigger_fields_dialog`, `open_profiles_dialog`, `click_qt_widget`, `set_filtered_deck_fields` (`name`, `search`, `limit`, `order`, `resched`), `setup_browser`, `select_preferences_tab`, `open_menu_and_locate`, `ensure_deck`, `delete_deck`, `set_col_config`, `wait_for` (`mode`: `web` | `qt_widget`, `selector`, `text`, `js`, `timeout_ms`), `web_select` (`label`, `value`), `web_toggle` (`label`, `checked`), `web_click` (`selector`, `text`), `web_expand` (`text`), `web_eval`, `resize_window`, `wait`.
- **Clean state invariant:** Always revert temporary decks/settings in `post_actions` (`close_dialogs`, `delete_deck`, `set_col_config`, `reset_to_decks`) so `Demo deck` remains clean for subsequent recipes.

### 3. Generate & Visually Verify
- **Multi-tutorial session workflow:** Pass `--keep-alive` on the first run (or pass multiple recipe IDs in one command) so `sandbox-anki` stays open; subsequent runs auto-reuse the live sandbox (`code_hash` checked) without cold startup. Pass `--stop-sandbox` when finished (or `--restart` to force-relaunch).
- Single recipe (fast iteration): `tools\.venv\Scripts\python.exe tools\generate_tutorials.py <recipe-id> --keep-alive --fast`
- Final quality / multi-recipe run: `tools\.venv\Scripts\python.exe tools\generate_tutorials.py <recipe-1> <recipe-2> --stop-sandbox`
- All recipes: `tools\.venv\Scripts\python.exe tools\generate_tutorials.py` (pass `--no-embed` to emit standalone `walkthrough.md` without modifying `docs/`).
- Inspect every `.webp` in `docs/assets/tutorials/<id>/` to confirm crisp highlight rings, non-overlapping step badges, loaded UI controls, and clean `Demo deck` data.

## Tools & Architecture Reference

### Upstream Manual & Diff Pipeline (`tools/convert_docs.py`, `tools/generate_upstream_diffs.py`)
- `convert_docs.py` converts Mintlify `docs-site/manual/` `.mdx` files into Quartz Markdown (`docs/manual/`), preserves `docs/assets/tutorials/` and `docs/guides/`, converts `<Note|Warning|Info|Danger|Tip>` to Obsidian callouts, and writes `docs/index.md`.
- `generate_upstream_diffs.py` shallow sparse-clones `ankitects/anki` (`docs-site/manual`), normalizes upstream `.mdx` via `convert_markdown()`, strips `<!-- tutorial:... -->` blocks, and writes changed-hunks-only JSON to `quartz/static/upstream-diffs.json` (`Static` emitter copies it into `public/static/` when present; `.github/workflows/deploy.yml` refreshes it before building).

### Sandboxed Capture Harness (`tools/setup_sandbox.py`, `tools/tutorial_capturer/`)
- Python environment: `tools/.venv` (`pillow`, `pyyaml`, `requests`). Bootstrap command: `tools\.venv\Scripts\python.exe tools\setup_sandbox.py`.
- Modular add-on layout (`tools/tutorial_capturer/`): `safety.py` (sandbox isolation + `code_hash`), `qt_helpers.py` (`_MainThreadDispatcher`, Qt widget/menu geometry, `devicePixelRatio` capture), `web_helpers.py` (`QWebEngineView` locators, `wait_for_web`, Svelte helpers), `actions.py` (`@register_action` registry + `/step` batch execution), `server.py` (HTTP `/health`, `/action`, `/step`), `__init__.py` (hooks).
- `tutorial_capturer` refuses to start unless `mw.pm.base` resolves inside `sandbox-anki`.
- **Maintenance invariants:**
  - Keep `aqt.*` imports at module top level (never inside action functions).
  - Use `aqt.dialogs.open("AddCards", mw)` (not `"Add"`).
  - Track `_LAST_OPENED_WINDOW` (`mark_opened`) for deterministic capture when foreground focus is absent.
  - Close dialogs via `aqt.dialogs.closeAll()` and `QDialog.done(0)` (avoids unsaved-changes prompts); close `QMenu` and pump events after `QMenu.popup`.
  - Trigger modal `exec()` dialogs (e.g., `FieldDialog`) via `QTimer.singleShot(0, ...)` and poll from the HTTP handler thread (`_run_open_fields_dialog`).

### Quartz Static Site (`quartz.config.ts`, `quartz.layout.ts`, `quartz/`)
- **Markdown invariant:** Always keep a blank `>` line before `> ---` inside `[!mimik]` blockquotes so intro text is not parsed as a setext `<h2>`.
- **Walkthrough & Diff:** `Plugin.Walkthrough()` runs before `Plugin.ObsidianFlavoredMarkdown()`, supporting `> [!mimik]`, `> [!walkthrough]`, and `[data-walkthrough]`. `GitDiff` toggles `static/upstream-diffs.json` inline via the sidebar `-/+` button.
- **Verification commands:**
  - Typecheck: `npx tsc --noEmit`
  - Build static site (`public/`): `npm run build`
  - Dev preview server: `node ./quartz/bootstrap-cli.mjs build --serve -d docs --port 8081 --wsPort 3002` (stop watcher before bulk deletion/regeneration in `docs/`).
