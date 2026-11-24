import { simplifySlug } from "../../util/path"

type SmartMode = "top" | "bottom" | "random"

const TOOLTIPS: Record<SmartMode, string> = {
  top: "Scroll to top",
  bottom: "Scroll to bottom",
  random: "Random doc",
}

document.addEventListener("nav", () => {
  const toggleFoldersBtn = document.getElementById("fb-toggle-folders") as HTMLButtonElement | null
  if (toggleFoldersBtn) {
    const syncFolderBtnState = () => {
      const anyOpen = Boolean(document.querySelector(".explorer .folder-outer.open"))
      const nextState = anyOpen ? "collapse" : "expand"
      const label = anyOpen ? "Collapse all" : "Expand all"
      toggleFoldersBtn.dataset.state = nextState
      toggleFoldersBtn.dataset.tooltip = label
      toggleFoldersBtn.setAttribute("aria-label", label)
    }

    const onToggleAllFolders = () => {
      const folderContainers = Array.from(
        document.querySelectorAll<HTMLElement>(".explorer .folder-container"),
      )
      if (folderContainers.length === 0) return

      const anyOpen = folderContainers.some((fc) =>
        fc.nextElementSibling?.classList.contains("open"),
      )
      const shouldCollapse = anyOpen
      const updatedState: { path: string; collapsed: boolean }[] = []

      for (const fc of folderContainers) {
        const folderOuter = fc.nextElementSibling as HTMLElement | null
        const folderPath = fc.dataset.folderpath
        if (folderOuter) {
          if (shouldCollapse) {
            folderOuter.classList.remove("open")
          } else {
            folderOuter.classList.add("open")
          }
        }
        if (folderPath) {
          updatedState.push({ path: folderPath, collapsed: shouldCollapse })
        }
      }

      try {
        localStorage.setItem("fileTree", JSON.stringify(updatedState))
      } catch {}

      syncFolderBtnState()
    }

    toggleFoldersBtn.addEventListener("click", onToggleAllFolders)
    document.addEventListener("folderstatechange", syncFolderBtnState)
    window.addCleanup(() => {
      toggleFoldersBtn.removeEventListener("click", onToggleAllFolders)
      document.removeEventListener("folderstatechange", syncFolderBtnState)
    })

    requestAnimationFrame(() => syncFolderBtnState())
    setTimeout(syncFolderBtnState, 150)
  }

  const btn = document.getElementById("fb-smart-btn") as HTMLButtonElement | null
  if (!btn) return

  const rawSlug = (document.body.dataset.slug ?? "index").toLowerCase()
  const currentSlug = simplifySlug((document.body.dataset.slug ?? "index") as any).toLowerCase()
  const isIndex =
    rawSlug === "index" || currentSlug === "index" || currentSlug === "/" || currentSlug === ""

  const setMode = (mode: SmartMode) => {
    if (btn.dataset.mode === mode) return
    btn.dataset.mode = mode
    btn.dataset.tooltip = TOOLTIPS[mode]
    btn.setAttribute("aria-label", TOOLTIPS[mode])
  }

  const updateMode = () => {
    if (isIndex) {
      setMode("random")
      return
    }

    const docHeight = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)
    const maxScroll = docHeight - window.innerHeight

    if (maxScroll <= 80) {
      setMode("random")
      return
    }

    const threshold = Math.min(240, maxScroll * 0.35)
    if (window.scrollY < threshold) {
      setMode("bottom")
    } else {
      setMode("top")
    }
  }

  const navigateRandom = async () => {
    try {
      const data = await fetchData
      const candidates = Object.keys(data).filter((slug) => {
        const lower = slug.toLowerCase()
        return (
          lower !== "index" &&
          lower !== "404" &&
          !lower.endsWith("/index") &&
          !lower.startsWith("tags/") &&
          lower !== currentSlug
        )
      })

      if (candidates.length === 0) return
      const randomSlug = candidates[Math.floor(Math.random() * candidates.length)]

      const iconHref =
        document.querySelector("link[rel='icon']")?.getAttribute("href") ?? "/static/icon.png"
      const staticIdx = iconHref.indexOf("static/")
      const basePath = staticIdx >= 0 ? iconHref.slice(0, staticIdx) : "/"
      const targetUrl = new URL(`${basePath}${randomSlug}`, window.location.href)

      if (typeof window.spaNavigate === "function") {
        window.spaNavigate(targetUrl, false)
      } else {
        window.location.href = targetUrl.toString()
      }
    } catch (err) {
      console.error("Random doc navigation failed:", err)
    }
  }

  const onClick = () => {
    const mode = (btn.dataset.mode as SmartMode) ?? "random"
    if (mode === "top") {
      window.scrollTo({ top: 0, behavior: "smooth" })
    } else if (mode === "bottom") {
      window.scrollTo({
        top: Math.max(document.body.scrollHeight, document.documentElement.scrollHeight),
        behavior: "smooth",
      })
    } else {
      navigateRandom()
    }
  }

  let ticking = false
  const onScroll = () => {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        updateMode()
        ticking = false
      })
      ticking = true
    }
  }

  btn.addEventListener("click", onClick)
  window.addEventListener("scroll", onScroll, { passive: true })
  window.addEventListener("resize", updateMode, { passive: true })

  window.addCleanup(() => {
    btn.removeEventListener("click", onClick)
    window.removeEventListener("scroll", onScroll)
    window.removeEventListener("resize", updateMode)
  })

  updateMode()
})
