import { ArrowUp } from "lucide-react"
import { useEffect, useRef, useState, type KeyboardEvent } from "react"

import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

type ComposerProps = {
  running: boolean
  placeholder?: string
  onSubmit: (question: string) => void
}

export function Composer({ running, placeholder = "Ask about a filing…", onSubmit }: ComposerProps) {
  const [value, setValue] = useState("")
  const field = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    field.current?.focus()
  }, [])

  function submit() {
    const question = value.trim()
    if (!question || running) return
    setValue("")
    onSubmit(question)
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <div className="border-t bg-background/90 px-4 py-4 backdrop-blur md:px-8">
      <form
        className="mx-auto flex w-full max-w-3xl items-end gap-2"
        onSubmit={(event) => {
          event.preventDefault()
          submit()
        }}
      >
        <Textarea
          ref={field}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          rows={2}
          className="min-h-14 flex-1 resize-none bg-card text-sm"
          aria-label="Question"
        />
        <Button type="submit" size="icon" className="size-10" disabled={running || !value.trim()}>
          <ArrowUp />
          <span className="sr-only">Ask</span>
        </Button>
      </form>
      <p className="mx-auto mt-2 max-w-3xl text-xs text-muted-foreground">
        Written from the loaded 10-Ks, with a citation on every claim. Not a recommendation.
      </p>
    </div>
  )
}
