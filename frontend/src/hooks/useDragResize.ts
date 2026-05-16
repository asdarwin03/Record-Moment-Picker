import type { PointerEvent } from 'react'
import type { FloatingWindowState } from '../types/finalResult'

type DragOptions = {
  minX?: number
  minY?: number
}

type ResizeOptions = {
  minWidth: number
  minHeight: number
}

export function createDragStartHandler(
  windowState: FloatingWindowState,
  setWindowState: (
    updater: (current: FloatingWindowState) => FloatingWindowState,
  ) => void,
  options: DragOptions = {},
) {
  return function startDrag(event: PointerEvent<HTMLElement>) {
    if (!(event.target instanceof HTMLElement)) {
      return
    }

    if (event.target.closest('button')) {
      return
    }

    const minX = options.minX ?? 12
    const minY = options.minY ?? 86
    const startX = event.clientX
    const startY = event.clientY
    const origin = windowState
    const target = event.currentTarget

    target.setPointerCapture(event.pointerId)

    function move(moveEvent: globalThis.PointerEvent) {
      setWindowState((current) => ({
        ...current,
        x: Math.max(minX, origin.x + moveEvent.clientX - startX),
        y: Math.max(minY, origin.y + moveEvent.clientY - startY),
      }))
    }

    function stop(upEvent: globalThis.PointerEvent) {
      target.releasePointerCapture(upEvent.pointerId)
      target.removeEventListener('pointermove', move)
      target.removeEventListener('pointerup', stop)
      target.removeEventListener('pointercancel', stop)
    }

    target.addEventListener('pointermove', move)
    target.addEventListener('pointerup', stop)
    target.addEventListener('pointercancel', stop)
  }
}

export function createResizeStartHandler(
  windowState: FloatingWindowState,
  setWindowState: (
    updater: (current: FloatingWindowState) => FloatingWindowState,
  ) => void,
  options: ResizeOptions,
) {
  return function startResize(event: PointerEvent<HTMLButtonElement>) {
    const startX = event.clientX
    const startY = event.clientY
    const origin = windowState
    const target = event.currentTarget

    event.preventDefault()
    event.stopPropagation()
    target.setPointerCapture(event.pointerId)

    function resize(moveEvent: globalThis.PointerEvent) {
      setWindowState((current) => ({
        ...current,
        width: Math.max(
          options.minWidth,
          origin.width + moveEvent.clientX - startX,
        ),
        height: Math.max(
          options.minHeight,
          origin.height + moveEvent.clientY - startY,
        ),
      }))
    }

    function stop(upEvent: globalThis.PointerEvent) {
      target.releasePointerCapture(upEvent.pointerId)
      target.removeEventListener('pointermove', resize)
      target.removeEventListener('pointerup', stop)
      target.removeEventListener('pointercancel', stop)
    }

    target.addEventListener('pointermove', resize)
    target.addEventListener('pointerup', stop)
    target.addEventListener('pointercancel', stop)
  }
}
