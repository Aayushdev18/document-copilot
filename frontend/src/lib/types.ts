export type Session = {
  token: string
  email: string
  userId: string
}

export type ThreadSummary = {
  id: string
  title: string
  updatedAt: string
}

export type Citation = {
  chunkId: string
  label: string
  excerpt: string
  passage: string
  ticker: string
  company: string
  form: string
  filingDate: string
  section: string
  sourceUrl: string
  paragraph?: number
  locator?: string
}

export type ChatMessage = {
  id: string
  role: "user" | "assistant"
  content: string
  createdAt: string
  citations: Citation[]
}

export type ThreadDetail = {
  thread: ThreadSummary
  messages: ChatMessage[]
}

export type Filing = {
  ticker: string
  company: string
  form: string
  filingDate: string
  sourceUrl: string
  passageCount: number
}

export type Corpus = {
  documentCount: number
  passageCount: number
  filings: Filing[]
}

export type FactYear = {
  year: string
  end: string
  value: number
  display: string
  accession: string
  filed: string
  sourceUrl: string
}

export type FinancialMetric = {
  key: string
  label: string
  concept: string
  current: FactYear
  prior: FactYear
  change: string
}

export type CompanySnapshot = {
  ticker: string
  company: string
  form: string
  filingDate: string
  sourceUrl: string
  factsUrl: string
  industry: string
  overview: string
  metrics: FinancialMetric[]
  risks: { title: string; text: string; citation: Citation }[]
}

export type DeskPanel = "snapshot" | "risks" | "chat" | "brief" | "compare"

export type AnalystBrief = {
  ticker: string
  company: string
  sections: {
    id: string
    heading: string
    body: string
    citations: Citation[]
  }[]
}
