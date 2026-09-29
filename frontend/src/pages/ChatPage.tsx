import { Menu } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { Outlet, useNavigate, useParams } from "react-router-dom"

import { Composer } from "@/components/chat/Composer"
import { DeskNav } from "@/components/chat/DeskNav"
import { SourceSheet } from "@/components/chat/SourceSheet"
import { Transcript } from "@/components/chat/Transcript"
import { CompanyDesk } from "@/components/desk/CompanyDesk"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent } from "@/components/ui/sheet"
import { api, isCitationList } from "@/lib/api"
import { useAuth } from "@/lib/auth"
import { ApiError, errorMessage } from "@/lib/http"
import type {
  AnalystBrief,
  ChatMessage,
  Citation,
  CompanySnapshot,
  Corpus,
  DeskPanel,
  ThreadSummary,
} from "@/lib/types"

function filingPrompts(currentYear: string, priorYear: string): string[] {
  return [
    "Why did revenue increase?",
    "What are the major risks?",
    "How did profitability change?",
    `What changed from ${priorYear} to ${currentYear}?`,
    "Summarize management's outlook",
  ]
}

export function ChatPage() {
  const { threadId } = useParams()
  const navigate = useNavigate()
  const { session, signOut } = useAuth()
  const [threads, setThreads] = useState<ThreadSummary[]>([])
  const [corpus, setCorpus] = useState<Corpus | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [streaming, setStreaming] = useState("")
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [navOpen, setNavOpen] = useState(false)
  const [citation, setCitation] = useState<Citation | null>(null)
  const [ticker, setTicker] = useState("AAPL")
  const [panel, setPanel] = useState<DeskPanel>("snapshot")
  const [snapshots, setSnapshots] = useState<Record<string, CompanySnapshot>>({})
  const [brief, setBrief] = useState<AnalystBrief | null>(null)
  const [briefing, setBriefing] = useState(false)
  const [briefError, setBriefError] = useState<string | null>(null)
  const skipLoad = useRef<string | null>(null)
  const citations = useRef<Citation[]>([])

  useEffect(() => {
    if (!session) return
    let cancelled = false
    api
      .corpus()
      .then((next) => {
        if (!cancelled) setCorpus(next)
      })
      .catch((caught) => {
        if (!cancelled) setError(errorMessage(caught))
      })
    return () => {
      cancelled = true
    }
  }, [session])

  async function refreshThreads() {
    setThreads(await api.threads())
  }

  useEffect(() => {
    if (!session) return
    let cancelled = false
    refreshThreads().catch((caught) => {
      if (!cancelled) handleFailure(caught)
    })
    return () => {
      cancelled = true
    }
    // Refresh the desk list when the signed-in analyst changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session])

  useEffect(() => {
    if (!session) return
    if (!threadId) {
      if (!running) setMessages([])
      return
    }
    if (skipLoad.current === threadId) {
      skipLoad.current = null
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    setMessages([])
    api
      .thread(threadId)
      .then((detail) => {
        if (!cancelled) setMessages(detail.messages)
      })
      .catch((caught) => {
        if (!cancelled) handleFailure(caught)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
    // Reloading on every running change would wipe an in-flight answer.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [threadId, session])

  function handleFailure(caught: unknown) {
    if (caught instanceof ApiError && caught.status === 401) {
      signOut()
      navigate("/login", { replace: true })
      return
    }
    setError(errorMessage(caught))
  }

  useEffect(() => {
    if (!session || !corpus) return
    let cancelled = false
    Promise.all(corpus.filings.map((filing) => api.snapshot(filing.ticker)))
      .then((rows) => {
        if (cancelled) return
        setSnapshots(Object.fromEntries(rows.map((row) => [row.ticker, row])))
      })
      .catch((caught) => {
        if (!cancelled) setError(errorMessage(caught))
      })
    return () => {
      cancelled = true
    }
  }, [session, corpus])

  async function generateBrief() {
    setBriefing(true)
    setBriefError(null)
    setPanel("brief")
    try {
      setBrief(await api.brief(ticker))
    } catch (caught) {
      setBrief(null)
      setBriefError(errorMessage(caught))
    } finally {
      setBriefing(false)
    }
  }

  async function ask(question: string) {
    if (!session || running) return
    setPanel("chat")
    setError(null)
    setRunning(true)
    setStreaming("")
    citations.current = []
    const optimistic: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
      createdAt: new Date().toISOString(),
      citations: [],
    }
    setMessages((current) => [...current, optimistic])
    let nextThreadId = threadId ?? null
    let assembled = ""
    try {
      await api.streamChat(question, threadId ?? null, ticker, (event, data) => {
        if (event === "thread" && typeof data.id === "string") {
          nextThreadId = data.id
          if (!threadId) skipLoad.current = data.id
        } else if (event === "delta" && typeof data.text === "string") {
          assembled += data.text
          setStreaming(assembled)
        } else if (event === "citations" && isCitationList(data.citations)) {
          citations.current = data.citations
        }
      })
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: assembled,
          createdAt: new Date().toISOString(),
          citations: citations.current,
        },
      ])
      setStreaming("")
      await refreshThreads()
      if (!threadId && nextThreadId) navigate(`/c/${nextThreadId}`, { replace: true })
    } catch (caught) {
      handleFailure(caught)
    } finally {
      setRunning(false)
    }
  }

  async function removeThread(id: string) {
    try {
      await api.deleteThread(id)
      if (id === threadId) navigate("/", { replace: true })
      await refreshThreads()
    } catch (caught) {
      handleFailure(caught)
    }
  }

  if (!session) return null

  const snapshot = snapshots[ticker] ?? null
  const currentYear = snapshot?.metrics[0]?.current.year ?? "this year"
  const priorYear = snapshot?.metrics[0]?.prior.year ?? "last year"

  const nav = (
    <DeskNav
      threads={threads}
      activeId={threadId}
      corpus={corpus}
      email={session.email}
      onNew={() => {
        setNavOpen(false)
        navigate("/")
      }}
      onSelect={(id) => {
        setNavOpen(false)
        navigate(`/c/${id}`)
      }}
      onDelete={(id) => {
        void removeThread(id)
      }}
      onSignOut={() => {
        signOut()
        navigate("/login", { replace: true })
      }}
    />
  )

  return (
    <div className="flex h-full min-h-0">
      <aside className="hidden w-72 shrink-0 md:block">{nav}</aside>
      <Sheet open={navOpen} onOpenChange={setNavOpen}>
        <SheetContent side="left" className="w-72 p-0 sm:max-w-xs" showCloseButton={false}>
          {nav}
        </SheetContent>
      </Sheet>
        <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-2 border-b px-3 py-2 md:hidden">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label="Open conversations"
            onClick={() => setNavOpen(true)}
          >
            <Menu />
          </Button>
          <p className="font-heading text-lg">Document Copilot</p>
        </header>
        <CompanyDesk
          filings={corpus?.filings ?? []}
          ticker={ticker}
          panel={panel}
          snapshots={snapshots}
          brief={brief}
          briefError={briefError}
          briefing={briefing}
          onSelect={(next) => {
            setTicker(next)
            setBrief(null)
            setBriefError(null)
          }}
          onPanel={setPanel}
          onBrief={() => {
            void generateBrief()
          }}
          onOpenCitation={setCitation}
        />
        {panel === "chat" &&
          (loading ? (
            <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
              Opening the conversation…
            </div>
          ) : (
            <Transcript
              messages={messages}
              streaming={streaming}
              running={running}
              error={error}
              companyName={snapshot?.company ?? ticker}
              prompts={filingPrompts(currentYear, priorYear)}
              onSuggest={(question) => {
                void ask(question)
              }}
              onOpenCitation={setCitation}
            />
          ))}
        {panel === "chat" && (
          <Composer
            running={running}
            placeholder={`Ask ${snapshot?.company ?? ticker} about its 10-K…`}
            onSubmit={(question) => void ask(question)}
          />
        )}
      </main>
      <SourceSheet citation={citation} onClose={() => setCitation(null)} />
      <Outlet />
    </div>
  )
}
