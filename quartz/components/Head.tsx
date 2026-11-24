import { i18n } from "../i18n"
import { FullSlug, getFileExtension, joinSegments, pathToRoot } from "../util/path"
import { CSSResourceToStyleElement, JSResourceToScriptElement } from "../util/resources"
import { googleFontHref, googleFontSubsetHref } from "../util/theme"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"
import { unescapeHTML } from "../util/escape"
import { CustomOgImagesEmitterName } from "../plugins/emitters/ogImage"

export default (() => {
  const Head: QuartzComponent = ({
    cfg,
    fileData,
    externalResources,
    ctx,
  }: QuartzComponentProps) => {
    const titleSuffix = cfg.pageTitleSuffix ?? ""
    const title =
      (fileData.frontmatter?.title ?? i18n(cfg.locale).propertyDefaults.title) + titleSuffix
    const description =
      fileData.frontmatter?.socialDescription ??
      fileData.frontmatter?.description ??
      unescapeHTML(fileData.description?.trim() ?? i18n(cfg.locale).propertyDefaults.description)

    const { css, js, additionalHead } = externalResources

    const url = new URL(`https://${cfg.baseUrl ?? "example.com"}`)
    const path = (ctx.argv.serve ? "/" : url.pathname) as FullSlug
    const baseDir = fileData.slug === "404" ? path : pathToRoot(fileData.slug!)
    const iconPath = joinSegments(baseDir, "static/icon.png")

    const slug = fileData.slug ?? ""
    const socialUrl = slug === "404" ? url.toString() : joinSegments(url.toString(), slug)

    const cleanBase = url.toString().replace(/\/$/, "")
    const canonicalPath =
      slug === "index"
        ? ""
        : slug.endsWith("/index")
          ? slug.slice(0, -"/index".length)
          : slug
    const canonicalUrl = cfg.baseUrl
      ? canonicalPath
        ? `${cleanBase}/${canonicalPath}`
        : `${cleanBase}/`
      : undefined

    const usesCustomOgImage = ctx.cfg.plugins.emitters.some(
      (e) => e.name === CustomOgImagesEmitterName,
    )
    const ogImageDefaultPath = `https://${cfg.baseUrl}/static/og-image.png`
    const ogImageUrl = fileData.frontmatter?.socialImage
      ? fileData.frontmatter.socialImage.startsWith("http")
        ? fileData.frontmatter.socialImage
        : `https://${cfg.baseUrl}/static/${fileData.frontmatter.socialImage}`
      : usesCustomOgImage && fileData.filePath !== undefined
        ? `https://${cfg.baseUrl}/${slug}-og-image.webp`
        : ogImageDefaultPath

    const isHome = slug === "index"
    const isListOrSystem =
      slug === "404" || slug === "tags" || slug.startsWith("tags/") || slug.endsWith("/index")

    const schemaData =
      canonicalUrl && slug !== "404"
        ? isHome
          ? {
              "@context": "https://schema.org",
              "@type": "WebSite",
              name: cfg.pageTitle,
              description,
              url: canonicalUrl,
              license: "https://creativecommons.org/licenses/by-sa/4.0/",
              isBasedOn: "https://docs.ankiweb.net/",
            }
          : !isListOrSystem
            ? {
                "@context": "https://schema.org",
                "@type": "TechArticle",
                headline: title,
                description,
                url: canonicalUrl,
                image: ogImageUrl,
                license: "https://creativecommons.org/licenses/by-sa/4.0/",
                isBasedOn: "https://docs.ankiweb.net/",
                ...(fileData.dates?.published || fileData.dates?.created
                  ? {
                      datePublished: (
                        fileData.dates.published ?? fileData.dates.created
                      ).toISOString(),
                    }
                  : {}),
                ...(fileData.dates?.modified
                  ? { dateModified: fileData.dates.modified.toISOString() }
                  : {}),
                mainEntityOfPage: {
                  "@type": "WebPage",
                  "@id": canonicalUrl,
                },
              }
            : null
        : null

    return (
      <head>
        <title>{title}</title>
        <meta charSet="utf-8" />
        {cfg.theme.cdnCaching && cfg.theme.fontOrigin === "googleFonts" && (
          <>
            <link rel="preconnect" href="https://fonts.googleapis.com" />
            <link rel="preconnect" href="https://fonts.gstatic.com" />
            <link rel="stylesheet" href={googleFontHref(cfg.theme)} />
            {cfg.theme.typography.title && (
              <link rel="stylesheet" href={googleFontSubsetHref(cfg.theme, cfg.pageTitle)} />
            )}
          </>
        )}
        <link rel="preconnect" href="https://cdnjs.cloudflare.com" crossOrigin="anonymous" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />

        <meta name="og:site_name" content={cfg.pageTitle}></meta>
        <meta property="og:title" content={title} />
        <meta property="og:type" content="website" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={title} />
        <meta name="twitter:description" content={description} />
        <meta property="og:description" content={description} />
        <meta property="og:image:alt" content={description} />

        {!usesCustomOgImage && (
          <>
            <meta property="og:image" content={ogImageDefaultPath} />
            <meta property="og:image:url" content={ogImageDefaultPath} />
            <meta name="twitter:image" content={ogImageDefaultPath} />
            <meta
              property="og:image:type"
              content={`image/${getFileExtension(ogImageDefaultPath) ?? "png"}`}
            />
          </>
        )}

        {canonicalUrl && slug !== "404" && <link rel="canonical" href={canonicalUrl} />}

        {cfg.baseUrl && (
          <>
            <meta property="twitter:domain" content={cfg.baseUrl}></meta>
            <meta property="og:url" content={socialUrl}></meta>
            <meta property="twitter:url" content={socialUrl}></meta>
          </>
        )}

        {schemaData && (
          <script
            type="application/ld+json"
            dangerouslySetInnerHTML={{
              __html: JSON.stringify(schemaData).replace(/</g, "\\u003c"),
            }}
          />
        )}

        <link rel="icon" type="image/png" href={`${iconPath}?v=8`} data-persist="true" />
        <link
          rel="shortcut icon"
          href={`${joinSegments(baseDir, "favicon.ico")}?v=8`}
          data-persist="true"
        />
        <link rel="apple-touch-icon" href={`${iconPath}?v=8`} data-persist="true" />
        <meta name="description" content={description} />
        <meta name="robots" content="noai, noimageai" />
        <meta name="generator" content="Quartz" />

        {css.map((resource) => CSSResourceToStyleElement(resource, true))}
        {js
          .filter((resource) => resource.loadTime === "beforeDOMReady")
          .map((res) => JSResourceToScriptElement(res, true))}
        {additionalHead.map((resource) => {
          if (typeof resource === "function") {
            return resource(fileData)
          } else {
            return resource
          }
        })}
      </head>
    )
  }

  return Head
}) satisfies QuartzComponentConstructor
