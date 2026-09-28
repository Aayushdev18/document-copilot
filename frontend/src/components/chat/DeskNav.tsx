import { Plus, Trash2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import type { Corpus, ThreadSummary } from "@/lib/types"

type DeskNavProps = {
  threads: ThreadSummary[]
  activeId?: string
  corpus: Corpus | null
  email: string
  onNew: () => void
  onSelect: (threadId: string) => void
  onDelete: (threadId: string) => void
  onSignOut: () => void
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(
    new Date(value),
  )
}

export function DeskNav({
  threads,
  activeId,
  corpus,
  email,
  onNew,
  onSelect,
  onDelete,
  onSignOut,
}: DeskNavProps) {
  return (
    <div className="flex h-full min-h-0 flex-col bg-sidebar text-sidebar-foreground">
      <div className="px-5 pt-6 pb-4">
        <p className="font-heading text-2xl tracking-tight text-sidebar-primary">Driftwood</p>
        <p className="mt-1 text-sm text-sidebar-foreground/80">Document Copilot</p>
        <p className="mt-3 text-xs leading-5 text-sidebar-foreground/60">
          {corpus
            ? `${corpus.documentCount} latest 10-Ks · ${corpus.passageCount} passages`
            : "Loading the corpus"}
        </p>
        {corpus && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {corpus.filings.map((filing) => (
              <span
                key={filing.ticker}
                className="rounded-full border border-sidebar-border px-2 py-0.5 font-mono text-[10px] tracking-wide"
              >
                {filing.ticker}
              </span>
            ))}
          </div>
        )}
      </div>
      <div className="px-3">
        <Button
          type="button"
          className="h-9 w-full bg-sidebar-primary text-sidebar-primary-foreground hover:bg-sidebar-primary/90"
          onClick={onNew}
        >
          <Plus />
          New question
        </Button>
      </div>
      <ScrollArea className="mt-4 min-h-0 flex-1">
        <div className="flex flex-col gap-1 px-3 pb-4">
          <p className="px-2 pb-1 text-[11px] tracking-[0.14em] text-sidebar-foreground/50 uppercase">
            Recent
          </p>
          {threads.length === 0 && (
            <p className="px-2 py-3 text-sm text-sidebar-foreground/60">No questions yet.</p>
          )}
          {threads.map((thread) => {
            const active = thread.id === activeId
            return (
              <div key={thread.id} className="group flex items-start gap-1">
                <button
                  type="button"
                  onClick={() => onSelect(thread.id)}
                  className={`min-w-0 flex-1 rounded-lg px-2 py-2 text-left ${
                    active ? "bg-sidebar-accent" : "hover:bg-sidebar-accent/70"
                  }`}
                >
                  <span className="block truncate text-sm">{thread.title}</span>
                  <span className="mt-0.5 block text-[11px] text-sidebar-foreground/50">
                    {formatDate(thread.updatedAt)}
                  </span>
                </button>
                <button
                  type="button"
                  aria-label={`Delete ${thread.title}`}
                  onClick={() => onDelete(thread.id)}
                  className="mt-1 rounded-md p-1.5 text-sidebar-foreground/50 hover:bg-sidebar-accent hover:text-sidebar-foreground md:opacity-0 md:group-hover:opacity-100"
                >
                  <Trash2 className="size-3.5" />
                </button>
              </div>
            )
          })}
        </div>
      </ScrollArea>
      <div className="border-t border-sidebar-border px-4 py-4">
        <p className="truncate text-sm">{email}</p>
        <button
          type="button"
          onClick={onSignOut}
          className="mt-1 text-xs text-sidebar-foreground/60 underline-offset-2 hover:text-sidebar-foreground hover:underline"
        >
          Sign out
        </button>
      </div>
    </div>
  )
}
