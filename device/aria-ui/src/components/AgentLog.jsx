import { useEffect, useRef } from 'react'

const TYPE_COLORS = {
  step:        'text-blue-400',
  tool_call:   'text-yellow-400',
  llm_output:  'text-purple-400',
  validation:  'text-orange-400',
  cem:         'text-teal-400',
  grasshopper: 'text-green-400',
  error:       'text-red-400',
  complete:    'text-green-300 font-semibold',
}

export default function AgentLog({ events }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events])

  return (
    <div className="h-96 overflow-y-auto bg-gray-900 border border-gray-700 rounded p-3 text-xs space-y-0.5">
      {events.length === 0 && (
        <p className="text-gray-500 italic">Waiting for pipeline events…</p>
      )}
      {events.map((ev, i) => (
        <div key={i} className="flex gap-2 leading-5">
          <span className="text-gray-500 shrink-0">{ev.timestamp}</span>
          <span className={`shrink-0 uppercase w-20 ${TYPE_COLORS[ev.type] ?? 'text-gray-300'}`}>
            [{ev.type}]
          </span>
          <span className="text-gray-200 break-all">{ev.message}</span>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
