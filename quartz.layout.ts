import { PageLayout, SharedLayout } from "./quartz/cfg"
import * as Component from "./quartz/components"

// components shared across all pages
export const sharedPageComponents: SharedLayout = {
  head: Component.Head(),
  header: [],
  afterBody: [
    Component.ConditionalRender({
      component: Component.Comments({
        provider: "giscus",
        options: {
          repo: "saadrehman-med/Anki-Interactive-Manual",
          repoId: "R_kgDOV33rzA",
          category: "General",
          categoryId: "DIC_kwDOV33rzM4DLvL9",
          mapping: "pathname",
          strict: false,
          reactionsEnabled: true,
          inputPosition: "top",
          lang: "en",
          lightTheme: "light",
          darkTheme: "dark",
        },
      }),
      condition: (page) => {
        const slug = (page.fileData.slug ?? "").toLowerCase()
        return (
          slug !== "index" &&
          !slug.endsWith("/index") &&
          slug !== "tags" &&
          !slug.startsWith("tags/") &&
          slug !== "404"
        )
      },
    }),
  ],
  footer: Component.Footer({
    links: {},
  }),
}

// components for pages that display a single page (e.g. a single note)
export const defaultContentPageLayout: PageLayout = {
  beforeBody: [
    Component.ConditionalRender({
      component: Component.Breadcrumbs(),
      condition: (page) => page.fileData.slug !== "index",
    }),
    Component.ArticleTitle(),
    Component.ConditionalRender({
      component: Component.ContentMeta(),
      condition: (page) => page.fileData.slug !== "index",
    }),
    Component.TagList(),
    Component.ConditionalRender({
      component: Component.DocsStats(),
      condition: (page) => page.fileData.slug === "index",
    }),
  ],
  left: [
    Component.PageTitle(),
    Component.MobileOnly(Component.Spacer()),
    Component.Flex({
      components: [
        { Component: Component.Search() },
        { Component: Component.Darkmode() },
        { Component: Component.ReaderMode() },
        { Component: Component.GitDiff() },
        { Component: Component.FloatingButtons() },
      ],
      gap: "0.75rem",
    }),
    Component.Explorer(),
    Component.SidebarFooter({
      manualUrl: "https://docs.ankiweb.net/",
      githubUrl: "https://github.com/saadrehman-med/Anki-Interactive-Manual",
      licenseUrl: "https://creativecommons.org/licenses/by-sa/4.0/",
    }),
  ],
  right: [
    Component.ConditionalRender({
      component: Component.Graph({
        localGraph: {
          depth: -1,
          scale: 0.45,
          repelForce: 0.4,
          centerForce: 0.35,
          linkDistance: 25,
          focusOnHover: true,
          enableRadial: true,
        },
      }),
      condition: (page) => (page.fileData.slug ?? "").toLowerCase() === "index",
    }),
    Component.ConditionalRender({
      component: Component.Graph(),
      condition: (page) => (page.fileData.slug ?? "").toLowerCase() !== "index",
    }),
    Component.DesktopOnly(Component.TableOfContents()),
    Component.Backlinks(),
  ],
}

// components for pages that display lists of pages  (e.g. tags or folders)
export const defaultListPageLayout: PageLayout = {
  beforeBody: [Component.Breadcrumbs(), Component.ArticleTitle(), Component.ContentMeta()],
  left: [
    Component.PageTitle(),
    Component.MobileOnly(Component.Spacer()),
    Component.Flex({
      components: [
        { Component: Component.Search() },
        { Component: Component.Darkmode() },
        { Component: Component.ReaderMode() },
        { Component: Component.GitDiff() },
        { Component: Component.FloatingButtons() },
      ],
      gap: "0.75rem",
    }),
    Component.Explorer(),
    Component.SidebarFooter({
      manualUrl: "https://docs.ankiweb.net/",
      githubUrl: "https://github.com/saadrehman-med/Anki-Interactive-Manual",
      licenseUrl: "https://creativecommons.org/licenses/by-sa/4.0/",
    }),
  ],
  right: [],
}
