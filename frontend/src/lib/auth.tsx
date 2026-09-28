import { createContext, useContext, useMemo, useState, type ReactNode } from "react"

import { clearSession, readSession, writeSession } from "@/lib/session"
import type { Session } from "@/lib/types"

type AuthValue = {
  session: Session | null
  signIn: (session: Session) => void
  signOut: () => void
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(() => readSession())
  const value = useMemo<AuthValue>(
    () => ({
      session,
      signIn(next) {
        writeSession(next)
        setSession(next)
      },
      signOut() {
        clearSession()
        setSession(null)
      },
    }),
    [session],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error("useAuth must be used within AuthProvider")
  return value
}
