'use client'

import { useEffect } from 'react'
import { AlertTriangle } from 'lucide-react'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <div className="flex flex-col items-center justify-center min-h-[400px]">
      <AlertTriangle className="w-12 h-12 text-red-500 mb-4" />
      <h2 className="text-2xl font-bold mb-2">Something went wrong!</h2>
      <p className="text-gray-600 mb-6">An error occurred while loading this page.</p>
      <button
        onClick={reset}
        className="btn-primary"
      >
        Try again
      </button>
    </div>
  )
}