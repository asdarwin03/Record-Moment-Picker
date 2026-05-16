import type { Segment } from '../../types/finalResult'
import { getTone } from '../../data/demoRecordings'
import { formatTime } from '../../utils/time'

type TimestampPanelProps = {
  expandedSids: string[]
  selectedSid: string
  segments: Segment[]
  onSeek: (time: number) => void
  onSelectSegment: (segment: Segment) => void
  onToggleSegment: (sid: string) => void
}

export function TimestampPanel({
  expandedSids,
  selectedSid,
  segments,
  onSeek,
  onSelectSegment,
  onToggleSegment,
}: TimestampPanelProps) {
  return (
    <div className="timestamp-area">
      <h2>타임스탬프</h2>
      <div className="timestamp-card">
        {segments.length === 0 ? (
          <p className="empty-state">아직 분석 결과가 없습니다.</p>
        ) : (
          segments.map((segment, index) => {
            const isExpanded = expandedSids.includes(segment.sid)

            return (
              <div className="timestamp-group" key={segment.sid}>
                <button
                  className={`timestamp-row ${getTone(index)} ${
                    segment.sid === selectedSid ? 'selected' : ''
                  }`}
                  type="button"
                  onClick={() => onSelectSegment(segment)}
                >
                  <span>{formatTime(segment.start_time)}</span>
                  <span>{segment.title}</span>
                  <span className="timestamp-meta">
                    {formatTime(segment.end_time)}
                  </span>
                  <span
                    className={
                      isExpanded
                        ? 'timestamp-dropdown expanded'
                        : 'timestamp-dropdown'
                    }
                    role="button"
                    tabIndex={0}
                    onClick={(event) => {
                      event.stopPropagation()
                      onToggleSegment(segment.sid)
                    }}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        event.stopPropagation()
                        onToggleSegment(segment.sid)
                      }
                    }}
                    aria-label={
                      isExpanded ? '중요한 순간 접기' : '중요한 순간 펼치기'
                    }
                  />
                </button>

                {isExpanded
                  ? segment.important.map((moment) => (
                      <button
                        className="timestamp-important-row"
                        key={`${segment.sid}-${moment.time}`}
                        type="button"
                        onClick={() => onSeek(moment.time)}
                      >
                        <span>{formatTime(moment.time)}</span>
                        <span>{moment.title}</span>
                      </button>
                    ))
                  : null}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
