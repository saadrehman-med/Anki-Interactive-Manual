import { pathToRoot } from "../util/path"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"
import { classNames } from "../util/lang"
import { i18n } from "../i18n"

const PageTitle: QuartzComponent = ({ fileData, cfg, displayClass }: QuartzComponentProps) => {
  const title = cfg?.pageTitle ?? i18n(cfg.locale).propertyDefaults.title
  const baseDir = pathToRoot(fileData.slug!)
  return (
    <h2 class={classNames(displayClass, "page-title")}>
      <a href={baseDir} class="page-title-link">
        <svg
          class="page-title-icon"
          viewBox="0 0 24 24"
          width="22"
          height="22"
          fill="currentColor"
          aria-hidden="true"
        >
          <path d="M12 2.25 14.95 8.23l6.6.96-4.78 4.66 1.13 6.57L12 17.32l-5.9 3.1 1.13-6.57L2.45 9.19l6.6-.96L12 2.25Z" />
        </svg>
        <span>{title}</span>
      </a>
    </h2>
  )
}

PageTitle.css = `
.page-title {
  font-size: 1.22rem;
  margin: 0;
  font-family: var(--titleFont);
  line-height: 1.2;
}
.page-title-link {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--dark);
  text-decoration: none;
  max-width: 100%;
  min-width: 0;
}
.page-title-link > span {
  min-width: 0;
  overflow-wrap: normal;
  word-break: normal;
}
.page-title-icon {
  flex-shrink: 0;
  color: var(--dark);
}
`

export default (() => PageTitle) satisfies QuartzComponentConstructor
