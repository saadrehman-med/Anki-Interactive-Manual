import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"
import { classNames } from "../util/lang"
import style from "./styles/floatingButtons.scss"
// @ts-ignore
import script from "./scripts/floatingButtons.inline"

export default (() => {
  const FloatingButtons: QuartzComponent = ({ displayClass, fileData }: QuartzComponentProps) => {
    const isIndex = (fileData.slug ?? "").toLowerCase() === "index"
    const initialMode = isIndex ? "random" : "bottom"
    const initialTooltip = isIndex ? "Random doc" : "Scroll to bottom"

    return (
      <div class={classNames(displayClass, "floating-buttons")} aria-label="Quick actions">
        {/* Expand All / Collapse All Explorer Folders button */}
        <button
          type="button"
          id="fb-toggle-folders"
          class="fb-btn"
          data-state="expand"
          aria-label="Expand all folders"
          data-tooltip="Expand all"
        >
          <svg
            class="fb-icon fb-icon-expand"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="m7 15 5 5 5-5" />
            <path d="m7 9 5-5 5 5" />
          </svg>

          <svg
            class="fb-icon fb-icon-collapse"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="m7 20 5-5 5 5" />
            <path d="m7 4 5 5 5-5" />
          </svg>
        </button>

        {/* Smart adaptive button (Random doc / Scroll bottom / Scroll top) */}
        <button
          type="button"
          id="fb-smart-btn"
          class="fb-btn"
          data-mode={initialMode}
          aria-label={initialTooltip}
          data-tooltip={initialTooltip}
        >
          <svg
            class="fb-icon fb-icon-top"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <polyline points="18 15 12 9 6 15" />
          </svg>

          <svg
            class="fb-icon fb-icon-bottom"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>

          <svg
            class="fb-icon fb-icon-random"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <polyline points="16 3 21 3 21 8" />
            <line x1="4" y1="20" x2="21" y2="3" />
            <polyline points="21 16 21 21 16 21" />
            <line x1="15" y1="15" x2="21" y2="21" />
            <line x1="4" y1="4" x2="9" y2="9" />
          </svg>
        </button>
      </div>
    )
  }

  FloatingButtons.css = style
  FloatingButtons.afterDOMLoaded = script

  return FloatingButtons
}) satisfies QuartzComponentConstructor
