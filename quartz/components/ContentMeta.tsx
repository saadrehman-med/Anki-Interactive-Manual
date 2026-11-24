import { Date } from "./Date"
import { QuartzComponentConstructor, QuartzComponentProps } from "./types"
import readingTime from "reading-time"
import { classNames } from "../util/lang"
import { i18n } from "../i18n"
import { JSX } from "preact"
import style from "./styles/contentMeta.scss"

interface ContentMetaOptions {
  /**
   * Whether to display reading time
   */
  showReadingTime: boolean
  showComma: boolean
}

const defaultOptions: ContentMetaOptions = {
  showReadingTime: true,
  showComma: true,
}

export default ((opts?: Partial<ContentMetaOptions>) => {
  const options: ContentMetaOptions = { ...defaultOptions, ...opts }

  function ContentMetadata({ cfg, fileData, displayClass }: QuartzComponentProps) {
    const text = fileData.text

    if (text) {
      const leftSegments: (string | JSX.Element)[] = []

      if (fileData.dates) {
        const createdDate = fileData.dates.created
        const modifiedDate = fileData.dates.modified

        const createdStr = createdDate ? createdDate.toISOString().slice(0, 10) : null
        const modifiedStr = modifiedDate ? modifiedDate.toISOString().slice(0, 10) : null

        if (createdDate && modifiedDate && createdStr !== modifiedStr) {
          leftSegments.push(
            <span>
              <Date date={createdDate} locale={cfg.locale} />{" "}
              <span class="meta-subtext">
                (updated <Date date={modifiedDate} locale={cfg.locale} />)
              </span>
            </span>,
          )
        } else if (createdDate || modifiedDate) {
          const dateToShow = (createdDate ?? modifiedDate)!
          leftSegments.push(
            <span>
              <Date date={dateToShow} locale={cfg.locale} />
            </span>,
          )
        }
      }

      if (options.showReadingTime) {
        const { minutes, words: _words } = readingTime(text)
        const displayedTime = i18n(cfg.locale).components.contentMeta.readingTime({
          minutes: Math.ceil(minutes),
        })
        leftSegments.push(<span>{displayedTime}</span>)
      }

      let editLink: JSX.Element | null = null
      if (fileData.slug && fileData.slug !== "index") {
        const title = fileData.frontmatter?.title ?? fileData.slug
        const issueUrl = `https://github.com/saadrehman-med/Anki-Interactive-Manual/issues/new?template=manual-feedback.yml&title=${encodeURIComponent(
          `[Feedback]: ${title}`,
        )}&page=${encodeURIComponent(`${title} (${fileData.slug})`)}`

        editLink = (
          <a
            href={issueUrl}
            target="_blank"
            rel="noopener noreferrer"
            class="suggest-edit-link"
            title="Report an issue, broken walkthrough, or suggest an edit"
          >
            <span>Suggest an edit</span>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.2"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path d="M7 17 17 7" />
              <path d="M7 7h10v10" />
            </svg>
          </a>
        )
      }

      return (
        <div class={classNames(displayClass, "content-meta-container")}>
          <p class="content-meta-left">
            {leftSegments.map((segment, index) => (
              <>
                {index > 0 && <span class="meta-separator">•</span>}
                {segment}
              </>
            ))}
          </p>
          {editLink && <div class="content-meta-right">{editLink}</div>}
        </div>
      )
    } else {
      return null
    }
  }

  ContentMetadata.css = style

  return ContentMetadata
}) satisfies QuartzComponentConstructor
