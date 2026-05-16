type RecordingSearchBarProps = {
  draftSearchQuery: string
  onApplySearch: () => void
  onDraftSearchQueryChange: (query: string) => void
  onResetSearch: () => void
}

export function RecordingSearchBar({
  draftSearchQuery,
  onApplySearch,
  onDraftSearchQueryChange,
  onResetSearch,
}: RecordingSearchBarProps) {
  return (
    <div className="recording-search">
      <input
        type="search"
        value={draftSearchQuery}
        onChange={(event) => onDraftSearchQueryChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter') {
            onApplySearch()
          }
        }}
        placeholder="녹음명, 요약, 원문, 중요 순간 검색"
        aria-label="녹음 통합검색"
      />
      <button type="button" onClick={onApplySearch} aria-label="통합검색">
        <span className="search-icon" aria-hidden="true" />
      </button>
      <button type="button" onClick={onResetSearch} aria-label="검색 초기화">
        <span className="reset-icon" aria-hidden="true" />
      </button>
    </div>
  )
}
