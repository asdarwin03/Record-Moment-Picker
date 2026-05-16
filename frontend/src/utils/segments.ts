import type {
  EnrichedTranscriptItem,
  Segment,
  SummaryRef,
  SummaryRow,
} from '../types/finalResult'

export function getAnalysisDuration(segments: Segment[]) {
  return Math.max(...segments.map((segment) => segment.end_time), 0)
}

export function getTranscriptItems(segments: Segment[]): EnrichedTranscriptItem[] {
  return segments.flatMap((segment) =>
    segment.texts.map((text) => ({
      ...text,
      segmentSid: segment.sid,
      segmentTitle: segment.title,
    })),
  )
}

export function getSummaryRows(segments: Segment[]): SummaryRow[] {
  return segments.flatMap((segment) =>
    segment.summary.map((line, index) => ({
      id: `${segment.sid}-${index}`,
      line,
      segment,
      summaryIndex: index,
    })),
  )
}

export function findSegmentByTime(segments: Segment[], time: number) {
  return segments.find(
    (segment) => time >= segment.start_time && time <= segment.end_time,
  )
}

export function getSelectedSummaryRow(
  summaryRows: SummaryRow[],
  summaryRef: SummaryRef | null,
) {
  if (!summaryRef) {
    return null
  }

  return (
    summaryRows.find(
      (row) =>
        row.segment.sid === summaryRef.sid &&
        row.summaryIndex === summaryRef.summaryIndex,
    ) ?? null
  )
}

export function getEvidenceTexts(
  selectedSummaryRow: SummaryRow | null,
  transcriptItems: EnrichedTranscriptItem[],
) {
  const selectedClue = selectedSummaryRow?.segment.clues.find(
    (clue) => clue.summary_index === selectedSummaryRow.summaryIndex,
  )

  return transcriptItems.filter((text) => selectedClue?.clue.includes(text.t_id))
}
