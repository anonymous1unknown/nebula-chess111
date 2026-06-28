import { useEffect, useState, useRef } from 'react'
import clsx from 'clsx'

interface ClockProps {
  timeMs: number
  isActive: boolean
  label: string
  color: 'white' | 'black'
}

function fmt(ms: number): string {
  if (ms <= 0) return '0:00'
  const total = Math.ceil(ms / 1000)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

export default function Clock({ timeMs, isActive, label, color }: ClockProps) {
  const [display, setDisplay] = useState(timeMs)
  const lastTickRef = useRef<number>(Date.now())
  const rafRef = useRef<number>()

  useEffect(() => {
    setDisplay(timeMs)
    lastTickRef.current = Date.now()
  }, [timeMs])

  useEffect(() => {
    if (!isActive) {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      return
    }

    const tick = () => {
      const now = Date.now()
      const elapsed = now - lastTickRef.current
      lastTickRef.current = now
      setDisplay(prev => Math.max(0, prev - elapsed))
      rafRef.current = requestAnimationFrame(tick)
    }

    rafRef.current = requestAnimationFrame(tick)
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [isActive])

  const isLow = display < 30_000
  const isCritical = display < 10_000

  return (
    <div
      className={clsx(
        'rounded-xl px-5 py-3 flex flex-col items-center transition-all duration-300',
        isActive && 'shadow-[0_0_20px_rgba(61,45,138,0.5)]',
        isCritical && isActive && 'animate-pulse-slow',
        color === 'white'
          ? 'bg-nebula-50 text-nebula-950'
          : 'bg-nebula-900 text-nebula-50',
        isActive && !isCritical && 'ring-2 ring-nebula-400/60',
        isCritical && isActive && 'ring-2 ring-cosmic-red/80',
      )}
    >
      <span className="text-xs font-semibold uppercase tracking-widest opacity-60 mb-0.5">
        {label}
      </span>
      <span
        className={clsx(
          'font-mono font-bold tabular-nums leading-none',
          isCritical ? 'text-cosmic-red text-3xl' : isLow ? 'text-cosmic-gold text-2xl' : 'text-2xl',
        )}
      >
        {fmt(display)}
      </span>
    </div>
  )
}
