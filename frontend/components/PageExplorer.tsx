'use client'

import { FileText, Check, X, Clock } from 'lucide-react'
import { format } from 'date-fns'
import type { Page } from '@/lib/types'

interface PageExplorerProps {
  pages?: Page[]
  isLoading: boolean
}

export function PageExplorer({ pages, isLoading }: PageExplorerProps) {
  if (isLoading) {
    return (
      <div className="animate-pulse space-y-2">
        <div className="h-10 bg-gray-200 rounded"></div>
        <div className="h-10 bg-gray-200 rounded"></div>
        <div className="h-10 bg-gray-200 rounded"></div>
      </div>
    )
  }

  if (!pages || pages.length === 0) {
    return (
      <div className="text-center py-8">
        <FileText className="w-8 h-8 text-gray-400 mx-auto mb-2" />
        <p className="text-gray-600">No pages crawled yet</p>
      </div>
    )
  }

  return (
    <div className="space-y-2 max-h-96 overflow-y-auto">
      {pages.map((page) => (
        <div
          key={page.url}
          className="p-3 border border-gray-200 rounded-lg hover:bg-gray-50"
        >
          <div className="flex items-center justify-between">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {page.url}
              </p>
              <div className="flex items-center gap-4 mt-1">
                <span className="text-xs text-gray-500">
                  Status: {page.status_code}
                </span>
                <span className="text-xs text-gray-500 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {format(new Date(page.crawled_at), 'MMM d, HH:mm')}
                </span>
              </div>
            </div>
            
            <div className="ml-4">
              {page.is_blocked ? (
                <div className="flex items-center gap-1 text-red-600">
                  <X className="w-4 h-4" />
                  <span className="text-xs">Blocked</span>
                </div>
              ) : (
                <div className="flex items-center gap-1 text-green-600">
                  <Check className="w-4 h-4" />
                  <span className="text-xs">Accessible</span>
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}