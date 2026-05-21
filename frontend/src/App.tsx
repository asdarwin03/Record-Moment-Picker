import { type MouseEvent, type PointerEvent, useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
import { demoSegments, initialRecordings } from './data/demoRecordings'
import { TransportBar } from './features/audio-player/TransportBar'
import { TranscriptDocumentWindow } from './features/document/TranscriptDocumentWindow'
import { FloatingEvidenceWindow } from './features/evidence/FloatingEvidenceWindow'
import { PromptPanel } from './features/prompt/PromptPanel'
import { RecordingListPanel } from './features/recordings/RecordingListPanel'
import { SummaryWorkspace } from './features/summary/SummaryWorkspace'
import { TimestampPanel } from './features/timeline/TimestampPanel'
import { useAudioController } from './hooks/useAudioController'
import {
  createFolder as createFolderRequest,
  deleteFolder as deleteFolderRequest,
  fetchBootstrap,
  fetchRecording,
  fetchRecordingStatus,
  hideRecordings,
  renameFolder as renameFolderRequest,
  updateRecordingFolder,
  uploadRecording,
} from './services/api'
import {
  createDragStartHandler,
  createResizeStartHandler,
} from './hooks/useDragResize'
import type {
  EnrichedTranscriptItem,
  FloatingWindowState,
  Recording,
  RecordingFolder,
  Segment,
  SummaryRef,
} from './types/finalResult'
import {
  getAnalysisDuration,
  getEvidenceTexts,
  getSelectedSummaryRow,
  getSummaryRows,
  getTranscriptItems,
} from './utils/segments'
import { recordingMatchesSearch } from './utils/recordingSearch'

const initialPrompt =
  '중요한 순간이 포함된 구간을 찾아줘.\n구간별 핵심 내용을 다시 요약해줘.'

const emptyRecording: Recording = {
  id: '',
  name: '',
  date: '',
  status: 'waiting',
  segments: [],
}

function delay(ms: number) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms)
  })
}

type EvidenceWindowState = {
  id: string
  isCollapsed: boolean
  summaryRef: SummaryRef
  window: FloatingWindowState
}

const processingStatuses = new Set(['uploaded', 'processing'])

function App() {
  const trackFillRef = useRef<HTMLDivElement | null>(null)

  const [recordings, setRecordings] = useState(initialRecordings)
  const [selectedRecordingId, setSelectedRecordingId] = useState('club')
  const [isUploading, setIsUploading] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)
  const [draftRecordingSearchQuery, setDraftRecordingSearchQuery] = useState('')
  const [appliedRecordingSearchQuery, setAppliedRecordingSearchQuery] =
    useState('')
  const [recordingSortDirection, setRecordingSortDirection] = useState<
    'asc' | 'desc'
  >('desc')
  const [folders, setFolders] = useState<RecordingFolder[]>([])
  const [selectedFolderId, setSelectedFolderId] = useState<
    string | null | undefined
  >(undefined)
  const [checkedRecordingIds, setCheckedRecordingIds] = useState<string[]>([])
  const [selectedSid, setSelectedSid] = useState(demoSegments[0]?.sid ?? '')
  const [evidenceWindows, setEvidenceWindows] = useState<EvidenceWindowState[]>(
    [],
  )
  const [documentWindow, setDocumentWindow] = useState<FloatingWindowState>({
    x: 760,
    y: 120,
    width: 620,
    height: 620,
  })
  const [documentHighlightId, setDocumentHighlightId] = useState<string | null>(
    null,
  )
  const [documentTitle, setDocumentTitle] = useState('전체 녹음 문서')
  const [documentItems, setDocumentItems] = useState<EnrichedTranscriptItem[]>(
    [],
  )
  const [isDocumentOpen, setIsDocumentOpen] = useState(false)
  const [expandedTimestampSids, setExpandedTimestampSids] = useState<string[]>(
    [],
  )
  const [prompt, setPrompt] = useState(initialPrompt)
  const [isPromptEnabled, setIsPromptEnabled] = useState(false)

  const visibleRecordings = useMemo(
    () => recordings.filter((recording) => !recording.isHidden),
    [recordings],
  )
  const folderScopedRecordings = useMemo(
    () =>
      visibleRecordings.filter((recording) => {
        if (selectedFolderId === undefined) {
          return true
        }

        if (selectedFolderId === null) {
          return !recording.folderId
        }

        return recording.folderId === selectedFolderId
      }),
    [selectedFolderId, visibleRecordings],
  )
  const folderCounts = useMemo(() => {
    const byId: Record<string, number> = {}
    let unfiled = 0

    visibleRecordings.forEach((recording) => {
      if (!recording.folderId) {
        unfiled += 1
        return
      }

      byId[recording.folderId] = (byId[recording.folderId] ?? 0) + 1
    })

    return {
      all: visibleRecordings.length,
      byId,
      unfiled,
    }
  }, [visibleRecordings])
  const selectedRecording =
    visibleRecordings.find((recording) => recording.id === selectedRecordingId) ??
    visibleRecordings[0] ??
    emptyRecording
  const filteredRecordings = useMemo(
    () =>
      folderScopedRecordings
        .filter((recording) =>
          recordingMatchesSearch(recording, appliedRecordingSearchQuery),
        )
        .toSorted((a, b) => {
          const aTime = new Date(a.date).getTime()
          const bTime = new Date(b.date).getTime()

          return recordingSortDirection === 'desc'
            ? bTime - aTime
            : aTime - bTime
        }),
    [
      appliedRecordingSearchQuery,
      folderScopedRecordings,
      recordingSortDirection,
    ],
  )
  const segments = selectedRecording.segments
  const analysisDuration = useMemo(
    () => getAnalysisDuration(segments),
    [segments],
  )
  const transcriptItems = useMemo(() => getTranscriptItems(segments), [segments])
  const summaryRows = useMemo(() => getSummaryRows(segments), [segments])
  const {
    audioRef,
    currentTime,
    duration,
    handleLoadedMetadata,
    handleTimeUpdate,
    isPlaying,
    resetAudio,
    seekToTime,
    setAudioDuration,
    setCurrentTime,
    setIsPlaying,
    togglePlayback,
  } = useAudioController({
    analysisDuration,
    segments,
    selectedRecording,
    onSegmentChange: setSelectedSid,
  })

  useEffect(() => {
    let isMounted = true

    fetchBootstrap()
      .then((payload) => {
        if (!isMounted) {
          return
        }

        setRecordings(payload.recordings)
        setFolders(payload.folders)

        const preferredRecording =
          payload.recordings.find((recording) => recording.id === 'club') ??
          payload.recordings[0]

        if (preferredRecording) {
          setSelectedRecordingId(preferredRecording.id)
          setSelectedSid(preferredRecording.segments[0]?.sid ?? '')
        }
      })
      .catch((error: Error) => {
        if (isMounted) {
          setApiError(`백엔드 연결 실패: ${error.message}`)
        }
      })

    return () => {
      isMounted = false
    }
  }, [])

  useEffect(() => {
    resetAudio(selectedRecording.segments[0]?.start_time ?? 0)
  }, [resetAudio, selectedRecording])

  function selectRecording(recording: Recording) {
    setSelectedRecordingId(recording.id)
    setEvidenceWindows([])
    setIsDocumentOpen(false)
    setDocumentHighlightId(null)
    setAudioDuration(0)
    setIsPlaying(false)
    setCheckedRecordingIds([])

    if (recording.segments[0]) {
      setSelectedSid(recording.segments[0].sid)
      setCurrentTime(recording.segments[0].start_time)
    }
  }

  function toggleCheckedRecording(id: string) {
    setCheckedRecordingIds((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id],
    )
  }

  async function removeCheckedRecordings() {
    if (checkedRecordingIds.length === 0) {
      return
    }

    const idsToHide = checkedRecordingIds

    try {
      await hideRecordings(idsToHide)
      setApiError(null)
    } catch (error) {
      setApiError(`녹음 제거 실패: ${(error as Error).message}`)
      return
    }

    setRecordings((items) =>
      items.map((recording) =>
        idsToHide.includes(recording.id)
          ? { ...recording, isHidden: true }
          : recording,
      ),
    )

    const nextRecording = visibleRecordings.find(
      (recording) => !idsToHide.includes(recording.id),
    )

    if (nextRecording && idsToHide.includes(selectedRecordingId)) {
      selectRecording(nextRecording)
      setCheckedRecordingIds([])
      return
    }

    if (!nextRecording) {
      setEvidenceWindows([])
      setIsDocumentOpen(false)
      setSelectedRecordingId('')
      setSelectedSid('')
      setCurrentTime(0)
      setAudioDuration(0)
      setIsPlaying(false)
    }

    setCheckedRecordingIds([])
  }

  async function addFolder() {
    const folderNumber = folders.length + 1

    try {
      const folder = await createFolderRequest(`새 폴더 ${folderNumber}`)
      setFolders((current) => [...current, folder])
      setSelectedFolderId(folder.id)
      setApiError(null)
    } catch (error) {
      setApiError(`폴더 추가 실패: ${(error as Error).message}`)
    }
  }

  async function deleteSelectedFolder() {
    if (!selectedFolderId) {
      return
    }

    try {
      await deleteFolderRequest(selectedFolderId)
      setApiError(null)
    } catch (error) {
      setApiError(`폴더 삭제 실패: ${(error as Error).message}`)
      return
    }

    setFolders((current) =>
      current.filter((folder) => folder.id !== selectedFolderId),
    )
    setRecordings((items) =>
      items.map((recording) =>
        recording.folderId === selectedFolderId
          ? { ...recording, folderId: undefined }
          : recording,
      ),
    )
    setSelectedFolderId(undefined)
  }

  async function moveRecordingToFolder(recordingId: string, folderId?: string) {
    const previousRecordings = recordings

    setRecordings((items) =>
      items.map((recording) =>
        recording.id === recordingId
          ? { ...recording, folderId }
        : recording,
      ),
    )

    try {
      const updatedRecording = await updateRecordingFolder(recordingId, folderId)
      setRecordings((items) =>
        items.map((recording) =>
          recording.id === recordingId ? updatedRecording : recording,
        ),
      )
      setApiError(null)
    } catch (error) {
      setRecordings(previousRecordings)
      setApiError(`폴더 이동 실패: ${(error as Error).message}`)
    }
  }

  async function renameFolder(folderId: string, name: string) {
    const trimmedName = name.trim()

    if (!trimmedName) {
      return
    }

    try {
      const renamedFolder = await renameFolderRequest(folderId, trimmedName)
      setFolders((current) =>
        current.map((folder) =>
          folder.id === folderId ? renamedFolder : folder,
        ),
      )
      setApiError(null)
    } catch (error) {
      setApiError(`폴더 이름 변경 실패: ${(error as Error).message}`)
    }
  }

  async function addRecordingFile(file: File) {
    const temporaryRecording: Recording = {
      id: `uploading-${Date.now()}`,
      name: file.name,
      date: new Date().toISOString().slice(0, 10),
      status: 'waiting',
      segments: [],
    }

    setIsUploading(true)
    setApiError(null)
    setRecordings((items) => [temporaryRecording, ...items])
    selectRecording(temporaryRecording)

    try {
      const uploadedRecording = await uploadRecording(file)
      setRecordings((items) =>
        items.map((recording) =>
          recording.id === temporaryRecording.id ? uploadedRecording : recording,
        ),
      )
      selectRecording(uploadedRecording)
      void pollRecordingUntilDone(uploadedRecording.id)
    } catch (error) {
      setRecordings((items) =>
        items.filter((recording) => recording.id !== temporaryRecording.id),
      )
      setApiError(`녹음 분석 실패: ${(error as Error).message}`)
    } finally {
      setIsUploading(false)
    }
  }

  async function pollRecordingUntilDone(recordingId: string) {
    const maxAttempts = 360

    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      await delay(5000)

      try {
        const status = await fetchRecordingStatus(recordingId)

        if (status.status === 'failed') {
          setApiError(
            `녹음 분석 실패: ${status.error_message ?? 'AI 처리 중 오류가 발생했습니다.'}`,
          )
          return
        }

        if (!processingStatuses.has(status.status)) {
          const completedRecording = await fetchRecording(recordingId)
          setRecordings((items) =>
            items.map((recording) =>
              recording.id === recordingId ? completedRecording : recording,
            ),
          )

          setApiError(null)
          return
        }
      } catch (error) {
        setApiError(`분석 상태 확인 실패: ${(error as Error).message}`)
      }
    }

    setApiError('녹음 분석이 오래 걸리고 있습니다. 잠시 후 목록을 새로고침해 주세요.')
  }

  function selectSegment(segment: Segment) {
    setSelectedSid(segment.sid)
    setEvidenceWindows([])
    setDocumentHighlightId(null)
    seekToTime(segment.start_time)
  }

  function selectSummary(segment: Segment, summaryIndex: number) {
    const id = `${segment.sid}-${summaryIndex}`

    setEvidenceWindows((current) => {
      if (current.some((window) => window.id === id)) {
        return current.filter((window) => window.id !== id)
      }

      return [
        ...current,
        {
          id,
          isCollapsed: false,
          summaryRef: { sid: segment.sid, summaryIndex },
          window: {
            x: 520 + current.length * 28,
            y: 430 + current.length * 28,
            width: 420,
            height: 360,
          },
        },
      ]
    })
    setDocumentHighlightId(null)
  }

  function toggleTimestampSegment(sid: string) {
    setExpandedTimestampSids((current) =>
      current.includes(sid)
        ? current.filter((item) => item !== sid)
        : [...current, sid],
    )
  }

  function openFullDocument(highlightId?: string) {
    setDocumentTitle('전체 녹음 문서')
    setDocumentItems(transcriptItems)
    setDocumentHighlightId(highlightId ?? transcriptItems[0]?.t_id ?? null)
    setIsDocumentOpen(true)
  }

  function updateEvidenceWindow(
    id: string,
    updater: (current: FloatingWindowState) => FloatingWindowState,
  ) {
    setEvidenceWindows((current) =>
      current.map((window) =>
        window.id === id
          ? {
              ...window,
              window: updater(window.window),
            }
          : window,
      ),
    )
  }

  function toggleEvidenceWindow(id: string) {
    setEvidenceWindows((current) =>
      current.map((window) =>
        window.id === id
          ? { ...window, isCollapsed: !window.isCollapsed }
          : window,
      ),
    )
  }

  function closeEvidenceWindow(id: string) {
    setEvidenceWindows((current) =>
      current.filter((window) => window.id !== id),
    )
  }

  function openSegmentDocument(segmentSid: string, highlightId?: string) {
    const segment = segments.find((item) => item.sid === segmentSid)
    const segmentTexts = transcriptItems.filter(
      (text) => text.segmentSid === segmentSid,
    )

    setDocumentTitle(segment?.title ?? '구간 녹음 문서')
    setDocumentItems(segmentTexts)
    setDocumentHighlightId(highlightId ?? segmentTexts[0]?.t_id ?? null)
    setIsDocumentOpen(true)
  }

  function seekToClientX(clientX: number, rect: DOMRect) {
    if (duration <= 0) {
      return
    }

    const ratio = Math.min(
      1,
      Math.max(0, (clientX - rect.left) / rect.width),
    )

    seekToTime(duration * ratio)
  }

  function seekFromTrack(event: MouseEvent<HTMLDivElement>) {
    seekToClientX(event.clientX, event.currentTarget.getBoundingClientRect())
  }

  function startPlayheadDrag(event: PointerEvent<HTMLButtonElement>) {
    const track = trackFillRef.current

    if (!track) {
      return
    }

    const rect = track.getBoundingClientRect()
    const target = event.currentTarget

    event.preventDefault()
    event.stopPropagation()
    target.setPointerCapture(event.pointerId)
    seekToClientX(event.clientX, rect)

    function movePlayhead(moveEvent: globalThis.PointerEvent) {
      seekToClientX(moveEvent.clientX, rect)
    }

    function stopDrag(upEvent: globalThis.PointerEvent) {
      target.releasePointerCapture(upEvent.pointerId)
      target.removeEventListener('pointermove', movePlayhead)
      target.removeEventListener('pointerup', stopDrag)
      target.removeEventListener('pointercancel', stopDrag)
    }

    target.addEventListener('pointermove', movePlayhead)
    target.addEventListener('pointerup', stopDrag)
    target.addEventListener('pointercancel', stopDrag)
  }

  const startDocumentDrag = createDragStartHandler(
    documentWindow,
    setDocumentWindow,
  )
  const startDocumentResize = createResizeStartHandler(
    documentWindow,
    setDocumentWindow,
    { minWidth: 420, minHeight: 360 },
  )

  return (
    <main className="rmp-screen">
      <audio
        ref={audioRef}
        src={selectedRecording.audioUrl}
        preload="metadata"
        onLoadedMetadata={(event) =>
          handleLoadedMetadata(event.currentTarget.duration)
        }
        onTimeUpdate={(event) => handleTimeUpdate(event.currentTarget.currentTime)}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onEnded={() => setIsPlaying(false)}
      />

      <TransportBar
        currentTime={currentTime}
        duration={duration}
        hasAudio={Boolean(selectedRecording.audioUrl)}
        isPlaying={isPlaying}
        selectedSid={selectedSid}
        segments={segments}
        trackFillRef={trackFillRef}
        onPlayheadDragStart={startPlayheadDrag}
        onSeek={seekToTime}
        onSeekFromTrack={seekFromTrack}
        onTogglePlayback={togglePlayback}
      />

      <section className="main-grid">
        <RecordingListPanel
          draftSearchQuery={draftRecordingSearchQuery}
          folderCounts={folderCounts}
          folders={folders}
          isUploading={isUploading}
          recordings={filteredRecordings}
          selectedFolderId={selectedFolderId}
          selectedIds={checkedRecordingIds}
          selectedRecordingId={selectedRecording.id}
          sortDirection={recordingSortDirection}
          totalVisibleCount={folderScopedRecordings.length}
          onAddFolder={() => void addFolder()}
          onAddRecordingFile={(file) => void addRecordingFile(file)}
          onApplySearch={() =>
            setAppliedRecordingSearchQuery(draftRecordingSearchQuery)
          }
          onDeleteFolder={() => void deleteSelectedFolder()}
          onDraftSearchQueryChange={setDraftRecordingSearchQuery}
          onDropRecordingToFolder={(recordingId, folderId) =>
            void moveRecordingToFolder(recordingId, folderId)
          }
          onRemoveChecked={() => void removeCheckedRecordings()}
          onResetSearch={() => {
            setDraftRecordingSearchQuery('')
            setAppliedRecordingSearchQuery('')
          }}
          onRenameFolder={(folderId, name) => void renameFolder(folderId, name)}
          onSelectFolder={setSelectedFolderId}
          onToggleSortDirection={() =>
            setRecordingSortDirection((direction) =>
              direction === 'desc' ? 'asc' : 'desc',
            )
          }
          onToggleChecked={toggleCheckedRecording}
          onSelectRecording={selectRecording}
        />

        <section className="center-panel">
          <PromptPanel
            isEnabled={isPromptEnabled}
            prompt={prompt}
            onEnabledChange={setIsPromptEnabled}
            onPromptChange={setPrompt}
          />
          <TimestampPanel
            expandedSids={expandedTimestampSids}
            selectedSid={selectedSid}
            segments={segments}
            onSeek={seekToTime}
            onSelectSegment={selectSegment}
            onToggleSegment={toggleTimestampSegment}
          />
        </section>

        <section className="summary-workspace" aria-label="요약 결과">
          <SummaryWorkspace
            openSummaryRefs={evidenceWindows.map((window) => window.summaryRef)}
            selectedSid={selectedSid}
            segments={segments}
            summaryRows={summaryRows}
            onOpenDocument={() => openFullDocument()}
            onSeek={seekToTime}
            onSelectSegment={selectSegment}
            onSelectSummary={selectSummary}
          />

          {evidenceWindows.map((evidenceWindow) => {
            const selectedSummaryRow = getSelectedSummaryRow(
              summaryRows,
              evidenceWindow.summaryRef,
            )

            if (!selectedSummaryRow) {
              return null
            }

            const evidenceTexts = getEvidenceTexts(
              selectedSummaryRow,
              transcriptItems,
            )
            const startEvidenceDrag = createDragStartHandler(
              evidenceWindow.window,
              (updater) => updateEvidenceWindow(evidenceWindow.id, updater),
            )
            const startEvidenceResize = createResizeStartHandler(
              evidenceWindow.window,
              (updater) => updateEvidenceWindow(evidenceWindow.id, updater),
              { minWidth: 320, minHeight: 220 },
            )

            return (
              <FloatingEvidenceWindow
                evidenceTexts={evidenceTexts}
                isCollapsed={evidenceWindow.isCollapsed}
                key={evidenceWindow.id}
                selectedSummaryRow={selectedSummaryRow}
                windowPosition={evidenceWindow.window}
                windowSize={evidenceWindow.window}
                onClose={() => closeEvidenceWindow(evidenceWindow.id)}
                onOpenSegmentDocument={openSegmentDocument}
                onResizeStart={startEvidenceResize}
                onSeek={seekToTime}
                onToggleCollapse={() => toggleEvidenceWindow(evidenceWindow.id)}
                onWindowDragStart={startEvidenceDrag}
              />
            )
          })}

          {isDocumentOpen && segments.length > 0 ? (
            <TranscriptDocumentWindow
              highlightId={documentHighlightId}
              title={documentTitle}
              transcriptItems={documentItems}
              windowState={documentWindow}
              onClose={() => setIsDocumentOpen(false)}
              onDragStart={startDocumentDrag}
              onHighlight={setDocumentHighlightId}
              onResizeStart={startDocumentResize}
              onSeek={seekToTime}
            />
          ) : null}
        </section>
      </section>

      {apiError ? <div className="api-error-banner">{apiError}</div> : null}
    </main>
  )
}

export default App
