let activeHeadingId: string | null = null

function updateActiveHeading() {
  const headings = Array.from(
    document.querySelectorAll<HTMLElement>(
      ".center article h1[id], .center article h2[id], .center article h3[id], .center article h4[id], .center article h5[id], .center article h6[id]",
    ),
  )
  if (headings.length === 0) return

  const scrollThreshold = 120
  let currentActive: HTMLElement | null = null

  for (const h of headings) {
    const top = h.getBoundingClientRect().top
    if (top <= scrollThreshold) {
      currentActive = h
    } else {
      break
    }
  }

  if (!currentActive && headings.length > 0) {
    const firstTop = headings[0].getBoundingClientRect().top
    if (firstTop < window.innerHeight * 0.5) {
      currentActive = headings[0]
    }
  }

  if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 50) {
    currentActive = headings[headings.length - 1]
  }

  const newId = currentActive ? currentActive.id : null
  if (newId === activeHeadingId) return
  activeHeadingId = newId

  document.querySelectorAll<HTMLAnchorElement>("ul.toc-content a[data-for]").forEach((link) => {
    const forId = link.getAttribute("data-for")
    if (forId === activeHeadingId) {
      link.classList.add("in-view")
      link.classList.add("active")

      // Smoothly scroll TOC container so the active item stays centered
      const container = link.closest<HTMLElement>("ul.toc-content")
      if (container) {
        const linkTop = link.offsetTop
        const linkHeight = link.offsetHeight
        const containerHeight = container.clientHeight
        const targetScroll = linkTop - containerHeight / 2 + linkHeight / 2

        container.scrollTo({
          top: Math.max(0, targetScroll),
          behavior: "smooth",
        })
      }
    } else {
      link.classList.remove("in-view")
      link.classList.remove("active")
    }
  })
}

function toggleToc(this: HTMLElement) {
  this.classList.toggle("collapsed")
  this.setAttribute(
    "aria-expanded",
    this.getAttribute("aria-expanded") === "true" ? "false" : "true",
  )
  const content = this.nextElementSibling as HTMLElement | undefined
  if (!content) return
  content.classList.toggle("collapsed")
}

function setupToc() {
  for (const toc of document.getElementsByClassName("toc")) {
    const button = toc.querySelector(".toc-header")
    const content = toc.querySelector(".toc-content")
    if (!button || !content) return
    button.addEventListener("click", toggleToc)
    window.addCleanup(() => button.removeEventListener("click", toggleToc))
  }
}

let scrollListener: (() => void) | null = null

document.addEventListener("nav", () => {
  setupToc()
  activeHeadingId = null

  if (scrollListener) {
    window.removeEventListener("scroll", scrollListener)
  }

  let ticking = false
  scrollListener = () => {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        updateActiveHeading()
        ticking = false
      })
      ticking = true
    }
  }

  window.addEventListener("scroll", scrollListener, { passive: true })
  window.addCleanup(() => {
    if (scrollListener) {
      window.removeEventListener("scroll", scrollListener)
      scrollListener = null
    }
  })

  updateActiveHeading()
})
