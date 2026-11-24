import { getFullSlug, joinSegments, pathToRoot } from "../../util/path"

interface DiffHunk {
  header: string
  lines: string[]
}

interface DiffTutorialBlock {
  id: string
  added: number
  lines: string[]
}

interface PageDiffEntry {
  upstreamPath: string
  added: number
  removed: number
  hunks: DiffHunk[]
  tutorials: DiffTutorialBlock[]
}

interface UpstreamDiffPayload {
  ok: boolean
  repoUrl: string
  commit: string
  shortCommit: string
  commitDate: string
  pages: Record<string, PageDiffEntry>
}

let cachedPromise: Promise<UpstreamDiffPayload | null> | null = null

function loadDiffData(): Promise<UpstreamDiffPayload | null> {
  if (!cachedPromise) {
    const baseDir = pathToRoot(getFullSlug(window))
    const url = joinSegments(baseDir, "static/upstream-diffs.json")
    cachedPromise = fetch(url)
      .then((res) => (res.ok ? (res.json() as Promise<UpstreamDiffPayload>) : null))
      .catch(() => null)
  }
  return cachedPromise
}

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className?: string,
  text?: string,
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag)
  if (className) node.className = className
  if (text !== undefined) node.textContent = text
  return node
}

function appendDiffLine(container: HTMLElement, rawLine: string, forceAdd = false): void {
  let cls = "gd-line gd-line-ctx"
  let display = rawLine

  if (forceAdd) {
    cls = "gd-line gd-line-add"
    display = `+${rawLine}`
  } else if (rawLine.startsWith("+")) {
    cls = "gd-line gd-line-add"
  } else if (rawLine.startsWith("-")) {
    cls = "gd-line gd-line-del"
  }

  container.appendChild(el("div", cls, display === "" ? " " : display))
}

function renderDiffView(payload: UpstreamDiffPayload | null, slug: string): HTMLElement {
  const root = el("div", "git-diff-view")
  root.id = "git-diff-view"

  const entry = payload?.ok ? payload.pages[slug] : undefined
  if (!payload || !payload.ok || !entry) {
    root.appendChild(el("div", "gd-empty", "cant fetch"))
    return root
  }

  const header = el("div", "gd-header")
  const meta = el("div", "gd-meta")

  const commitLink = el("a", "gd-link gd-sha", payload.shortCommit)
  commitLink.href = `${payload.repoUrl}/commit/${payload.commit}`
  commitLink.target = "_blank"
  commitLink.rel = "noopener noreferrer"
  meta.appendChild(commitLink)

  if (payload.commitDate) {
    meta.appendChild(el("span", "gd-date", payload.commitDate))
  }

  const fileLink = el("a", "gd-link gd-path", entry.upstreamPath)
  fileLink.href = `${payload.repoUrl}/blob/${payload.commit}/${entry.upstreamPath}`
  fileLink.target = "_blank"
  fileLink.rel = "noopener noreferrer"
  meta.appendChild(fileLink)

  header.appendChild(meta)

  const stats = el("div", "gd-stats")
  stats.appendChild(el("span", "gd-stat-add", `+${entry.added}`))
  stats.appendChild(el("span", "gd-stat-del", `-${entry.removed}`))
  header.appendChild(stats)

  root.appendChild(header)

  for (const hunk of entry.hunks) {
    const hunkBox = el("div", "gd-hunk")
    hunkBox.appendChild(el("div", "gd-hunk-header", hunk.header))
    const linesWrap = el("div", "gd-lines")
    for (const line of hunk.lines) {
      appendDiffLine(linesWrap, line)
    }
    hunkBox.appendChild(linesWrap)
    root.appendChild(hunkBox)
  }

  if (entry.tutorials.length > 0) {
    const tutList = el("div", "gd-tutorials")
    for (const tut of entry.tutorials) {
      const details = el("details", "gd-tutorial")
      const summary = el("summary", "gd-tutorial-summary")
      summary.appendChild(el("code", "gd-tutorial-id", `<!-- tutorial:${tut.id} -->`))
      summary.appendChild(el("span", "gd-stat-add", `+${tut.added}`))
      details.appendChild(summary)

      const linesWrap = el("div", "gd-lines")
      for (const line of tut.lines) {
        appendDiffLine(linesWrap, line, true)
      }
      details.appendChild(linesWrap)
      tutList.appendChild(details)
    }
    root.appendChild(tutList)
  }

  return root
}

document.addEventListener("nav", () => {
  let active = false
  document.documentElement.setAttribute("git-diff", "off")
  const existingView = document.getElementById("git-diff-view")
  existingView?.remove()

  const buttons = Array.from(document.getElementsByClassName("gitdiff")) as HTMLButtonElement[]
  const syncButtons = (on: boolean) => {
    for (const btn of buttons) {
      btn.dataset.active = on ? "true" : "false"
      btn.setAttribute("aria-pressed", on ? "true" : "false")
    }
  }

  const closeDiff = () => {
    active = false
    document.documentElement.setAttribute("git-diff", "off")
    syncButtons(false)
    document.getElementById("git-diff-view")?.remove()
  }

  const openDiff = async () => {
    const article = document.querySelector(".center > article") as HTMLElement | null
    if (!article || !article.parentElement) return

    active = true
    syncButtons(true)
    const slug = getFullSlug(window).replace(/^\/+|\/+$/g, "")
    const payload = await loadDiffData()
    if (!active) return

    document.getElementById("git-diff-view")?.remove()
    const view = renderDiffView(payload, slug)
    article.insertAdjacentElement("afterend", view)
    document.documentElement.setAttribute("git-diff", "on")
  }

  const onToggle = () => {
    if (active) {
      closeDiff()
    } else {
      void openDiff()
    }
  }

  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Escape" && active) {
      closeDiff()
    }
  }

  syncButtons(false)
  for (const btn of buttons) {
    btn.addEventListener("click", onToggle)
    window.addCleanup(() => btn.removeEventListener("click", onToggle))
  }

  document.addEventListener("keydown", onKeyDown)
  window.addCleanup(() => {
    document.removeEventListener("keydown", onKeyDown)
    closeDiff()
  })
})
