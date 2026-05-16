import { useState } from 'react'
import type { Recording, RecordingFolder } from '../../types/finalResult'
import { classNames } from '../../utils/classNames'
import { RecordingFolderSection } from './RecordingFolderSection'
import { RecordingRows } from './RecordingRows'
import { RecordingSearchBar } from './RecordingSearchBar'
import { RecordingSortBar } from './RecordingSortBar'
import type {
  FolderCounts,
  FolderSelection,
  RecordingSortDirection,
} from './types'

type RecordingListPanelProps = {
  draftSearchQuery: string
  folderCounts: FolderCounts
  folders: RecordingFolder[]
  recordings: Recording[]
  selectedFolderId: FolderSelection
  selectedIds: string[]
  selectedRecordingId: string
  sortDirection: RecordingSortDirection
  totalVisibleCount: number
  onAddFolder: () => void
  onDeleteFolder: () => void
  onDropRecordingToFolder: (recordingId: string, folderId?: string) => void
  onRemoveChecked: () => void
  onApplySearch: () => void
  onDraftSearchQueryChange: (query: string) => void
  onResetSearch: () => void
  onRenameFolder: (folderId: string, name: string) => void
  onSelectFolder: (folderId: FolderSelection) => void
  onToggleSortDirection: () => void
  onToggleChecked: (id: string) => void
  onSelectRecording: (recording: Recording) => void
}

export function RecordingListPanel({
  draftSearchQuery,
  folderCounts,
  folders,
  recordings,
  selectedFolderId,
  selectedIds,
  selectedRecordingId,
  sortDirection,
  totalVisibleCount,
  onAddFolder,
  onApplySearch,
  onDeleteFolder,
  onDraftSearchQueryChange,
  onDropRecordingToFolder,
  onRemoveChecked,
  onRenameFolder,
  onResetSearch,
  onSelectFolder,
  onSelectRecording,
  onToggleChecked,
  onToggleSortDirection,
}: RecordingListPanelProps) {
  const [draggingRecordingId, setDraggingRecordingId] = useState<string | null>(
    null,
  )
  const [hoveredDropTargetId, setHoveredDropTargetId] = useState<string | null>(
    null,
  )

  function resetDragState() {
    setDraggingRecordingId(null)
    setHoveredDropTargetId(null)
  }

  return (
    <aside
      className={classNames(
        'recording-panel',
        draggingRecordingId && 'dragging-recording',
      )}
      aria-labelledby="recording-title"
    >
      <div className="recording-head">
        <h2 id="recording-title">녹음 리스트</h2>
        <span>
          {recordings.length} / {totalVisibleCount}
        </span>
      </div>

      <RecordingSearchBar
        draftSearchQuery={draftSearchQuery}
        onApplySearch={onApplySearch}
        onDraftSearchQueryChange={onDraftSearchQueryChange}
        onResetSearch={onResetSearch}
      />

      <RecordingSortBar
        sortDirection={sortDirection}
        onToggleSortDirection={onToggleSortDirection}
      />

      <RecordingFolderSection
        draggingRecordingId={draggingRecordingId}
        folderCounts={folderCounts}
        folders={folders}
        hoveredDropTargetId={hoveredDropTargetId}
        selectedFolderId={selectedFolderId}
        onAddFolder={onAddFolder}
        onDeleteFolder={onDeleteFolder}
        onDropRecordingToFolder={(recordingId, folderId) => {
          onDropRecordingToFolder(recordingId, folderId)
          resetDragState()
        }}
        onRenameFolder={onRenameFolder}
        onSelectFolder={onSelectFolder}
        onSetHoveredDropTargetId={setHoveredDropTargetId}
      />

      <div className="recording-list">
        <RecordingRows
          draggingRecordingId={draggingRecordingId}
          recordings={recordings}
          selectedIds={selectedIds}
          selectedRecordingId={selectedRecordingId}
          onDragEnd={resetDragState}
          onDragStart={setDraggingRecordingId}
          onSelectRecording={onSelectRecording}
          onToggleChecked={onToggleChecked}
        />
      </div>

      <div className="recording-actions">
        <button type="button" disabled title="백엔드/AI 연결 후 활성화됩니다">
          추가
        </button>
        <button
          type="button"
          onClick={onRemoveChecked}
          disabled={selectedIds.length === 0}
        >
          제거
        </button>
      </div>
    </aside>
  )
}
