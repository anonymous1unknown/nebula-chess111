import { useEffect, useRef } from 'react'
import clsx from 'clsx'

interface MoveListProps {
  moves: string[]
  currentMove?: number
  onSelectMove?: (idx: number) => void
}

export default function MoveList({ moves, currentMove, onSelectMove }: MoveListProps) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [moves.length])

  const pairs: [string, string | undefined][] = []
  for (let i = 0; i < moves.length; i += 2) {
    pairs.push([moves[i], moves[i + 1]])
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-3 space-y-0.5">
        {pairs.length === 0 && (
          <p className="text-nebula-400 text-sm text-center py-4">No moves yet</p>
        )}
        {pairs.map((pair, i) => (
          <div key={i} className="flex items-center gap-1 rounded-lg overflow-hidden">
            <span className="w-7 text-right text-nebula-500 text-xs font-mono shrink-0 px-1">
              {i + 1}.
            </span>
            {pair.map((san, j) => {
              if (!san) return <div key={j} className="flex-1" />
              const moveIdx = i * 2 + j
              const isCurrent = currentMove === moveIdx
              return (
                <button
                  key={j}
                  onClick={() => onSelectMove?.(moveIdx)}
                  className={clsx(
                    'flex-1 px-2 py-1 text-sm font-mono text-left rounded transition-all duration-150',
                    isCurrent
                      ? 'bg-nebula-500 text-white font-semibold'
                      : 'text-nebula-100 hover:bg-nebula-700/50',
                  )}
                >
                  {san}
                </button>
              )
            })}
            {pair.length < 2 && <div className="flex-1" />}
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  )
}
