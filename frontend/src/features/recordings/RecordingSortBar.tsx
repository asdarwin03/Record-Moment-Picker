import type { RecordingSortDirection } from './types'

type RecordingSortBarProps = {
  sortDirection: RecordingSortDirection
  onToggleSortDirection: () => void
}

export function RecordingSortBar({
  sortDirection,
  onToggleSortDirection,
}: RecordingSortBarProps) {
  const isRecentFirst = sortDirection === 'desc'

  return (
    <div className="recording-sortbar">
      <button
        type="button"
        onClick={onToggleSortDirection}
        aria-label={
          isRecentFirst ? '날짜 오름차순으로 정렬' : '날짜 내림차순으로 정렬'
        }
        title={isRecentFirst ? '최근 순' : '오래된 순'}
      >
        {isRecentFirst ? '↓' : '↑'}
      </button>
      <span>{isRecentFirst ? '최근 순' : '오래된 순'}</span>
    </div>
  )
}
