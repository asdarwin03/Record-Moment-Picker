import type { PointerEvent } from 'react'
import type {
  EnrichedTranscriptItem,
  FloatingWindowState,
  SummaryRow,
} from '../../types/finalResult'
import { formatTime } from '../../utils/time'

type FloatingEvidenceWindowProps = {
  evidenceTexts: EnrichedTranscriptItem[]
  isCollapsed: boolean
  selectedSummaryRow: SummaryRow
  windowPosition: Pick<FloatingWindowState, 'x' | 'y'>
  windowSize: Pick<FloatingWindowState, 'width' | 'height'>
  onClose: () => void
  onOpenSegmentDocument: (segmentSid: string, highlightId?: string) => void
  onResizeStart: (event: PointerEvent<HTMLButtonElement>) => void
  onSeek: (time: number) => void
  onToggleCollapse: () => void
  onWindowDragStart: (event: PointerEvent<HTMLElement>) => void
}

export function FloatingEvidenceWindow({
  evidenceTexts,
  isCollapsed,
  selectedSummaryRow,
  windowPosition,
  windowSize,
  onClose,
  onOpenSegmentDocument,
  onResizeStart,
  onSeek,
  onToggleCollapse,
  onWindowDragStart,
}: FloatingEvidenceWindowProps) {
  const evidenceGroups = evidenceTexts.reduce<
    Array<{
      segmentSid: string
      segmentTitle: string
      texts: EnrichedTranscriptItem[]
    }>
  >((groups, text) => {
    const group = groups.find((item) => item.segmentSid === text.segmentSid)

    if (group) {
      group.texts.push(text)
      return groups
    }

    return [
      ...groups,
      {
        segmentSid: text.segmentSid,
        segmentTitle: text.segmentTitle,
        texts: [text],
      },
    ]
  }, [])

  return (
    <article
      className={isCollapsed ? 'floating-evidence collapsed' : 'floating-evidence'}
      style={{
        transform: `translate(${windowPosition.x}px, ${windowPosition.y}px)`,
        width: `${isCollapsed ? 360 : windowSize.width}px`,
        height: isCollapsed ? 'auto' : `${windowSize.height}px`,
      }}
    >
      <header
        className="floating-evidence-head"
        onPointerDown={onWindowDragStart}
      >
        <div>
          <p>요약 근거</p>
          <h3>{selectedSummaryRow.line}</h3>
        </div>
        <div className="evidence-window-actions">
          <button
            type="button"
            onClick={onToggleCollapse}
            aria-label={isCollapsed ? '요약 근거 펼치기' : '요약 근거 접기'}
          >
            {isCollapsed ? '펼치기' : '접기'}
          </button>
          <button type="button" onClick={onClose} aria-label="요약 근거 닫기">
            닫기
          </button>
        </div>
      </header>

      {!isCollapsed ? (
        <div className="floating-evidence-body">
          <div className="evidence-group-list">
            {evidenceGroups.map((group) => (
              <section className="evidence-group" key={group.segmentSid}>
                <div className="evidence-group-head">
                  <div>
                    <span>{formatTime(group.texts[0]?.time ?? 0)}</span>
                    <h4>{group.segmentTitle}</h4>
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      onOpenSegmentDocument(
                        group.segmentSid,
                        group.texts[0]?.t_id,
                      )
                    }
                  >
                    구간 녹음 문서 보기
                  </button>
                </div>
                <div className="evidence-text-list">
                  {group.texts.map((text) => (
                    <button
                      key={text.t_id}
                      type="button"
                      onClick={() => {
                        onSeek(text.time)
                        onOpenSegmentDocument(text.segmentSid, text.t_id)
                      }}
                    >
                      <strong>{formatTime(text.time)}</strong>
                      <span>{text.text}</span>
                    </button>
                  ))}
                </div>
              </section>
            ))}
          </div>
          <button
            className="floating-resize-handle"
            type="button"
            onPointerDown={onResizeStart}
            aria-label="요약 근거 창 크기 조절"
          />
        </div>
      ) : null}
    </article>
  )
}
