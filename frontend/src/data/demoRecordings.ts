import finalResult from '../../../shared/examples/final-result.cross-topic-evidence.example.json'
import type { Recording, Segment, Tone } from '../types/finalResult'

export const demoSegments = normalizeDemoSegments(finalResult)

export const tones: Tone[] = ['purple', 'blue', 'green', 'orange']

export const initialRecordings: Recording[] = [
  {
    id: 'os',
    name: '운영체제 7강.m4a',
    date: '2026-03-21',
    status: 'waiting',
    segments: [],
  },
  {
    id: 'club',
    name: '동아리 회의.m4a',
    date: '2026-03-29',
    status: 'done',
    segments: demoSegments,
  },
]

export function getTone(index: number) {
  return tones[index % tones.length]
}

function normalizeDemoSegments(rawSegments: unknown): Segment[] {
  if (!Array.isArray(rawSegments)) {
    return []
  }

  return rawSegments.map((segment) => {
    type LegacyTranscriptItem = Segment['texts'][number] & { time?: number }
    const item = segment as Omit<Segment, 'texts'> & {
      texts: LegacyTranscriptItem[]
    }
    const texts = item.texts.map((text, index) => ({
      ...text,
      start_time: text.start_time ?? text.time ?? item.start_time,
      end_time:
        text.end_time ??
        item.texts[index + 1]?.start_time ??
        item.texts[index + 1]?.time ??
        item.end_time,
    }))

    return {
      ...item,
      start_time: texts.length > 0 ? Math.min(...texts.map((text) => text.start_time)) : item.start_time,
      end_time: texts.length > 0 ? Math.max(...texts.map((text) => text.end_time)) : item.end_time,
      texts,
    }
  })
}
