import type { Segment } from '../../types/finalResult'
import { formatRange, formatTime } from '../../utils/time'

type TimelineProps = {
  segments: Segment[]
  selectedSid: string
  duration: number
  onSelectSegment: (sid: string) => void
  onSeek: (time: number) => void
}

export function Timeline({
  segments,
  selectedSid,
  duration,
  onSelectSegment,
  onSeek,
}: TimelineProps) {
  return (
    <section className="timeline-panel" aria-labelledby="timeline-title">
      <div className="section-heading">
        <p className="eyebrow">Timeline</p>
        <h2 id="timeline-title">분석 구간</h2>
      </div>

      <div className="timeline-bar" aria-hidden="true">
        {segments.map((segment) => {
          const left = (segment.start_time / duration) * 100
          const width =
            ((segment.end_time - segment.start_time) / duration) * 100

          return (
            <button
              className={
                segment.sid === selectedSid
                  ? 'timeline-block is-selected'
                  : 'timeline-block'
              }
              key={segment.sid}
              type="button"
              style={{ left: `${left}%`, width: `${width}%` }}
              onClick={() => onSelectSegment(segment.sid)}
              aria-label={`${segment.title} ${formatRange(
                segment.start_time,
                segment.end_time,
              )}`}
            />
          )
        })}
      </div>

      <div className="timeline-list">
        {segments.map((segment) => (
          <button
            className={
              segment.sid === selectedSid
                ? 'timeline-row is-selected'
                : 'timeline-row'
            }
            key={segment.sid}
            type="button"
            onClick={() => onSelectSegment(segment.sid)}
          >
            <span>{segment.title}</span>
            <span>{formatRange(segment.start_time, segment.end_time)}</span>
          </button>
        ))}
      </div>

      <div className="moment-list">
        {segments.flatMap((segment) =>
          segment.important.map((moment) => (
            <button
              className="moment-button"
              key={`${segment.sid}-${moment.time}`}
              type="button"
              onClick={() => {
                onSelectSegment(segment.sid)
                onSeek(moment.time)
              }}
            >
              <span>{moment.title}</span>
              <span>{formatTime(moment.time)}</span>
            </button>
          )),
        )}
      </div>
    </section>
  )
}
