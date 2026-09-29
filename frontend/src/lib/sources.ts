import type { Citation } from "@/lib/types"

export function sectionTrail(section: string): string {
  const match = section.match(/Item\s+[\dA]+/i)
  if (!match) return section
  const item = match[0].replace(/\s+/g, " ")
  const upper = item.toUpperCase()
  if (upper === "ITEM 1A") return "Item 1A → Risk Factors"
  if (upper === "ITEM 7") return "Item 7 → MD&A"
  if (upper === "ITEM 1") return "Item 1 → Business"
  if (upper === "ITEM 8") return "Item 8 → Financial Statements"
  const rest = section.replace(/^Item\s+[\dA]+\.?\s*/i, "").trim()
  return rest ? `${item} → ${rest}` : item
}

export function sourceTrail(citation: Citation): string {
  const year = citation.filingDate.slice(0, 4)
  const paragraph = citation.paragraph ? ` · paragraph ${citation.paragraph}` : ""
  return `${citation.company} ${year} ${citation.form} → ${sectionTrail(citation.section)}${paragraph}`
}

export function filingLinks(content: string): string[] {
  const matches = content.match(/https:\/\/www\.sec\.gov\/\S+/g) ?? []
  return [...new Set(matches.map((url) => url.replace(/[).,]+$/, "")))]
}
