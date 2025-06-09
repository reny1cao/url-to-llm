'use client'

import { Activity } from 'lucide-react'
import type { CrawlStatus } from '@/lib/types'

interface CrawlProgressProps {
  status: CrawlStatus
}

export function CrawlProgress({ status }: CrawlProgressProps) {
  return (
    <div className="card bg-blue-50 border-blue-200">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-blue-600 animate-pulse" />
          <span className="font-medium text-blue-900">Crawl in Progress</span>
        </div>
        
        <span className="text-sm text-blue-700">
          {status.pages_crawled} pages crawled
        </span>
      </div>
      
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-blue-700">Progress</span>
          <span className="text-blue-900 font-medium">{Math.round(status.progress)}%</span>
        </div>
        
        <div className="w-full bg-blue-200 rounded-full h-2">
          <div 
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${status.progress}%` }}
          />
        </div>
        
        {status.eta && (
          <p className="text-sm text-blue-700 mt-2">
            Estimated completion: {new Date(status.eta).toLocaleTimeString()}
          </p>
        )}
      </div>
    </div>
  )
}