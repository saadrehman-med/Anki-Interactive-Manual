import { QuartzTransformerPlugin } from "../types"
import { Root, Blockquote, BlockContent, DefinitionContent, Heading, Paragraph } from "mdast"
import { Element, ElementContent, Root as HtmlRoot } from "hast"
import { toString as mdastToString } from "mdast-util-to-string"
import { toString as hastToString } from "hast-util-to-string"
import { PluggableList } from "unified"
import { visit } from "unist-util-visit"
import { JSResource, CSSResource } from "../../util/resources"
// @ts-ignore
import walkthroughScript from "../../components/scripts/walkthrough.inline"
import walkthroughStyle from "../../components/styles/walkthrough.inline.scss"

const WALKTHROUGH_HEADER_RE = /^\[!(mimik|walkthrough)\][ \t]*([^\n]*)(?:\n|$)/i

function makeMdastDiv(
  classNames: string[],
  children: (BlockContent | DefinitionContent)[],
  extraProps: Record<string, unknown> = {},
): Blockquote {
  return {
    type: "blockquote",
    data: {
      hName: "div",
      hProperties: {
        className: classNames,
        ...extraProps,
      },
    },
    children,
  }
}

function makeMdastEl(
  tag: string,
  classNames: string[],
  children: (BlockContent | DefinitionContent)[],
  extraProps: Record<string, unknown> = {},
): Blockquote {
  return {
    type: "blockquote",
    data: {
      hName: tag,
      hProperties: {
        className: classNames,
        ...extraProps,
      },
    },
    children,
  }
}

function makeMdastTextNode(tag: string, classNames: string[], text: string, extraProps: Record<string, unknown> = {}): Blockquote {
  return makeMdastEl(
    tag,
    classNames,
    [
      {
        type: "paragraph",
        data: { hName: "span" },
        children: [{ type: "text", value: text }],
      },
    ],
    extraProps,
  )
}

function isMediaParagraph(node: BlockContent | DefinitionContent): boolean {
  if (node.type !== "paragraph") return false
  const meaningful = node.children.filter(
    (c) => !(c.type === "text" && c.value.trim() === ""),
  )
  return meaningful.length > 0 && meaningful.every((c) => c.type === "image")
}

interface ParsedMdastStep {
  heading: string
  media: (BlockContent | DefinitionContent)[]
  caption: (BlockContent | DefinitionContent)[]
}

function buildMdastPlayer(
  node: Blockquote,
  title: string,
  intro: (BlockContent | DefinitionContent)[],
  steps: ParsedMdastStep[],
) {
  const header = makeMdastDiv(
    ["wt-header"],
    [
      makeMdastDiv(
        ["wt-header-text"],
        [
          {
            type: "html",
            value: `<span class="wt-kicker"><svg class="wt-kicker-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg><span>Walkthrough</span></span>`,
          },
          makeMdastTextNode("h3", ["wt-title"], title),
          makeMdastTextNode("span", ["wt-meta"], `${steps.length} steps`),
        ],
      ),
    ],
  )

  const stepNodes: Blockquote[] = steps.map((step, idx) => {
    const stepChildren: (BlockContent | DefinitionContent)[] = [
      makeMdastDiv(
        ["wt-step-body"],
        [
          makeMdastTextNode("h4", ["wt-step-heading"], step.heading),
          makeMdastDiv(["wt-step-caption"], step.caption),
        ],
      ),
    ]
    if (step.media.length > 0) {
      stepChildren.push(makeMdastDiv(["wt-media-stage"], step.media))
    }

    return makeMdastEl(
      "section",
      idx === 0 ? ["wt-step", "is-active"] : ["wt-step"],
      stepChildren,
      {
        "data-step-index": String(idx),
        "aria-hidden": idx === 0 ? "false" : "true",
      },
    )
  })

  const stage = makeMdastDiv(["wt-stage"], [makeMdastDiv(["wt-slides"], stepNodes)])

  const controls = makeMdastDiv(
    ["wt-controls"],
    [
      makeMdastTextNode("button", ["wt-btn", "wt-prev"], "← Previous", {
        type: "button",
        disabled: true,
      }),
      makeMdastDiv(
        ["wt-center-status"],
        [
          makeMdastTextNode("span", ["wt-counter"], `Step 1 of ${steps.length}`, {
            "aria-live": "polite",
          }),
          makeMdastDiv(["wt-indicators"], [], {
            role: "tablist",
            "aria-label": "Walkthrough steps",
          }),
        ],
      ),
      makeMdastDiv(
        ["wt-right-actions"],
        [
          makeMdastTextNode("button", ["wt-btn", "wt-btn-primary", "wt-next"], "Next →", {
            type: "button",
            disabled: steps.length <= 1,
          }),
          makeMdastTextNode("button", ["wt-btn", "wt-view-all"], "View all", {
            type: "button",
            "aria-pressed": "false",
          }),
        ],
      ),
    ],
  )

  const children: (BlockContent | DefinitionContent)[] = [header]
  if (intro.length > 0) {
    children.push(makeMdastDiv(["wt-intro"], intro))
  }
  children.push(stage, controls)

  node.data = {
    hName: "div",
    hProperties: {
      className: ["wt-player"],
      "data-walkthrough": title,
      tabIndex: 0,
    },
  }
  node.children = children
}

function makeHastEl(
  tagName: string,
  classNames: string[],
  children: ElementContent[],
  extraProps: Record<string, unknown> = {},
): Element {
  return {
    type: "element",
    tagName,
    properties: {
      className: classNames,
      ...extraProps,
    },
    children,
  }
}

function isHastMediaEl(node: ElementContent): boolean {
  if (node.type !== "element") return false
  if (node.tagName === "img") return true
  if (node.tagName === "p") {
    const meaningful = node.children.filter(
      (c) => !(c.type === "text" && c.value.trim() === ""),
    )
    return (
      meaningful.length > 0 &&
      meaningful.every((c) => c.type === "element" && c.tagName === "img")
    )
  }
  return false
}

function transformHastContainer(el: Element) {
  const rawTitle = el.properties?.dataWalkthrough ?? el.properties?.["data-walkthrough"]
  const title =
    typeof rawTitle === "string" && rawTitle.trim().length > 0
      ? rawTitle.trim()
      : "Interactive Walkthrough"

  const intro: ElementContent[] = []
  const steps: { heading: string; media: ElementContent[]; caption: ElementContent[] }[] = []
  let current: { heading: string; media: ElementContent[]; caption: ElementContent[] } | null = null

  for (const child of el.children) {
    if (child.type === "text" && child.value.trim() === "") continue
    if (child.type === "element" && child.tagName === "hr") continue
    if (child.type === "element" && child.tagName === "h2") {
      current = { heading: hastToString(child).trim(), media: [], caption: [] }
      steps.push(current)
      continue
    }
    if (!current) {
      intro.push(child)
    } else if (isHastMediaEl(child)) {
      current.media.push(child)
    } else {
      current.caption.push(child)
    }
  }

  if (steps.length === 0) return

  const header = makeHastEl("div", ["wt-header"], [
    makeHastEl("div", ["wt-header-text"], [
      makeHastEl("span", ["wt-kicker"], [{ type: "text", value: "Walkthrough" }]),
      makeHastEl("h3", ["wt-title"], [{ type: "text", value: title }]),
      makeHastEl("span", ["wt-meta"], [{ type: "text", value: `${steps.length} steps` }]),
    ]),
  ])

  const stepEls = steps.map((step, idx) => {
    const bodyChildren: ElementContent[] = [
      makeHastEl("div", ["wt-step-body"], [
        makeHastEl("h4", ["wt-step-heading"], [{ type: "text", value: step.heading }]),
        makeHastEl("div", ["wt-step-caption"], step.caption),
      ]),
    ]
    if (step.media.length > 0) {
      bodyChildren.push(makeHastEl("div", ["wt-media-stage"], step.media))
    }
    return makeHastEl("section", idx === 0 ? ["wt-step", "is-active"] : ["wt-step"], bodyChildren, {
      dataStepIndex: String(idx),
      ariaHidden: idx === 0 ? "false" : "true",
    })
  })

  const stage = makeHastEl("div", ["wt-stage"], [makeHastEl("div", ["wt-slides"], stepEls)])
  const controls = makeHastEl("div", ["wt-controls"], [
    makeHastEl("button", ["wt-btn", "wt-prev"], [{ type: "text", value: "← Previous" }], {
      type: "button",
      disabled: true,
    }),
    makeHastEl("div", ["wt-center-status"], [
      makeHastEl("span", ["wt-counter"], [{ type: "text", value: `Step 1 of ${steps.length}` }], {
        ariaLive: "polite",
      }),
      makeHastEl("div", ["wt-indicators"], [], {
        role: "tablist",
        ariaLabel: "Walkthrough steps",
      }),
    ]),
    makeHastEl("div", ["wt-right-actions"], [
      makeHastEl("button", ["wt-btn", "wt-btn-primary", "wt-next"], [{ type: "text", value: "Next →" }], {
        type: "button",
        disabled: steps.length <= 1,
      }),
      makeHastEl("button", ["wt-btn", "wt-view-all"], [{ type: "text", value: "View all" }], {
        type: "button",
        ariaPressed: "false",
      }),
    ]),
  ])

  el.tagName = "div"
  el.properties = {
    ...(el.properties ?? {}),
    className: ["wt-player"],
    dataWalkthrough: title,
    tabIndex: 0,
  }
  el.children = intro.length > 0 ? [header, makeHastEl("div", ["wt-intro"], intro), stage, controls] : [header, stage, controls]
}

/**
 * Guard against setext headings inside blockquotes: ensure a blank `>` line
 * precedes any `> ---` thematic break line.
 */
function guardBlockquoteHr(src: string): string {
  const lines = src.split(/\r?\n/)
  const out: string[] = []
  for (const line of lines) {
    if (/^[ \t]*>[ \t]*---+[ \t]*$/.test(line) && out.length > 0) {
      const prev = out[out.length - 1]
      if (!/^[ \t]*>[ \t]*$/.test(prev)) {
        out.push(">")
      }
    }
    out.push(line)
  }
  return out.join("\n")
}

export const Walkthrough: QuartzTransformerPlugin = () => {
  return {
    name: "Walkthrough",
    textTransform(_ctx, src) {
      return guardBlockquoteHr(src)
    },
    markdownPlugins() {
      const plugins: PluggableList = [
        () => {
          return (tree: Root, file) => {
            visit(tree, "blockquote", (node: Blockquote) => {
              if (!node.children || node.children.length === 0) return
              const first = node.children[0]
              if (first.type !== "paragraph") return

              const fullFirstText = mdastToString(first).trimStart()
              const match = WALKTHROUGH_HEADER_RE.exec(fullFirstText)
              if (!match) return

              const title = match[2].trim() || "Interactive Walkthrough"

              // Strip `[!mimik] Title` from first paragraph's leading text
              const remainingNodes = [...node.children]
              const firstPara = { ...first, children: [...first.children] } as Paragraph
              if (firstPara.children.length > 0 && firstPara.children[0].type === "text") {
                const stripped = firstPara.children[0].value.replace(WALKTHROUGH_HEADER_RE, "")
                if (stripped.trim().length > 0) {
                  firstPara.children[0] = { type: "text", value: stripped }
                  remainingNodes[0] = firstPara
                } else {
                  firstPara.children.shift()
                  if (firstPara.children.length > 0) {
                    remainingNodes[0] = firstPara
                  } else {
                    remainingNodes.shift()
                  }
                }
              }

              const intro: (BlockContent | DefinitionContent)[] = []
              const steps: ParsedMdastStep[] = []
              let currentStep: ParsedMdastStep | null = null

              for (const child of remainingNodes) {
                if (child.type === "thematicBreak") continue
                if (child.type === "heading" && (child as Heading).depth === 2) {
                  currentStep = {
                    heading: mdastToString(child).trim(),
                    media: [],
                    caption: [],
                  }
                  steps.push(currentStep)
                  continue
                }
                if (!currentStep) {
                  intro.push(child)
                } else if (isMediaParagraph(child)) {
                  currentStep.media.push(child)
                } else {
                  currentStep.caption.push(child)
                }
              }

              if (steps.length === 0) return
              file.data.hasWalkthrough = true
              buildMdastPlayer(node, title, intro, steps)
            })
          }
        },
      ]
      return plugins
    },
    htmlPlugins() {
      return [
        () => {
          return (tree: HtmlRoot, file) => {
            visit(tree, "element", (node: Element) => {
              const props = node.properties ?? {}
              const hasAttr =
                props.dataWalkthrough !== undefined || props["data-walkthrough"] !== undefined
              if (!hasAttr) return
              const classes = Array.isArray(props.className) ? props.className : []
              if (classes.includes("wt-player")) return
              file.data.hasWalkthrough = true
              transformHastContainer(node)
            })
          }
        },
      ]
    },
    externalResources() {
      const js: JSResource[] = [
        {
          script: walkthroughScript,
          loadTime: "afterDOMReady",
          contentType: "inline",
        },
      ]
      const css: CSSResource[] = [
        {
          content: walkthroughStyle,
          inline: true,
        },
      ]
      return { js, css }
    },
  }
}

declare module "vfile" {
  interface DataMap {
    hasWalkthrough?: boolean
  }
}
