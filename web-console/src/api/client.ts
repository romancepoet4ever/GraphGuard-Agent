const DEFAULT_API_URL = 'http://127.0.0.1:8001'

export const API_BASE_URL = (import.meta.env.VITE_GRAPHGUARD_API_URL || DEFAULT_API_URL).replace(/\/$/, '')
export const STREAMLIT_URL = (import.meta.env.VITE_GRAPHGUARD_STREAMLIT_URL || 'http://127.0.0.1:8501').replace(/\/$/, '')

export class ApiError extends Error {
  status: number
  details: unknown

  constructor(message: string, status: number, details: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.details = details
  }
}

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
  })
  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json') ? await response.json() : await response.text()
  if (!response.ok) {
    const message = typeof payload === 'string' ? payload : JSON.stringify(payload)
    throw new ApiError(message || response.statusText, response.status, payload)
  }
  return payload as T
}

export function reportExportUrl(traceId: string, format: 'markdown' | 'pdf' = 'markdown') {
  return `${API_BASE_URL}/api/v1/reports/${encodeURIComponent(traceId)}/export?format=${format}`
}
