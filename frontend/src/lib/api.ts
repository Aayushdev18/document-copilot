import { ApiError, request, requestJson } from "@/lib/http"
import type {
  AnalystBrief,
  Citation,
  Comparison,
  CompanySnapshot,
  Corpus,
  Session,
  ThreadDetail,
  ThreadSummary,
} from "@/lib/types"

export type StreamHandler = (event: string, data: Record<string, unknown>) => void

async function readStream(response: Response, onEvent: StreamHandler): Promise<void> {
  if (!response.body) return
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const blocks = buffer.split("\n\n")
    buffer = blocks.pop() ?? ""
    for (const block of blocks) {
      let event = "message"
      let data = ""
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim()
        else if (line.startsWith("data:")) data += line.slice(5).trim()
      }
      if (data) {
        const parsed = JSON.parse(data) as Record<string, unknown>
        onEvent(event, parsed)
        if (event === "delta") {
          await new Promise((resolve) => setTimeout(resolve, 28))
        }
      }
    }
  }
}

export const api = {
  createSession(email: string) {
    return requestJson<Session>("/auth/session", { method: "POST", body: { email } })
  },
  corpus() {
    return requestJson<Corpus>("/corpus")
  },
  threads() {
    return requestJson<ThreadSummary[]>("/threads")
  },
  thread(threadId: string) {
    return requestJson<ThreadDetail>(`/threads/${threadId}`)
  },
  deleteThread(threadId: string) {
    return requestJson<void>(`/threads/${threadId}`, { method: "DELETE" })
  },
  snapshot(ticker: string) {
    return requestJson<CompanySnapshot>(`/companies/${ticker}`)
  },
  brief(ticker: string) {
    return requestJson<AnalystBrief>(`/companies/${ticker}/brief`, { method: "POST" })
  },
  compare(tickers: string[]) {
    return requestJson<Comparison>("/companies/compare", { method: "POST", body: { tickers } })
  },
  async streamChat(
    message: string,
    threadId: string | null,
    ticker: string,
    onEvent: StreamHandler,
  ) {
    const response = await request("/chat/stream", {
      method: "POST",
      body: { message, threadId, ticker },
    })
    if (!response.ok) {
      let detail = "The request failed."
      try {
        const payload = (await response.json()) as { detail?: string }
        if (typeof payload.detail === "string") detail = payload.detail
      } catch {
        detail = response.statusText || detail
      }
      throw new ApiError(detail, response.status, false)
    }
    await readStream(response, onEvent)
  },
}

export function isCitationList(value: unknown): value is Citation[] {
  return Array.isArray(value)
}
