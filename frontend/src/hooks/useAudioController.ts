import { useCallback, useRef, useState } from 'react'
import type { Recording, Segment } from '../types/finalResult'
import { findSegmentByTime } from '../utils/segments'

type UseAudioControllerOptions = {
  analysisDuration: number
  segments: Segment[]
  selectedRecording: Recording
  onSegmentChange: (sid: string) => void
}

export function useAudioController({
  analysisDuration,
  segments,
  selectedRecording,
  onSegmentChange,
}: UseAudioControllerOptions) {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [currentTime, setCurrentTime] = useState(segments[0]?.start_time ?? 0)
  const [audioDuration, setAudioDuration] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const duration = audioDuration || analysisDuration

  const seekToTime = useCallback(
    function seekToTime(nextTime: number) {
      const safeTime = Math.min(Math.max(0, nextTime), duration || nextTime)
      const audio = audioRef.current
      const nextSegment = findSegmentByTime(segments, safeTime)

      setCurrentTime(safeTime)

      if (audio && selectedRecording.audioUrl) {
        audio.currentTime = safeTime
      }

      if (nextSegment) {
        onSegmentChange(nextSegment.sid)
      }
    },
    [duration, onSegmentChange, segments, selectedRecording.audioUrl],
  )

  const togglePlayback = useCallback(
    async function togglePlayback() {
      const audio = audioRef.current

      if (!audio || !selectedRecording.audioUrl) {
        return
      }

      if (audio.paused) {
        await audio.play()
        setIsPlaying(true)
        return
      }

      audio.pause()
      setIsPlaying(false)
    },
    [selectedRecording.audioUrl],
  )

  const resetAudio = useCallback(function resetAudio(nextTime: number) {
    const audio = audioRef.current

    if (audio) {
      audio.pause()
      audio.currentTime = nextTime
      audio.load()
    }

    setAudioDuration(0)
    setIsPlaying(false)
    setCurrentTime(nextTime)
  }, [])

  function handleLoadedMetadata(durationValue: number) {
    setAudioDuration(Number.isFinite(durationValue) ? durationValue : 0)
  }

  function handleTimeUpdate(nextTime: number) {
    const nextSegment = findSegmentByTime(segments, nextTime)

    setCurrentTime(nextTime)

    if (nextSegment) {
      onSegmentChange(nextSegment.sid)
    }
  }

  return {
    audioRef,
    audioDuration,
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
  }
}
