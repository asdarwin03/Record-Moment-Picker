import type { PointerEvent } from 'react'
import type {
  EnrichedTranscriptItem,
  FloatingWindowState,
} from '../../types/finalResult'
import { formatTime } from '../../utils/time'

type TranscriptDocumentWindowProps = {
  highlightId: string | null
  title: string
  transcriptItems: EnrichedTranscriptItem[]
  windowState: FloatingWindowState
  onClose: () => void
  onDragStart: (event: PointerEvent<HTMLElement>) => void
  onHighlight: (id: string) => void
  onResizeStart: (event: PointerEvent<HTMLButtonElement>) => void
  onSeek: (time: number) => void
}

export function TranscriptDocumentWindow({
  highlightId,
  title,
  transcriptItems,
  windowState,
  onClose,
  onDragStart,
  onHighlight,
  onResizeStart,
  onSeek,
}: TranscriptDocumentWindowProps) {
  return (
    <aside
      className="document-drawer"
      aria-label="녹음 내용 문서"
      style={{
        transform: `translate(${windowState.x}px, ${windowState.y}px)`,
        width: `${windowState.width}px`,
        height: `${windowState.height}px`,
      }}
    >
      <div className="drawer-head" onPointerDown={onDragStart}>
        <div>
          <p>녹음 내용 문서</p>
          <h2>{title}</h2>
        </div>
        <button type="button" onClick={onClose}>
          닫기
        </button>
      </div>
      <div className="drawer-transcript">
        {transcriptItems.map((text) => (
          <button
            className={
              text.t_id === highlightId
                ? 'transcript-line highlighted'
                : 'transcript-line'
            }
            key={text.t_id}
            type="button"
            onClick={() => {
              onSeek(text.start_time)
              onHighlight(text.t_id)
            }}
          >
            <strong>{formatTime(text.start_time)}</strong>
            <span>
              <em>{text.segmentTitle}</em>
              {text.text}
            </span>
          </button>
        ))}
      </div>
      <button
        className="document-resize-handle"
        type="button"
        onPointerDown={onResizeStart}
        aria-label="문서 창 크기 조절"
      />
    </aside>
  )
}
