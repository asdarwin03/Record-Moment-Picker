import type { MouseEvent, PointerEvent, RefObject } from 'react'
import type { Segment } from '../../types/finalResult'
import { formatRange, formatTime } from '../../utils/time'
import { getTone } from '../../data/demoRecordings'

type TransportBarProps = {
  currentTime: number
  duration: number
  isPlaying: boolean
  selectedSid: string
  hasAudio: boolean
  segments: Segment[]
  trackFillRef: RefObject<HTMLDivElement | null>
  onSeek: (time: number) => void
  onSeekFromTrack: (event: MouseEvent<HTMLDivElement>) => void
  onPlayheadDragStart: (event: PointerEvent<HTMLButtonElement>) => void
  onTogglePlayback: () => void
}

export function TransportBar({
  currentTime,
  duration,
  isPlaying,
  selectedSid,
  hasAudio,
  segments,
  trackFillRef,
  onSeek,
  onSeekFromTrack,
  onPlayheadDragStart,
  onTogglePlayback,
}: TransportBarProps) {
  return (
    <header className="transport-bar" aria-label="재생 컨트롤">
      <button className="record-dot" type="button" aria-label="녹음" />
      <button className="speed-button" type="button">
        1.0x
      </button>
      <button
        className="round-tool"
        type="button"
        onClick={() => onSeek(currentTime - 10)}
        aria-label="10초 뒤로"
      >
        10
      </button>
      <button
        className="play-button"
        type="button"
        onClick={onTogglePlayback}
        disabled={!hasAudio}
        aria-label={isPlaying ? '일시정지' : '재생'}
        title={hasAudio ? undefined : '오디오 파일을 추가하면 재생할 수 있습니다'}
      >
        {isPlaying ? 'Ⅱ' : '▶'}
      </button>
      <button
        className="round-tool"
        type="button"
        onClick={() => onSeek(currentTime + 10)}
        aria-label="10초 앞으로"
      >
        10
      </button>
      <time className="current-time">{formatTime(currentTime)}</time>
      <div className="overview-track" aria-label="녹음 구간 개요">
        <div
          className="overview-track-fill"
          ref={trackFillRef}
          onClick={onSeekFromTrack}
          role="slider"
          aria-label="재생 위치"
          aria-valuemin={0}
          aria-valuemax={Math.round(duration)}
          aria-valuenow={Math.round(currentTime)}
        >
          {segments.map((segment, index) => (
            <div
              className={`track-segment ${getTone(index)} ${
                segment.sid === selectedSid ? 'selected' : ''
              }`}
              key={segment.sid}
              style={{
                left: `${(segment.start_time / duration) * 100}%`,
                width: `${
                  ((segment.end_time - segment.start_time) / duration) * 100
                }%`,
              }}
            >
              <button
                className="segment-hit"
                type="button"
                aria-label={`${segment.title} ${formatRange(
                  segment.start_time,
                  segment.end_time,
                )}`}
              />
              {segment.important.map((moment) => (
                <button
                  className="important-marker"
                  key={`${segment.sid}-${moment.time}`}
                  type="button"
                  style={{
                    left: `${
                      ((moment.time - segment.start_time) /
                        (segment.end_time - segment.start_time)) *
                      100
                    }%`,
                  }}
                  onClick={(event) => {
                    event.stopPropagation()
                    onSeek(moment.time)
                  }}
                  aria-label={`${formatTime(moment.time)} ${moment.title}`}
                  title={`${formatTime(moment.time)} ${moment.title}`}
                />
              ))}
            </div>
          ))}
        </div>
        {duration > 0 ? (
          <button
            type="button"
            className="playhead-marker"
            onPointerDown={onPlayheadDragStart}
            style={{
              left: `${Math.min(
                100,
                Math.max(0, (currentTime / duration) * 100),
              )}%`,
            }}
            aria-label={`현재 재생 위치 ${formatTime(currentTime)}`}
          />
        ) : null}
      </div>
      <time className="total-time">{formatTime(duration)}</time>
      <button className="menu-button" type="button" aria-label="목록">
        ≡
      </button>
    </header>
  )
}
