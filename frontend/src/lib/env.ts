type AuthMode = "local" | "supabase"

function required(name: string, value: string | undefined): string {
  if (!value) {
    throw new Error(`Missing ${name}. Set it in frontend/.env before starting the app.`)
  }
  return value
}

const authModeValue = import.meta.env.VITE_AUTH_MODE || "local"
if (authModeValue !== "local" && authModeValue !== "supabase") {
  throw new Error("VITE_AUTH_MODE must be 'local' or 'supabase'.")
}

const authMode = authModeValue as AuthMode

export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || "/api",
  authMode,
  supabaseUrl:
    authMode === "supabase"
      ? required("VITE_SUPABASE_URL", import.meta.env.VITE_SUPABASE_URL)
      : "",
  supabaseAnonKey:
    authMode === "supabase"
      ? required("VITE_SUPABASE_ANON_KEY", import.meta.env.VITE_SUPABASE_ANON_KEY)
      : "",
}
