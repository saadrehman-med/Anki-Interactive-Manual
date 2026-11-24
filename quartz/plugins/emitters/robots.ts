import { QuartzEmitterPlugin } from "../types"
import { write } from "./helpers"
import { FullSlug } from "../../util/path"

const ROBOTS_TXT = `# Block AI / LLM chatbots, scrapers, and training crawlers
User-agent: GPTBot
Disallow: /

User-agent: ChatGPT-User
Disallow: /

User-agent: OAI-SearchBot
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: Claude-Web
Disallow: /

User-agent: anthropic-ai
Disallow: /

User-agent: Google-Extended
Disallow: /

User-agent: GoogleOther
Disallow: /

User-agent: PerplexityBot
Disallow: /

User-agent: Perplexity-User
Disallow: /

User-agent: Applebot-Extended
Disallow: /

User-agent: Meta-ExternalAgent
Disallow: /

User-agent: Meta-ExternalFetcher
Disallow: /

User-agent: FacebookBot
Disallow: /

User-agent: CCBot
Disallow: /

User-agent: Bytespider
Disallow: /

User-agent: Amazonbot
Disallow: /

User-agent: cohere-ai
Disallow: /

User-agent: Diffbot
Disallow: /

User-agent: YouBot
Disallow: /

User-agent: DuckAssistBot
Disallow: /

User-agent: AI2Bot
Disallow: /

User-agent: Ai2Bot-Dolma
Disallow: /

User-agent: MistralAI-User
Disallow: /

User-agent: DeepSeekBot
Disallow: /

User-agent: Timpibot
Disallow: /

User-agent: Omgilibot
Disallow: /

User-agent: Omgili
Disallow: /

User-agent: Webzio-Extended
Disallow: /

User-agent: ImagesiftBot
Disallow: /

User-agent: Kangaroo Bot
Disallow: /

User-agent: xAI-Bot
Disallow: /

User-agent: GrokBot
Disallow: /

# Allow standard search engines
User-agent: *
Allow: /
`

export const RobotsTxt: QuartzEmitterPlugin = () => ({
  name: "RobotsTxt",
  async emit(ctx) {
    const baseUrl =
      ctx.cfg.configuration.baseUrl ?? "saadrehman-med.github.io/Anki-Interactive-Manual"
    const content = `${ROBOTS_TXT}\nSitemap: https://${baseUrl.replace(/^https?:\/\//, "").replace(/\/+$/, "")}/sitemap.xml\n`
    const path = await write({
      ctx,
      content,
      slug: "robots" as FullSlug,
      ext: ".txt",
    })
    return [path]
  },
  async *partialEmit() {},
})
