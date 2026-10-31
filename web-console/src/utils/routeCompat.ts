export function traceIdFromQuery(search: string) {
  const params = new URLSearchParams(search)
  return params.get('trace_id') || params.get('traceId') || ''
}
