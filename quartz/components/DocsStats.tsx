import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"
import style from "./styles/docsStats.scss"
import readingTime from "reading-time"
import { resolveRelative, FullSlug } from "../util/path"
import { getDate } from "./Date"
import fs from "fs"
import path from "path"

export default (() => {
  const DocsStats: QuartzComponent = ({ ctx, cfg, fileData, allFiles }: QuartzComponentProps) => {
    const currentSlug = (fileData.slug ?? "index") as FullSlug

    const folderSet = new Set<string>()
    let totalWords = 0

    for (const file of allFiles) {
      const { words } = readingTime(file.text ?? "")
      totalWords += words

      const relPath = (file.relativePath ?? "").replace(/\\/g, "/")
      const parts = relPath.split("/")
      if (parts.length > 1) {
        let currentPath = ""
        for (let i = 0; i < parts.length - 1; i++) {
          currentPath = currentPath ? `${currentPath}/${parts[i]}` : parts[i]
          folderSet.add(currentPath)
        }
      }
    }

    const docFiles = allFiles.filter((f) => {
      const slug = (f.slug ?? "").toLowerCase()
      return slug !== "index" && !slug.endsWith("/index")
    })

    type DocItem = {
      title: string
      href: string
      readMinutes: number
      mtimeMs: number
      isManual: boolean
      hasWalkthrough: boolean
    }

    const candidates: DocItem[] = []
    let walkthroughCount = 0

    for (const file of docFiles) {
      const rel = (file.relativePath ?? "").replace(/\\/g, "/")
      const segments = rel.split("/")
      const title =
        file.frontmatter?.title ?? segments[segments.length - 1].replace(/\.md$/i, "")
      const text = file.text ?? ""
      const { minutes } = readingTime(text)
      const readMinutes = Math.max(1, Math.ceil(minutes))
      const hasWalkthrough = Boolean(file.hasWalkthrough)
      if (hasWalkthrough) walkthroughCount++

      let mtimeMs = 0
      try {
        const fullPath = path.resolve(ctx.argv.directory, file.relativePath!)
        mtimeMs = fs.statSync(fullPath).mtimeMs
      } catch {
        const d = getDate(cfg, file)
        mtimeMs = d ? d.getTime() : 0
      }

      if (file.slug) {
        candidates.push({
          title,
          href: resolveRelative(currentSlug, file.slug as FullSlug),
          readMinutes,
          mtimeMs,
          isManual: rel.startsWith("manual/"),
          hasWalkthrough,
        })
      }
    }

    // Prioritize interactive walkthrough pages & core manual chapters in the quick browser list
    const featuredDocs = candidates
      .sort((a, b) => {
        if (a.hasWalkthrough !== b.hasWalkthrough) return a.hasWalkthrough ? -1 : 1
        if (a.isManual !== b.isManual) return a.isManual ? -1 : 1
        return b.mtimeMs - a.mtimeMs
      })
      .slice(0, 18)

    const formattedWords = totalWords >= 1000 ? `${(totalWords / 1000).toFixed(1)}k` : `${totalWords}`

    return (
      <div class="home-widgets">
        <div class="docs-stats-bar">
          <span class="stat-item">{docFiles.length} pages</span>
          <span class="stat-divider">·</span>
          <span class="stat-item">{formattedWords} words</span>
          <span class="stat-divider">·</span>
          <span class="stat-item">{folderSet.size} sections</span>
          {walkthroughCount > 0 && (
            <>
              <span class="stat-divider">·</span>
              <span class="stat-item">
                {walkthroughCount} interactive {walkthroughCount === 1 ? "walkthrough" : "walkthroughs"}
              </span>
            </>
          )}
        </div>

        {featuredDocs.length > 0 && (
          <div class="recent-guides-section">
            <div class="recent-guides-header">Core Manual &amp; Walkthroughs</div>
            <ul class="recent-guides-list">
              {featuredDocs.map((doc) => (
                <li class="recent-guide-row">
                  <a href={doc.href} class="recent-guide-title internal">
                    {doc.title}
                    {doc.hasWalkthrough && <span class="walkthrough-tag">Interactive</span>}
                  </a>
                  <span class="recent-guide-time">{doc.readMinutes} min read</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    )
  }

  DocsStats.css = style
  return DocsStats
}) satisfies QuartzComponentConstructor
