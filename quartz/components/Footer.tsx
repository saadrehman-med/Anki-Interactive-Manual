import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"
import style from "./styles/footer.scss"

interface Options {
  links: Record<string, string>
}

export default ((opts?: Options) => {
  const Footer: QuartzComponent = ({ displayClass }: QuartzComponentProps) => {
    const links = opts?.links ?? {}
    const entries = Object.entries(links)
    return (
      <footer class={`${displayClass ?? ""}`}>
        {entries.length > 0 && (
          <ul>
            {entries.map(([text, link]) => (
              <li>
                <a href={link}>{text}</a>
              </li>
            ))}
          </ul>
        )}
        <p class="footer-credit">
          Made with{" "}
          <span class="footer-heart" aria-label="love">
            &#x2665;&#xFE0E;
          </span>{" "}
          in Rawalpindi, Pakistan
        </p>
      </footer>
    )
  }

  Footer.css = style
  return Footer
}) satisfies QuartzComponentConstructor
