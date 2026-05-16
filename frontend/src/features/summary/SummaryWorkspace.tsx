import type { Segment, SummaryRef, SummaryRow } from '../../types/finalResult'
import { getTone } from '../../data/demoRecordings'
import { formatRange, formatTime } from '../../utils/time'

type SummaryWorkspaceProps = {
  openSummaryRefs: SummaryRef[]
  selectedSid: string
  segments: Segment[]
  summaryRows: SummaryRow[]
  onOpenDocument: () => void
  onSeek: (time: number) => void
  onSelectSegment: (segment: Segment) => void
  onSelectSummary: (segment: Segment, summaryIndex: number) => void
}

export function SummaryWorkspace({
  openSummaryRefs,
  selectedSid,
  segments,
  summaryRows,
  onOpenDocument,
  onSeek,
  onSelectSegment,
  onSelectSummary,
}: SummaryWorkspaceProps) {
  return (
    <div className="summary-frame">
      <article className="summary-document">
        <div className="document-head">
          <h2>전체 요약</h2>
          <button type="button" onClick={onOpenDocument}>
            전체 녹음 문서 보기
          </button>
        </div>

        {segments.length === 0 ? (
          <p className="empty-state">분석 완료 후 요약이 표시됩니다.</p>
        ) : (
          <div className="summary-scroll">
            <ol className="full-summary">
              {summaryRows.map((row) => (
                <li key={row.id}>
                  <button
                    className={
                      openSummaryRefs.some(
                        (ref) =>
                          ref.sid === row.segment.sid &&
                          ref.summaryIndex === row.summaryIndex,
                      )
                        ? 'selected'
                        : ''
                    }
                    type="button"
                    onClick={() => onSelectSummary(row.segment, row.summaryIndex)}
                  >
                    {row.line}
                  </button>
                </li>
              ))}
            </ol>

            <div className="section-summary">
              <h3>구간별 주제</h3>
              {segments.map((segment, index) => (
                <button
                  className={`summary-topic ${getTone(index)} ${
                    segment.sid === selectedSid ? 'selected' : ''
                  }`}
                  key={segment.sid}
                  type="button"
                  onClick={() => onSelectSegment(segment)}
                >
                  <span>{formatRange(segment.start_time, segment.end_time)}</span>
                  <span>{segment.title}</span>
                </button>
              ))}
            </div>

            <div className="important-box">
              <h3>중요한 순간</h3>
              {segments.flatMap((segment) =>
                segment.important.map((moment) => (
                  <button
                    key={`${segment.sid}-${moment.time}`}
                    type="button"
                    onClick={() => onSeek(moment.time)}
                  >
                    <strong>{formatTime(moment.time)}</strong>
                    <span>{moment.title}</span>
                  </button>
                )),
              )}
            </div>
          </div>
        )}
      </article>
    </div>
  )
}
