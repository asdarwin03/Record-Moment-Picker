export type FolderCounts = {
  all: number
  byId: Record<string, number>
  unfiled: number
}

export type FolderSelection = string | null | undefined

export type RecordingSortDirection = 'asc' | 'desc'
