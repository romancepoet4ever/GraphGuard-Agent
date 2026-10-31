import dayjs from 'dayjs'

export function formatTime(value?: string) {
  if (!value) return 'n/a'
  const parsed = dayjs(value)
  return parsed.isValid() ? parsed.format('YYYY-MM-DD HH:mm:ss') : value
}

export function durationText(start?: string, end?: string) {
  if (!start) return 'n/a'
  const a = dayjs(start)
  const b = end ? dayjs(end) : dayjs()
  if (!a.isValid() || !b.isValid()) return 'n/a'
  const seconds = Math.max(0, b.diff(a, 'second'))
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  return `${minutes}m ${seconds % 60}s`
}

export function pct(value: number | undefined) {
  const safe = Number.isFinite(value) ? Number(value) : 0
  return `${Math.round(safe * 100)}%`
}

export function truncateMiddle(value: string, max = 28) {
  if (!value || value.length <= max) return value || 'n/a'
  const keep = Math.max(4, Math.floor((max - 3) / 2))
  return `${value.slice(0, keep)}...${value.slice(-keep)}`
}

export function asText(value: unknown, fallback = 'n/a') {
  if (value === null || value === undefined || value === '') return fallback
  return String(value)
}
