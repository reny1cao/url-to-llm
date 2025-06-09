'use client'

import { Download, Copy, ExternalLink } from 'lucide-react'
import { toast } from 'sonner'

interface ManifestViewerProps {
  host: string
  manifest?: string
  isLoading: boolean
}

export function ManifestViewer({ host, manifest, isLoading }: ManifestViewerProps) {
  const manifestUrl = `${process.env.NEXT_PUBLIC_CDN_URL}/llm/${host}/llm.txt`

  const handleCopy = () => {
    if (manifest) {
      navigator.clipboard.writeText(manifest)
      toast.success('Manifest copied to clipboard')
    }
  }

  const handleDownload = () => {
    if (manifest) {
      const blob = new Blob([manifest], { type: 'text/plain' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${host}-llm.txt`
      a.click()
      window.URL.revokeObjectURL(url)
      toast.success('Manifest downloaded')
    }
  }

  if (isLoading) {
    return (
      <div className="animate-pulse">
        <div className="h-4 bg-gray-200 rounded mb-2"></div>
        <div className="h-4 bg-gray-200 rounded mb-2 w-3/4"></div>
        <div className="h-4 bg-gray-200 rounded w-1/2"></div>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <a
            href={manifestUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-llm-primary hover:underline flex items-center gap-1"
          >
            View Raw
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="p-2 text-gray-600 hover:text-gray-900"
            title="Copy to clipboard"
          >
            <Copy className="w-4 h-4" />
          </button>
          <button
            onClick={handleDownload}
            className="p-2 text-gray-600 hover:text-gray-900"
            title="Download"
          >
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      <div className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto">
        <pre className="text-sm font-mono whitespace-pre-wrap">
          {manifest || 'No manifest available'}
        </pre>
      </div>
    </div>
  )
}