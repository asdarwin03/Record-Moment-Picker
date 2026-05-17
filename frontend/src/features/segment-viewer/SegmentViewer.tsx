import type { Segment } from '../../types/finalResult'
import { formatRange, formatTime } from '../../utils/time'

type SegmentViewerProps = {
  segment: Segment
  highlightedTextIds: string[]
  onHighlightTextIds: (ids: string[]) => void
  onSeek: (time: number) => void
}

export function SegmentViewer({
  segment,
  highlightedTextIds,
  onHighlightTextIds,
  onSeek,
}: SegmentViewerProps) {
  const clueBySummaryIndex = new Map(
    segment.clues.map((clue) => [clue.summary_index, clue.clue]),
  )

  return (
    <section className="segment-viewer" aria-labelledby="segment-title">
      <div className="segment-header">
        <div>
          <p className="eyebrow">{segment.sid}</p>
          <h2 id="segment-title">{segment.title}</h2>
        </div>
        <span>{formatRange(segment.start_time, segment.end_time)}</span>
      </div>

      <div className="detail-grid">
        <div className="detail-column">
          <h3>구간 요약</h3>
          <ol className="summary-list compact">
            {segment.summary.map((line, index) => {
              const clueIds = clueBySummaryIndex.get(index) ?? []

              return (
                <li key={line}>
                  <button
                    type="button"
                    onClick={() => onHighlightTextIds(clueIds)}
                  >
                    {line}
                  </button>
                </li>
              )
            })}
          </ol>
        </div>

        <div className="detail-column">
          <h3>원문 근거</h3>
          <div className="transcript-list">
            {segment.texts.map((text) => (
              <button
                className={
                  highlightedTextIds.includes(text.t_id)
                    ? 'transcript-item is-highlighted'
                    : 'transcript-item'
                }
                key={text.t_id}
                type="button"
                onClick={() => onSeek(text.start_time)}
              >
                <span>{formatTime(text.start_time)}</span>
                <p>{text.text}</p>
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
