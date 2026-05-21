import type { Recording, RecordingFolder, Segment } from '../types/finalResult'

type ApiResponse<T> = {
  success: boolean
  data: T
  message: string | null
}

type BootstrapPayload = {
  recordings: Recording[]
  folders: RecordingFolder[]
}

type RecordDetailPayload = {
  recording?: Recording
}

type RecordStatusPayload = {
  id: string
  status: 'uploaded' | 'processing' | 'completed' | 'failed'
  frontend_status: Recording['status']
  error_message?: string | null
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? '/api'
const assetBaseUrl = apiBaseUrl.endsWith('/api')
  ? apiBaseUrl.slice(0, -4)
  : apiBaseUrl.replace(/\/api\/?$/, '')

export async function fetchBootstrap() {
  const payload = await request<BootstrapPayload>('/bootstrap')

  return {
    folders: payload.folders,
    recordings: payload.recordings.map(normalizeRecording),
  }
}

export async function uploadRecording(file: File) {
  const formData = new FormData()
  formData.append('file', file)

  const payload = await request<RecordDetailPayload>('/records', {
    method: 'POST',
    body: formData,
  })

  if (!payload.recording) {
    throw new Error('업로드 응답에 녹음 정보가 없습니다.')
  }

  return normalizeRecording(payload.recording)
}

export async function fetchRecording(recordingId: string) {
  const payload = await request<RecordDetailPayload>(
    `/records/${encodeURIComponent(recordingId)}`,
  )

  if (!payload.recording) {
    throw new Error('녹음 조회 응답에 녹음 정보가 없습니다.')
  }

  return normalizeRecording(payload.recording)
}

export function fetchRecordingStatus(recordingId: string) {
  return request<RecordStatusPayload>(
    `/records/${encodeURIComponent(recordingId)}/status`,
  )
}

export async function hideRecordings(ids: string[]) {
  const recordings = await request<Recording[]>('/records/bulk/hide', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids }),
  })

  return recordings.map(normalizeRecording)
}

export function createFolder(name: string) {
  return request<RecordingFolder>('/folders', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
}

export function renameFolder(folderId: string, name: string) {
  return request<RecordingFolder>(`/folders/${encodeURIComponent(folderId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
}

export function deleteFolder(folderId: string) {
  return request<{ id: string }>(`/folders/${encodeURIComponent(folderId)}`, {
    method: 'DELETE',
  })
}

export async function updateRecordingFolder(
  recordingId: string,
  folderId?: string,
) {
  const payload = await request<RecordDetailPayload>(
    `/records/${encodeURIComponent(recordingId)}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folderId }),
    },
  )

  if (!payload.recording) {
    throw new Error('녹음 수정 응답에 녹음 정보가 없습니다.')
  }

  return normalizeRecording(payload.recording)
}

async function request<T>(path: string, options: RequestInit = {}) {
  const response = await fetch(`${apiBaseUrl}${path}`, options)
  const payload = (await response.json().catch(() => null)) as
    | ApiResponse<T>
    | null

  if (!response.ok || !payload?.success) {
    throw new Error(payload?.message ?? `요청 실패 (${response.status})`)
  }

  return payload.data
}

function normalizeRecording(recording: Recording): Recording {
  const normalizedRecording = {
    ...recording,
    segments: normalizeSegments(recording.segments),
  }

  if (!recording.audioUrl || isAbsoluteUrl(recording.audioUrl)) {
    return normalizedRecording
  }

  return {
    ...normalizedRecording,
    audioUrl: `${assetBaseUrl}${recording.audioUrl}`,
  }
}

function isAbsoluteUrl(value: string) {
  return /^https?:\/\//i.test(value)
}

function normalizeSegments(segments: Segment[]) {
  return segments.map((segment) => {
    const texts = segment.texts.map((text, index) => {
      const legacyText = text as typeof text & { time?: number }
      const startTime = text.start_time ?? legacyText.time ?? segment.start_time
      const nextText = segment.texts[index + 1] as
        | (typeof text & { time?: number })
        | undefined

      return {
        ...text,
        start_time: startTime,
        end_time:
          text.end_time ??
          nextText?.start_time ??
          nextText?.time ??
          segment.end_time,
      }
    })

    const startTime =
      texts.length > 0
        ? Math.min(...texts.map((text) => text.start_time))
        : segment.start_time
    const endTime =
      texts.length > 0
        ? Math.max(...texts.map((text) => text.end_time))
        : segment.end_time

    return {
      ...segment,
      start_time: startTime,
      end_time: endTime,
      texts,
    }
  })
}
