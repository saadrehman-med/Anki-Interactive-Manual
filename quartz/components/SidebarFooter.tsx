import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"
import { classNames } from "../util/lang"

interface Options {
  githubUrl?: string
  manualUrl?: string
  licenseUrl?: string
}

export default ((opts?: Options) => {
  const SidebarFooter: QuartzComponent = ({ displayClass }: QuartzComponentProps) => {
    const manualHref = opts?.manualUrl || "https://docs.ankiweb.net/"
    const githubHref = opts?.githubUrl || "https://github.com/ankitects/anki"
    const licenseHref = opts?.licenseUrl || "https://creativecommons.org/licenses/by-sa/4.0/"

    return (
      <div class={classNames(displayClass, "sidebar-bottom-links")}>
        <a
          href={manualHref}
          class="sidebar-social-link"
          aria-label="Official Anki Manual"
          title="Official Anki Manual (docs.ankiweb.net)"
          target="_blank"
          rel="noopener noreferrer"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="17"
            height="17"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
          </svg>
        </a>
        <a
          href={githubHref}
          class="sidebar-social-link"
          aria-label="Anki Interactive Manual on GitHub"
          title="Anki Interactive Manual on GitHub"
          target="_blank"
          rel="noopener noreferrer"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="17"
            height="17"
            viewBox="0 0 24 24"
            fill="currentColor"
          >
            <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
          </svg>
        </a>
        <a
          href={licenseHref}
          class="sidebar-social-link"
          aria-label="CC BY-SA 4.0 License"
          title="Licensed under CC BY-SA 4.0"
          target="_blank"
          rel="noopener noreferrer"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="17"
            height="17"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <path d="M14.83 14.83a4 4 0 1 1 0-5.66" />
          </svg>
        </a>
      </div>
    )
  }

  SidebarFooter.css = `
.sidebar-bottom-links {
  margin-top: auto;
  padding-top: 0.75rem;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1.1rem;
  flex-shrink: 0;
}

.sidebar-social-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--darkgray);
  transition: color 0.2s ease, transform 0.2s ease;

  &:hover {
    color: var(--dark);
    transform: translateY(-1px);
  }
}

:root[saved-theme="dark"] .sidebar-social-link {
  color: var(--gray);

  &:hover {
    color: var(--dark);
  }
}

@media all and (max-width: 800px) {
  .sidebar-bottom-links {
    display: none;
  }
}
`

  return SidebarFooter
}) satisfies QuartzComponentConstructor
