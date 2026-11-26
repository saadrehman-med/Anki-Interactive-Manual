const STORAGE_KEY = "anki-interactive-welcome-seen"

function setupWelcomeModal() {
  const modal = document.getElementById("welcome-modal")
  if (!modal) return

  if (!sessionStorage.getItem(STORAGE_KEY)) {
    modal.removeAttribute("hidden")
  }

  const close = () => {
    modal.setAttribute("hidden", "")
    sessionStorage.setItem(STORAGE_KEY, "1")
  }

  const closeBtn = modal.querySelector(".welcome-modal-close")
  const confirmBtn = modal.querySelector(".welcome-modal-btn")

  const onBackdropClick = (e: MouseEvent) => {
    if (e.target === modal) close()
  }
  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Escape" && !modal.hasAttribute("hidden")) close()
  }

  closeBtn?.addEventListener("click", close)
  confirmBtn?.addEventListener("click", close)
  modal.addEventListener("click", onBackdropClick)
  document.addEventListener("keydown", onKeyDown)

  window.addCleanup(() => {
    closeBtn?.removeEventListener("click", close)
    confirmBtn?.removeEventListener("click", close)
    modal.removeEventListener("click", onBackdropClick)
    document.removeEventListener("keydown", onKeyDown)
  })
}

document.addEventListener("nav", setupWelcomeModal)
setupWelcomeModal()
