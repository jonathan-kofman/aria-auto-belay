import { useState, useEffect, useCallback } from 'react'
import GoalInput from './components/GoalInput'
import AgentLog from './components/AgentLog'
import PartsList from './components/PartsList'

const MAX_EVENTS = 500

export default function App() {
  const [events, setEvents] = useState([])
  const [running, setRunning] = useState(false)
  const [lastGoal, setLastGoal] = useState('')

  // SSE subscription
  useEffect(() => {
    const es = new EventSource('/api/log/stream')
    es.onmessage = (e) => {
      try {
        const ev = JSON.parse(e.data)
        setEvents((prev) => {
          const next = [...prev, ev]
          return next.length > MAX_EVENTS ? next.slice(-MAX_EVENTS) : next
        })
        if (ev.type === 'complete' || ev.type === 'error') {
          setRunning(false)
        }
      } catch {
        // ignore parse errors from heartbeat lines
      }
    }
    return () => es.close()
  }, [])

  const handleSubmit = useCallback(async (goal) => {
    setRunning(true)
    setLastGoal(goal)
    setEvents((prev) => [
      ...prev,
      {
        type: 'step',
        timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
        message: `Submitting: ${goal}`,
        data: {},
      },
    ])
    try {
      await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal }),
      })
    } catch (err) {
      setEvents((prev) => [
        ...prev,
        {
          type: 'error',
          timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
          message: `Request failed: ${err.message}`,
          data: {},
        },
      ])
      setRunning(false)
    }
  }, [])

  return (
    <div className="min-h-screen p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold text-white tracking-tight">ARIA-OS</h1>
        <span className="text-xs text-gray-500">autonomous CAD pipeline</span>
        {running && (
          <span className="ml-auto text-xs text-blue-400 animate-pulse">Running…</span>
        )}
      </div>

      {/* Goal input */}
      <section className="space-y-2">
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest">Goal</h2>
        <GoalInput onSubmit={handleSubmit} disabled={running} />
        {lastGoal && (
          <p className="text-xs text-gray-500">Last: {lastGoal}</p>
        )}
      </section>

      {/* Agent log */}
      <section className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest">
            Pipeline log
          </h2>
          <button
            className="text-xs text-gray-500 hover:text-gray-300"
            onClick={() => setEvents([])}
          >
            Clear
          </button>
        </div>
        <AgentLog events={events} />
      </section>

      {/* Parts table */}
      <section className="space-y-2">
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest">
          Generated parts
        </h2>
        <PartsList />
      </section>
    </div>
  )
}
