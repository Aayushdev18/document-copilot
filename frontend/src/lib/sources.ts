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

export function xbrlCitations(content: string, company: string, ticker: string): Citation[] {
  const links = filingLinks(content)
  if (links.length === 0) return []
  const blocks = content.split(/\n\n+/)
  return links.map((url, index) => {
    const block = blocks.find((item) => item.includes(url)) ?? content
    const filed = block.match(/filed (\d{4}-\d{2}-\d{2})/)?.[1] ?? ""
    const accession = block.match(/accession ([0-9-]+)/)?.[1] ?? String(index + 1)
    const passage = block.replace(url, "").trim()
    return {
      chunkId: `xbrl-${accession}-${index}`,
      label: "XBRL",
      excerpt: passage,
      passage,
      ticker,
      company,
      form: "10-K",
      filingDate: filed,
      section: "Item 8. Financial Statements",
      sourceUrl: url,
      locator: "Item 8 · SEC XBRL",
    }
  })
}
