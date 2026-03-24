import { useEffect, useState } from 'react'

export default function PartsList() {
  const [parts, setParts] = useState([])
  const [error, setError] = useState(null)

  const fetchParts = () => {
    fetch('/api/parts')
      .then((r) => r.json())
      .then((d) => setParts(d.parts || []))
      .catch((e) => setError(e.message))
  }

  useEffect(() => {
    fetchParts()
    const id = setInterval(fetchParts, 5000)
    return () => clearInterval(id)
  }, [])

  if (error) return <p className="text-red-400 text-xs">{error}</p>
  if (!parts.length) return <p className="text-gray-500 text-xs italic">No parts generated yet.</p>

  // Show most recent 20, newest first
  const recent = [...parts].reverse().slice(0, 20)

  return (
    <div className="overflow-auto max-h-64">
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr className="text-gray-400 border-b border-gray-700">
            <th className="text-left py-1 pr-4">Part</th>
            <th className="text-left py-1 pr-4">Tool</th>
            <th className="text-left py-1 pr-4">Passed</th>
            <th className="text-left py-1">CEM</th>
          </tr>
        </thead>
        <tbody>
          {recent.map((p, i) => (
            <tr key={i} className="border-b border-gray-800 hover:bg-gray-800">
              <td className="py-1 pr-4 text-blue-300 truncate max-w-xs">{p.part_id || '—'}</td>
              <td className="py-1 pr-4 text-gray-300">{p.tool_used || '—'}</td>
              <td className={`py-1 pr-4 ${p.passed ? 'text-green-400' : 'text-red-400'}`}>
                {p.passed ? 'PASS' : 'FAIL'}
              </td>
              <td className={`py-1 ${p.cem_passed ? 'text-teal-400' : 'text-gray-500'}`}>
                {p.cem_passed == null ? '—' : p.cem_passed ? 'PASS' : 'FAIL'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
