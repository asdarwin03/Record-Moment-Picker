export function formatTime(totalSeconds: number) {
  const safeSeconds = Math.max(0, Math.floor(totalSeconds))
  const minutes = Math.floor(safeSeconds / 60)
  const seconds = safeSeconds % 60

  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

export function formatRange(start: number, end: number) {
  return `${formatTime(start)} - ${formatTime(end)}`
}
