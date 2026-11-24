// @ts-ignore
import gitDiffScript from "./scripts/gitdiff.inline"
import styles from "./styles/gitdiff.scss"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"
import { classNames } from "../util/lang"

const GitDiff: QuartzComponent = ({ displayClass, fileData }: QuartzComponentProps) => {
  const slug = fileData.slug ?? ""
  if (slug === "guides" || slug.startsWith("guides/")) {
    return null
  }
  return (
    <button
      type="button"
      class={classNames(displayClass, "gitdiff")}
      aria-label="-/+"
      aria-pressed="false"
      data-active="false"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="gitDiffIcon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <line x1="4.5" y1="7.5" x2="10.5" y2="7.5" />
        <line x1="15" y1="5" x2="9" y2="19" />
        <line x1="13.5" y1="16.5" x2="19.5" y2="16.5" />
        <line x1="16.5" y1="13.5" x2="16.5" y2="19.5" />
      </svg>
    </button>
  )
}

GitDiff.afterDOMLoaded = gitDiffScript
GitDiff.css = styles

export default (() => GitDiff) satisfies QuartzComponentConstructor
