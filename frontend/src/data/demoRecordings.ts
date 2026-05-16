import finalResult from '../../../shared/examples/final-result.cross-topic-evidence.example.json'
import type { Recording, Segment, Tone } from '../types/finalResult'

export const demoSegments = finalResult as Segment[]

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
