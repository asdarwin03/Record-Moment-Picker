import { type DragEvent, useState } from 'react'
import type { RecordingFolder } from '../../types/finalResult'
import { classNames } from '../../utils/classNames'
import type { FolderCounts, FolderSelection } from './types'

type RecordingFolderSectionProps = {
  draggingRecordingId: string | null
  folderCounts: FolderCounts
  folders: RecordingFolder[]
  hoveredDropTargetId: string | null
  selectedFolderId: FolderSelection
  onAddFolder: () => void
  onDeleteFolder: () => void
  onDropRecordingToFolder: (recordingId: string, folderId?: string) => void
  onRenameFolder: (folderId: string, name: string) => void
  onSelectFolder: (folderId: FolderSelection) => void
  onSetHoveredDropTargetId: (targetId: string | null) => void
}

export function RecordingFolderSection({
  draggingRecordingId,
  folderCounts,
  folders,
  hoveredDropTargetId,
  selectedFolderId,
  onAddFolder,
  onDeleteFolder,
  onDropRecordingToFolder,
  onRenameFolder,
  onSelectFolder,
  onSetHoveredDropTargetId,
}: RecordingFolderSectionProps) {
  const [editingFolderId, setEditingFolderId] = useState<string | null>(null)
  const [editingFolderName, setEditingFolderName] = useState('')

  function getFolderClassName(folderId: FolderSelection) {
    const isSelected =
      folderId === null
        ? selectedFolderId === null
        : selectedFolderId === folderId
    const dropTargetId = folderId ?? (folderId === null ? 'unfiled' : 'all')

    return classNames(
      'folder-chip',
      isSelected && 'selected',
      folderId !== undefined && draggingRecordingId && 'drop-ready',
      hoveredDropTargetId === dropTargetId && 'drop-hover',
    )
  }

  function handleFolderDrop(folderId: string | undefined) {
    return (event: DragEvent<HTMLButtonElement>) => {
      const recordingId = event.dataTransfer.getData('text/plain')

      event.preventDefault()

      if (recordingId) {
        onDropRecordingToFolder(recordingId, folderId)
      }

      onSetHoveredDropTargetId(null)
    }
  }

  function handleFolderDragOver(dropTargetId: string) {
    return (event: DragEvent<HTMLButtonElement>) => {
      event.preventDefault()
      event.dataTransfer.dropEffect = 'move'
      onSetHoveredDropTargetId(dropTargetId)
    }
  }

  function startFolderRename(folder: RecordingFolder) {
    setEditingFolderId(folder.id)
    setEditingFolderName(folder.name)
  }

  function commitFolderRename() {
    if (!editingFolderId) {
      return
    }

    onRenameFolder(editingFolderId, editingFolderName)
    setEditingFolderId(null)
    setEditingFolderName('')
  }

  function cancelFolderRename() {
    setEditingFolderId(null)
    setEditingFolderName('')
  }

  return (
    <div className="folder-section">
      <div className="folder-section-head">
        <span>폴더</span>
        <div className="folder-toolbar">
          <button type="button" onClick={onAddFolder}>
            추가
          </button>
          <button
            type="button"
            onClick={onDeleteFolder}
            disabled={!selectedFolderId}
          >
            삭제
          </button>
        </div>
      </div>
      <div className="folder-list" aria-label="녹음 폴더">
        <button
          className={getFolderClassName(undefined)}
          type="button"
          onClick={() => onSelectFolder(undefined)}
        >
          <span>전체</span>
          <strong>{folderCounts.all}</strong>
        </button>
        <button
          className={getFolderClassName(null)}
          type="button"
          title="녹음을 이곳에 드롭하면 폴더에서 빠집니다"
          onClick={() => onSelectFolder(null)}
          onDragOver={handleFolderDragOver('unfiled')}
          onDrop={handleFolderDrop(undefined)}
        >
          <span>미분류</span>
          <strong>{folderCounts.unfiled}</strong>
        </button>
        {folders.map((folder) => (
          <div className="folder-item" key={folder.id}>
            {editingFolderId === folder.id ? (
              <input
                autoFocus
                className="folder-rename-input"
                value={editingFolderName}
                onBlur={commitFolderRename}
                onChange={(event) => setEditingFolderName(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    commitFolderRename()
                  }

                  if (event.key === 'Escape') {
                    cancelFolderRename()
                  }
                }}
              />
            ) : (
              <button
                className={getFolderClassName(folder.id)}
                type="button"
                title={`${folder.name}에 녹음 넣기`}
                onClick={() => onSelectFolder(folder.id)}
                onDoubleClick={() => startFolderRename(folder)}
                onDragOver={handleFolderDragOver(folder.id)}
                onDrop={handleFolderDrop(folder.id)}
              >
                <span>{folder.name}</span>
                <strong>{folderCounts.byId[folder.id] ?? 0}</strong>
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
