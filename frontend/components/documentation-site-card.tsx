'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { RefreshCw, CheckCircle, AlertCircle, Clock, ExternalLink, Loader2 } from 'lucide-react'
import { DocumentationSite } from '@/lib/types'
import { formatDistanceToNow } from 'date-fns'
import { api } from '@/lib/api'
import { useCrawlProgress } from '@/hooks/useCrawlProgress'

interface DocumentationSiteCardProps {
  site: DocumentationSite
  onCrawlStart: (host: string) => void
  onCrawlComplete: (host: string) => void
  isCrawling: boolean
}

export function DocumentationSiteCard({ 
  site, 
  onCrawlStart, 
  onCrawlComplete,
  isCrawling: initialCrawling 
}: DocumentationSiteCardProps) {
  const [isStartingCrawl, setIsStartingCrawl] = useState(false)
  const [shouldTrack, setShouldTrack] = useState(initialCrawling)
  const { progress, isComplete, result } = useCrawlProgress(shouldTrack ? site.host : null)
  
  // Determine if currently crawling
  const isCrawling = initialCrawling || (progress !== null && !isComplete)
  
  useEffect(() => {
    if (isComplete && result) {
      // Notify parent that crawl is complete
      onCrawlComplete(site.host)
      // Stop tracking after completion
      setTimeout(() => setShouldTrack(false), 2000)
    }
  }, [isComplete, result, site.host, onCrawlComplete])
  
  useEffect(() => {
    // Start tracking if initial crawling is true
    if (initialCrawling && !shouldTrack) {
      setShouldTrack(true)
    }
  }, [initialCrawling, shouldTrack])

  const handleRecrawl = async () => {
    setIsStartingCrawl(true)
    try {
      await api.recrawlSite(`https://${site.host}`)
      onCrawlStart(site.host)
      setShouldTrack(true)
    } catch (error) {
      console.error('Failed to start crawl:', error)
    } finally {
      setIsStartingCrawl(false)
    }
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-sm transition-all">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-medium text-gray-900">{site.host}</h3>
          <p className="text-sm text-gray-500 mt-1">
            {site.total_pages} pages • {formatDistanceToNow(new Date(site.last_updated), { addSuffix: true })}
          </p>
        </div>
        <div className="ml-3">
          {isCrawling ? (
            <div className="flex items-center gap-2">
              <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
              <span className="text-sm text-blue-600">Crawling...</span>
            </div>
          ) : site.is_fresh ? (
            <CheckCircle className="w-5 h-5 text-green-500" />
          ) : site.is_stale ? (
            <AlertCircle className="w-5 h-5 text-red-500" />
          ) : (
            <Clock className="w-5 h-5 text-yellow-500" />
          )}
        </div>
      </div>

      {/* Progress Bar for Active Crawls */}
      {isCrawling && progress && (
        <div className="mb-4 space-y-2">
          <div className="w-full bg-gray-200 rounded-full h-1.5">
            <div 
              className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
              style={{ width: `${progress.progress_percent}%` }}
            />
          </div>
          <div className="text-xs text-gray-500 space-y-1">
            <div className="flex justify-between">
              <span>{progress.pages_crawled} pages crawled</span>
              <span>{progress.pages_discovered} discovered</span>
            </div>
            {progress.current_url && (
              <div className="truncate">
                Currently: {progress.current_url.replace(/^https?:\/\//, '')}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Completion Status */}
      {isComplete && result && (
        <div className="mb-4 p-3 bg-green-50 rounded-lg">
          <p className="text-sm text-green-800">
            Crawl complete! Added {result.pages_added} new pages, updated {result.pages_updated}.
          </p>
        </div>
      )}

      <div className="flex items-center gap-3">
        <Link
          href={`/docs/${site.host}`}
          className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
        >
          Browse
        </Link>
        {site.is_stale && !isCrawling && (
          <button
            onClick={handleRecrawl}
            disabled={isStartingCrawl}
            className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-50"
          >
            {isStartingCrawl ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
          </button>
        )}
        <a
          href={`https://${site.host}`}
          target="_blank"
          rel="noopener noreferrer"
          className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
        >
          <ExternalLink className="w-4 h-4" />
        </a>
      </div>
    </div>
  )
}