import { useCallback, useRef, useState } from 'react'
import type { Recording, Segment } from '../types/finalResult'
import { findSegmentByTime } from '../utils/segments'

const PLAYBACK_RATES = [1, 1.25, 1.5, 2, 0.75] as const

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
  const [playbackRate, setPlaybackRate] = useState(1)
  const playbackRateRef = useRef(1)
  const duration = Math.max(audioDuration, analysisDuration)

  const applyPlaybackRate = useCallback(function applyPlaybackRate(nextRate: number) {
    const audio = audioRef.current

    if (audio) {
      audio.playbackRate = nextRate
    }
  }, [])

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
        audio.playbackRate = playbackRate
        await audio.play()
        setIsPlaying(true)
        return
      }

      audio.pause()
      setIsPlaying(false)
    },
    [playbackRate, selectedRecording.audioUrl],
  )

  const cyclePlaybackRate = useCallback(
    function cyclePlaybackRate() {
      setPlaybackRate((currentRate) => {
        const currentIndex = PLAYBACK_RATES.findIndex((rate) => rate === currentRate)
        const nextRate = PLAYBACK_RATES[(currentIndex + 1) % PLAYBACK_RATES.length]
        playbackRateRef.current = nextRate
        applyPlaybackRate(nextRate)
        return nextRate
      })
    },
    [applyPlaybackRate],
  )

  const resetAudio = useCallback(function resetAudio(nextTime: number) {
    const audio = audioRef.current

    if (audio) {
      audio.pause()
      audio.currentTime = nextTime
      audio.playbackRate = playbackRateRef.current
      audio.load()
    }

    setAudioDuration(0)
    setIsPlaying(false)
    setCurrentTime(nextTime)
  }, [])

  function handleLoadedMetadata(durationValue: number) {
    applyPlaybackRate(playbackRate)
    setAudioDuration(Number.isFinite(durationValue) ? durationValue : 0)
  }

  function handleTimeUpdate(nextTime: number) {
    const nextSegment = findSegmentByTime(segments, nextTime)

    setCurrentTime(nextTime)
    setAudioDuration((currentDuration) =>
      Math.max(currentDuration, analysisDuration, nextTime),
    )

    if (nextSegment) {
      onSegmentChange(nextSegment.sid)
    }
  }

  return {
    audioRef,
    audioDuration,
    currentTime,
    cyclePlaybackRate,
    duration,
    handleLoadedMetadata,
    handleTimeUpdate,
    isPlaying,
    playbackRate,
    resetAudio,
    seekToTime,
    setAudioDuration,
    setCurrentTime,
    setIsPlaying,
    togglePlayback,
  }
}
