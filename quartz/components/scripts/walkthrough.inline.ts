function initWalkthroughPlayer(player: HTMLElement) {
  if (player.dataset.wtInitialized === "true") return
  player.dataset.wtInitialized = "true"

  const steps = Array.from(player.querySelectorAll<HTMLElement>(":scope .wt-step"))
  if (steps.length === 0) return

  const prevBtn = player.querySelector<HTMLButtonElement>(":scope .wt-prev")
  const nextBtn = player.querySelector<HTMLButtonElement>(":scope .wt-next")
  const counterEl = player.querySelector<HTMLElement>(":scope .wt-counter")
  const viewAllBtn = player.querySelector<HTMLButtonElement>(":scope .wt-view-all")
  const indicatorsEl = player.querySelector<HTMLElement>(":scope .wt-indicators")

  let current = 0
  let viewAll = false
  const total = steps.length

  // Build step indicators: clickable dots if <= 12 steps, interactive progress bar if > 12 steps
  const dotButtons: HTMLButtonElement[] = []
  let progressTrack: HTMLElement | null = null
  let progressFill: HTMLElement | null = null

  if (indicatorsEl) {
    indicatorsEl.innerHTML = ""
    if (total <= 12) {
      indicatorsEl.classList.remove("is-progress")
      indicatorsEl.classList.add("is-dots")
      for (let i = 0; i < total; i++) {
        const dot = document.createElement("button")
        dot.type = "button"
        dot.className = "wt-dot"
        dot.setAttribute("role", "tab")
        dot.setAttribute("aria-label", `Go to step ${i + 1} of ${total}`)
        dot.setAttribute("aria-selected", i === 0 ? "true" : "false")
        const onClick = () => goTo(i)
        dot.addEventListener("click", onClick)
        window.addCleanup(() => dot.removeEventListener("click", onClick))
        indicatorsEl.appendChild(dot)
        dotButtons.push(dot)
      }
    } else {
      indicatorsEl.classList.remove("is-dots")
      indicatorsEl.classList.add("is-progress")
      progressTrack = document.createElement("div")
      progressTrack.className = "wt-progress-track"
      progressTrack.setAttribute("role", "slider")
      progressTrack.setAttribute("aria-label", "Walkthrough step progress")
      progressTrack.setAttribute("aria-valuemin", "1")
      progressTrack.setAttribute("aria-valuemax", String(total))
      progressTrack.setAttribute("aria-valuenow", "1")
      progressTrack.tabIndex = 0

      progressFill = document.createElement("div")
      progressFill.className = "wt-progress-fill"
      progressTrack.appendChild(progressFill)

      const onTrackClick = (e: MouseEvent) => {
        const rect = progressTrack!.getBoundingClientRect()
        if (rect.width <= 0) return
        const ratio = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width))
        const target = Math.min(total - 1, Math.floor(ratio * total))
        goTo(target)
      }
      progressTrack.addEventListener("click", onTrackClick)
      window.addCleanup(() => progressTrack!.removeEventListener("click", onTrackClick))
      indicatorsEl.appendChild(progressTrack)
    }
  }

  function render() {
    for (let i = 0; i < total; i++) {
      const active = !viewAll && i === current
      steps[i].classList.toggle("is-active", active)
      steps[i].setAttribute("aria-hidden", !viewAll && i !== current ? "true" : "false")
    }

    if (counterEl) {
      counterEl.textContent = viewAll ? `${total} steps` : `Step ${current + 1} of ${total}`
    }

    if (prevBtn) {
      prevBtn.disabled = viewAll || current <= 0
    }
    if (nextBtn) {
      nextBtn.disabled = viewAll || current >= total - 1
    }

    dotButtons.forEach((dot, i) => {
      const active = i === current
      dot.classList.toggle("is-active", active)
      dot.setAttribute("aria-selected", active ? "true" : "false")
    })

    if (progressTrack && progressFill) {
      const pct = ((current + 1) / total) * 100
      progressFill.style.width = `${pct}%`
      progressTrack.setAttribute("aria-valuenow", String(current + 1))
    }

    player.classList.toggle("is-view-all", viewAll)
    if (viewAllBtn) {
      viewAllBtn.textContent = viewAll ? "Slide view" : "View all"
      viewAllBtn.setAttribute("aria-pressed", viewAll ? "true" : "false")
    }
  }

  function goTo(index: number) {
    if (viewAll) {
      viewAll = false
    }
    current = Math.max(0, Math.min(total - 1, index))
    render()
  }

  const onPrev = () => goTo(current - 1)
  const onNext = () => goTo(current + 1)
  const onViewAll = () => {
    viewAll = !viewAll
    render()
  }

  const onKeyDown = (e: KeyboardEvent) => {
    const target = e.target as HTMLElement | null
    if (target && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return
    if (viewAll) return
    if (e.key === "ArrowLeft") {
      e.preventDefault()
      goTo(current - 1)
    } else if (e.key === "ArrowRight") {
      e.preventDefault()
      goTo(current + 1)
    }
  }

  prevBtn?.addEventListener("click", onPrev)
  nextBtn?.addEventListener("click", onNext)
  viewAllBtn?.addEventListener("click", onViewAll)
  player.addEventListener("keydown", onKeyDown)

  window.addCleanup(() => {
    prevBtn?.removeEventListener("click", onPrev)
    nextBtn?.removeEventListener("click", onNext)
    viewAllBtn?.removeEventListener("click", onViewAll)
    player.removeEventListener("keydown", onKeyDown)
    delete player.dataset.wtInitialized
  })

  render()
}

document.addEventListener("nav", () => {
  const players = Array.from(document.querySelectorAll<HTMLElement>(".wt-player, [data-walkthrough]"))
  for (const player of players) {
    initWalkthroughPlayer(player)
  }

  // Global keyboard shortcut when there's a single focused/visible player or first player in viewport
  const onDocKeyDown = (e: KeyboardEvent) => {
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return
    const activeEl = document.activeElement as HTMLElement | null
    if (activeEl && (activeEl.closest(".wt-player") || ["INPUT", "TEXTAREA", "SELECT"].includes(activeEl.tagName))) {
      return
    }
    const visiblePlayer = players.find((p) => {
      if (p.classList.contains("is-view-all")) return false
      const r = p.getBoundingClientRect()
      return r.bottom > 80 && r.top < window.innerHeight - 80
    })
    if (!visiblePlayer) return
    const btn = visiblePlayer.querySelector<HTMLButtonElement>(
      e.key === "ArrowLeft" ? ".wt-prev" : ".wt-next",
    )
    if (btn && !btn.disabled) {
      e.preventDefault()
      btn.click()
    }
  }

  document.addEventListener("keydown", onDocKeyDown)
  window.addCleanup(() => document.removeEventListener("keydown", onDocKeyDown))
})
