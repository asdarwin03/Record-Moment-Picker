import type { Recording } from '../types/finalResult'

function normalizeSearchText(value: string) {
  return value.trim().toLocaleLowerCase()
}

function collectPrimitiveValues(value: unknown): string[] {
  if (value == null) {
    return []
  }

  if (
    typeof value === 'string' ||
    typeof value === 'number' ||
    typeof value === 'boolean'
  ) {
    return [String(value)]
  }

  if (Array.isArray(value)) {
    return value.flatMap((item) => collectPrimitiveValues(item))
  }

  if (typeof value === 'object') {
    return Object.values(value).flatMap((item) => collectPrimitiveValues(item))
  }

  return []
}

export function recordingMatchesSearch(recording: Recording, query: string) {
  const normalizedQuery = normalizeSearchText(query)

  if (!normalizedQuery) {
    return true
  }

  const searchableText = collectPrimitiveValues(recording)
    .join(' ')
    .toLocaleLowerCase()

  return searchableText.includes(normalizedQuery)
}
