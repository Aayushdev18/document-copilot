import { useState, type FormEvent } from "react"
import { Navigate } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { api } from "@/lib/api"
import { useAuth } from "@/lib/auth"
import { ApiError, errorMessage } from "@/lib/http"

export function LoginPage() {
  const { session, signIn } = useAuth()
  const [email, setEmail] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  if (session) return <Navigate to="/" replace />

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setPending(true)
    setError(null)
    try {
      signIn(await api.createSession(email))
    } catch (caught) {
      setError(
        caught instanceof ApiError && caught.isNetworkError
          ? "The API is not running. Start the backend, then try again."
          : errorMessage(caught),
      )
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center px-4 py-12">
      <Card className="w-full max-w-md bg-card">
        <CardHeader>
          <p className="font-heading text-4xl tracking-tight text-primary">Driftwood</p>
          <CardTitle className="text-lg">Document Copilot</CardTitle>
          <CardDescription className="text-sm leading-6">
            A research desk for questions about SEC filings. This local workspace signs you in
            with an email and keeps the conversation on this machine.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-3" onSubmit={onSubmit}>
            <label htmlFor="email" className="text-sm font-medium">
              Work email
            </label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              placeholder="analyst@driftwood.example"
              onChange={(event) => setEmail(event.target.value)}
              className="h-10 bg-background"
            />
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="mt-2 h-10" disabled={pending}>
              {pending ? "Opening…" : "Open the desk"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
