import { useState } from 'react'

export default function GoalInput({ onSubmit, disabled }) {
  const [goal, setGoal] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    const trimmed = goal.trim()
    if (!trimmed) return
    onSubmit(trimmed)
    setGoal('')
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        className="flex-1 bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm
                   focus:outline-none focus:border-blue-500 placeholder-gray-500"
        placeholder="e.g. ARIA ratchet ring, 213mm OD, 24 teeth, 21mm thick"
        value={goal}
        onChange={(e) => setGoal(e.target.value)}
        disabled={disabled}
      />
      <button
        type="submit"
        disabled={disabled || !goal.trim()}
        className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-40
                   rounded text-sm font-semibold transition-colors"
      >
        Generate
      </button>
    </form>
  )
}
