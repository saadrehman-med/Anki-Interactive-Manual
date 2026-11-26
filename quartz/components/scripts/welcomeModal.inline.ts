const STORAGE_KEY = "anki-interactive-welcome-seen"

document.documentElement.setAttribute(
  "data-welcome-open",
  sessionStorage.getItem(STORAGE_KEY) ? "false" : "true",
)

document.addEventListener("nav", () => {
  const modal = document.getElementById("welcome-modal")
  if (!modal) return

  const close = () => {
    document.documentElement.setAttribute("data-welcome-open", "false")
    sessionStorage.setItem(STORAGE_KEY, "1")
  }

  const closeBtn = modal.querySelector(".welcome-modal-close")
  const confirmBtn = modal.querySelector(".welcome-modal-btn")

  const onBackdropClick = (e: MouseEvent) => {
    if (e.target === modal) close()
  }
  const onKeyDown = (e: KeyboardEvent) => {
    if (
      e.key === "Escape" &&
      document.documentElement.getAttribute("data-welcome-open") === "true"
    ) {
      close()
    }
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
})
