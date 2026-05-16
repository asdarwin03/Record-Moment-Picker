import { formatTime } from '../../utils/time'

type MockAudioPlayerProps = {
  currentTime: number
  duration: number
  onSeek: (time: number) => void
}

export function MockAudioPlayer({
  currentTime,
  duration,
  onSeek,
}: MockAudioPlayerProps) {
  const progress = duration > 0 ? (currentTime / duration) * 100 : 0

  return (
    <section className="player-panel" aria-label="오디오 플레이어">
      <button className="icon-button" type="button" aria-label="재생">
        ▶
      </button>
      <div className="player-track">
        <input
          aria-label="재생 위치"
          type="range"
          min="0"
          max={duration}
          value={currentTime}
          onChange={(event) => onSeek(Number(event.target.value))}
          style={{ backgroundSize: `${progress}% 100%` }}
        />
        <div className="player-times">
          <span>{formatTime(currentTime)}</span>
          <span>{formatTime(duration)}</span>
        </div>
      </div>
    </section>
  )
}
