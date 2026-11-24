let isReaderMode = false
let readerModeArmed = false

const emitReaderModeChangeEvent = (mode: "on" | "off") => {
  const event: CustomEventMap["readermodechange"] = new CustomEvent("readermodechange", {
    detail: { mode },
  })
  document.dispatchEvent(event)
}

document.addEventListener("nav", () => {
  const setReaderMode = (on: boolean) => {
    isReaderMode = on
    const newMode = isReaderMode ? "on" : "off"
    document.documentElement.setAttribute("reader-mode", newMode)
    emitReaderModeChangeEvent(newMode)
  }

  const switchReaderMode = () => {
    const turningOn = !isReaderMode
    readerModeArmed = false
    setReaderMode(turningOn)
  }

  for (const readerModeButton of document.getElementsByClassName("readermode")) {
    readerModeButton.addEventListener("click", switchReaderMode)
    window.addCleanup(() => readerModeButton.removeEventListener("click", switchReaderMode))
  }

  const leftSidebar = document.querySelector(".sidebar.left") as HTMLElement | null
  const rightSidebar = document.querySelector(".sidebar.right") as HTMLElement | null

  const onLeftLeave = () => {
    if (isReaderMode) {
      readerModeArmed = true
    }
  }

  const onLeftEnter = () => {
    if (isReaderMode && readerModeArmed) {
      readerModeArmed = false
      setReaderMode(false)
    }
  }

  const onRightEnter = () => {
    if (isReaderMode) {
      readerModeArmed = false
      setReaderMode(false)
    }
  }

  if (leftSidebar) {
    leftSidebar.addEventListener("mouseleave", onLeftLeave)
    leftSidebar.addEventListener("mouseenter", onLeftEnter)
    window.addCleanup(() => {
      leftSidebar.removeEventListener("mouseleave", onLeftLeave)
      leftSidebar.removeEventListener("mouseenter", onLeftEnter)
    })
  }

  if (rightSidebar) {
    rightSidebar.addEventListener("mouseenter", onRightEnter)
    window.addCleanup(() => {
      rightSidebar.removeEventListener("mouseenter", onRightEnter)
    })
  }

  document.documentElement.setAttribute("reader-mode", isReaderMode ? "on" : "off")
})
