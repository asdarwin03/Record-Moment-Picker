import type { Segment } from '../../types/finalResult'

type SummaryPanelProps = {
  segments: Segment[]
}

export function SummaryPanel({ segments }: SummaryPanelProps) {
  const summaryCount = segments.reduce(
    (total, segment) => total + segment.summary.length,
    0,
  )
  const importantCount = segments.reduce(
    (total, segment) => total + segment.important.length,
    0,
  )

  return (
    <section className="summary-panel" aria-labelledby="summary-title">
      <div className="section-heading">
        <p className="eyebrow">Overview</p>
        <h2 id="summary-title">전체 요약</h2>
      </div>

      <div className="metric-grid">
        <div>
          <strong>{segments.length}</strong>
          <span>구간</span>
        </div>
        <div>
          <strong>{summaryCount}</strong>
          <span>요약</span>
        </div>
        <div>
          <strong>{importantCount}</strong>
          <span>중요 순간</span>
        </div>
      </div>

      <ol className="summary-list">
        {segments.flatMap((segment) =>
          segment.summary.map((line) => (
            <li key={`${segment.sid}-${line}`}>{line}</li>
          )),
        )}
      </ol>
    </section>
  )
}
