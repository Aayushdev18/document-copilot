import { env } from "@/lib/env"
import { readSession } from "@/lib/session"

export class ApiError extends Error {
  readonly status: number
  readonly isNetworkError: boolean

  constructor(message: string, status: number, isNetworkError = false) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.isNetworkError = isNetworkError
  }
}

type RequestOptions = {
  method?: string
  body?: unknown
}

function errorDetail(payload: unknown): string | null {
  if (!payload || typeof payload !== "object" || !("detail" in payload)) return null
  const detail = payload.detail
  if (typeof detail === "string") return detail
  if (Array.isArray(detail)) {
    const first = detail[0] as { msg?: unknown } | undefined
    if (first && typeof first.msg === "string") return first.msg
  }
  return null
}

export async function request(path: string, options: RequestOptions = {}): Promise<Response> {
  const session = readSession()
  const headers = new Headers()
  if (options.body !== undefined) headers.set("Content-Type", "application/json")
  if (session) headers.set("Authorization", `Bearer ${session.token}`)

  try {
    return await fetch(`${env.apiBaseUrl}${path}`, {
      method: options.method ?? "GET",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    })
  } catch {
    throw new ApiError("The research API could not be reached.", 0, true)
  }
}

export async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await request(path, options)
  if (!response.ok) {
    let detail: string | null = null
    try {
      detail = errorDetail(await response.json())
    } catch {
      detail = null
    }
    throw new ApiError(detail || "The request failed.", response.status, false)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  return "Something went wrong while reading the filings."
}
