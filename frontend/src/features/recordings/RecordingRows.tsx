import type { Recording } from '../../types/finalResult'
import { classNames } from '../../utils/classNames'

type RecordingRowsProps = {
  draggingRecordingId: string | null
  recordings: Recording[]
  selectedIds: string[]
  selectedRecordingId: string
  onDragEnd: () => void
  onDragStart: (recordingId: string) => void
  onRetryRecording: (recording: Recording) => void
  onSelectRecording: (recording: Recording) => void
  onToggleChecked: (id: string) => void
}

export function RecordingRows({
  draggingRecordingId,
  recordings,
  selectedIds,
  selectedRecordingId,
  onDragEnd,
  onDragStart,
  onRetryRecording,
  onSelectRecording,
  onToggleChecked,
}: RecordingRowsProps) {
  if (recordings.length === 0) {
    return <p className="recording-empty">검색 결과가 없습니다.</p>
  }

  return recordings.map((recording) => (
    <button
      className={classNames(
        'recording-row',
        selectedRecordingId === recording.id && 'selected',
        draggingRecordingId === recording.id && 'dragging',
      )}
      key={recording.id}
      type="button"
      draggable
      onDragStart={(event) => {
        event.dataTransfer.setData('text/plain', recording.id)
        event.dataTransfer.effectAllowed = 'move'
        onDragStart(recording.id)
      }}
      onDragEnd={onDragEnd}
      onClick={() => onSelectRecording(recording)}
    >
      <span
        className="recording-check"
        role="checkbox"
        tabIndex={0}
        aria-checked={selectedIds.includes(recording.id)}
        onClick={(event) => {
          event.stopPropagation()
          onToggleChecked(recording.id)
        }}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            event.stopPropagation()
            onToggleChecked(recording.id)
          }
        }}
      />
      <span>{recording.name}</span>
      <span>{recording.date}</span>
      {recording.status === 'failed' ? (
        <span className="failed-status-wrapper">
          <span className="failed-status-tooltip" role="tooltip">
            {recording.error_message ?? '업로드 또는 AI 처리에 실패했습니다.'}
            {' '}
            클릭하면 다시 시도합니다.
          </span>
          <span
            className="status failed"
            role="button"
            tabIndex={0}
            title={`${
              recording.error_message ?? '업로드 또는 AI 처리에 실패했습니다.'
            } 클릭하면 다시 시도합니다.`}
            aria-label={`분석 실패: ${
              recording.error_message ?? '업로드 또는 AI 처리에 실패했습니다.'
            } 클릭하면 다시 시도합니다.`}
            onClick={(event) => {
              event.stopPropagation()
              onRetryRecording(recording)
            }}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                event.stopPropagation()
                onRetryRecording(recording)
              }
            }}
          >
            !
          </span>
        </span>
      ) : recording.status === 'waiting' ? (
        <span className="status waiting" aria-label="녹음 정보 추가 중" />
      ) : (
        <span className="status complete" aria-hidden="true" />
      )}
    </button>
  ))
}
