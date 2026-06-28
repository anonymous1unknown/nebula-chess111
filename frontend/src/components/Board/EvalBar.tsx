import { motion } from 'framer-motion'

interface EvalBarProps {
  eval_cp?: number | null   // centipawns (positive = white advantage)
  height?: number
  vertical?: boolean
}

function cpToPercent(cp: number | null | undefined): number {
  if (cp == null) return 50
  // Sigmoid-like mapping: 0cp = 50%, ±300cp ≈ 80%/20%
  const pct = 50 + 50 * Math.tanh(cp / 400)
  return Math.max(5, Math.min(95, pct))
}

function cpToDisplay(cp: number | null | undefined): string {
  if (cp == null) return '='
  const abs = Math.abs(cp) / 100
  if (abs > 20) return cp > 0 ? '+M' : '-M'
  const sign = cp > 0 ? '+' : cp < 0 ? '' : ''
  return `${sign}${abs.toFixed(1)}`
}

export default function EvalBar({ eval_cp, height = 400, vertical = true }: EvalBarProps) {
  const whitePct = cpToPercent(eval_cp)
  const blackPct = 100 - whitePct

  if (!vertical) {
    return (
      <div className="w-full h-4 rounded-full overflow-hidden bg-nebula-900 flex">
        <motion.div
          className="bg-white h-full"
          animate={{ width: `${whitePct}%` }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
        />
        <motion.div
          className="bg-nebula-950 h-full"
          animate={{ width: `${blackPct}%` }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
        />
      </div>
    )
  }

  return (
    <div
      className="relative flex flex-col rounded-lg overflow-hidden border border-nebula-700/40"
      style={{ width: 20, height }}
    >
      {/* Black section (top) */}
      <motion.div
        className="w-full bg-nebula-950"
        animate={{ height: `${blackPct}%` }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
      />
      {/* White section (bottom) */}
      <motion.div
        className="w-full bg-white"
        animate={{ height: `${whitePct}%` }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
      />

      {/* Score label */}
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
        <span className="text-[9px] font-mono font-bold text-nebula-400 rotate-180"
          style={{ writingMode: 'vertical-lr' }}>
          {cpToDisplay(eval_cp)}
        </span>
      </div>
    </div>
  )
}
