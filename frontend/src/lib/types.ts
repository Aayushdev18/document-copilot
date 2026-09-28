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
