'use client'

import Link from 'next/link'
import { format } from 'date-fns'
import { Globe, Clock, FileText, AlertCircle } from 'lucide-react'
import type { Host } from '@/lib/types'

interface HostTableProps {
  hosts?: Host[]
  isLoading: boolean
}

export function HostTable({ hosts, isLoading }: HostTableProps) {
  if (isLoading) {
    return (
      <div className="animate-pulse">
        <div className="h-10 bg-gray-200 rounded mb-4"></div>
        <div className="h-10 bg-gray-200 rounded mb-4"></div>
        <div className="h-10 bg-gray-200 rounded"></div>
      </div>
    )
  }

  if (!hosts || hosts.length === 0) {
    return (
      <div className="text-center py-12">
        <Globe className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <p className="text-gray-600">No hosts crawled yet</p>
        <p className="text-sm text-gray-500 mt-2">Start by adding a new host to crawl</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="text-left py-3 px-4 font-medium text-gray-700">Host</th>
            <th className="text-left py-3 px-4 font-medium text-gray-700">Pages</th>
            <th className="text-left py-3 px-4 font-medium text-gray-700">Status</th>
            <th className="text-left py-3 px-4 font-medium text-gray-700">Last Crawled</th>
            <th className="text-left py-3 px-4 font-medium text-gray-700">Manifest</th>
          </tr>
        </thead>
        <tbody>
          {hosts.map((host) => (
            <tr key={host.host} className="border-b border-gray-100 hover:bg-gray-50">
              <td className="py-3 px-4">
                <Link 
                  href={`/hosts/${host.host}`}
                  className="flex items-center gap-2 text-llm-primary hover:underline"
                >
                  <Globe className="w-4 h-4" />
                  {host.host}
                </Link>
              </td>
              <td className="py-3 px-4">
                <div className="flex items-center gap-4">
                  <span className="text-sm">
                    <span className="font-medium">{host.total_pages}</span> total
                  </span>
                  {host.blocked_pages > 0 && (
                    <span className="flex items-center gap-1 text-sm text-orange-600">
                      <AlertCircle className="w-3 h-3" />
                      {host.blocked_pages} blocked
                    </span>
                  )}
                </div>
              </td>
              <td className="py-3 px-4">
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  Active
                </span>
              </td>
              <td className="py-3 px-4">
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <Clock className="w-4 h-4" />
                  {format(new Date(host.last_crawled), 'MMM d, HH:mm')}
                </div>
              </td>
              <td className="py-3 px-4">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-gray-400" />
                  <code className="text-xs bg-gray-100 px-2 py-1 rounded">
                    {host.manifest_hash}
                  </code>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}