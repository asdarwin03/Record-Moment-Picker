export type TranscriptItem = {
  t_id: string
  start_time: number
  end_time: number
  text: string
}

export type ImportantMoment = {
  time: number
  title: string
}

export type SummaryClue = {
  summary_index: number
  clue: string[]
}

export type Segment = {
  sid: string
  start_time: number
  end_time: number
  title: string
  summary: string[]
  texts: TranscriptItem[]
  important: ImportantMoment[]
  clues: SummaryClue[]
}

export type Recording = {
  id: string
  name: string
  date: string
  status: 'waiting' | 'done' | 'failed'
  segments: Segment[]
  audioUrl?: string
  error_message?: string | null
  pipelineSettings?: PipelineSettings
  folderId?: string
  isHidden?: boolean
}

export type RecordingFolder = {
  id: string
  name: string
}

export type EnrichedTranscriptItem = TranscriptItem & {
  segmentSid: string
  segmentTitle: string
}

export type SummaryRef = {
  sid: string
  summaryIndex: number
}

export type SummaryRow = {
  id: string
  line: string
  segment: Segment
  summaryIndex: number
}

export type FloatingWindowState = {
  x: number
  y: number
  width: number
  height: number
}

export type Tone = 'purple' | 'blue' | 'green' | 'orange'
import type { PipelineSettings } from './pipelineSettings'
