import { QuartzComponent, QuartzComponentConstructor } from "./types"
import style from "./styles/welcomeModal.scss"
// @ts-ignore
import script from "./scripts/welcomeModal.inline"

export default (() => {
  const WelcomeModal: QuartzComponent = () => {
    return (
      <div
        id="welcome-modal"
        class="welcome-modal-backdrop"
        role="dialog"
        aria-modal="true"
        aria-label="Welcome notice"
        hidden
      >
        <div class="welcome-modal-card">
          <button
            type="button"
            class="welcome-modal-close"
            aria-label="Close welcome popup"
          >
            &times;
          </button>
          <p>
            Hello! I&apos;m a big fan of Anki, and I built this fan project to
            learn how to use GitHub, manage repositories, collaborate with
            others, and work with Quartz and a few other tools (listed below) to
            create my own personal website and projects.
          </p>
          <p>
            I&apos;ve tried to keep the content as faithful as possible to the
            official Anki Manual while adding a few extra features.
          </p>
          <p class="welcome-modal-disclaimer">
            Please note that this is an independent fan project and is not the
            official Anki Manual.
          </p>
          <div class="welcome-modal-actions">
            <button type="button" class="welcome-modal-btn">
              Continue
            </button>
          </div>
        </div>
      </div>
    )
  }

  WelcomeModal.css = style
  WelcomeModal.afterDOMLoaded = script

  return WelcomeModal
}) satisfies QuartzComponentConstructor
