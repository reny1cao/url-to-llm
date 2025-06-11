'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Globe, Search, ExternalLink, RefreshCw } from 'lucide-react'
import { api } from '@/lib/api'
import { formatDistanceToNow } from 'date-fns'

export default function HostsPage() {
  const [searchTerm, setSearchTerm] = useState('')
  
  const { data: hosts, isLoading, refetch } = useQuery({
    queryKey: ['hosts'],
    queryFn: api.listHosts,
  })

  const filteredHosts = hosts?.filter((host: any) =>
    host.host.toLowerCase().includes(searchTerm.toLowerCase())
  ) || []

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Crawled Hosts</h1>
        <p className="text-gray-600">
          Manage and explore all domains with llm.txt manifests
        </p>
      </div>

      <div className="mb-6 flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search hosts..."
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <button
          onClick={() => refetch()}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="card animate-pulse">
              <div className="h-6 bg-gray-200 rounded mb-4"></div>
              <div className="space-y-2">
                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                <div className="h-4 bg-gray-200 rounded w-1/2"></div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredHosts.map((host: any) => (
            <div key={host.host} className="card hover:shadow-lg transition-shadow">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Globe className="w-5 h-5 text-blue-600" />
                  <h3 className="font-semibold text-lg">{host.host}</h3>
                </div>
                <a
                  href={`https://${host.host}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-gray-400 hover:text-gray-600"
                >
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>

              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Total Pages</span>
                  <span className="font-medium">{host.total_pages}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Accessible</span>
                  <span className="font-medium text-green-600">
                    {host.accessible_pages} ({Math.round((host.accessible_pages / host.total_pages) * 100)}%)
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Last Crawled</span>
                  <span className="font-medium">
                    {formatDistanceToNow(new Date(host.last_crawled), { addSuffix: true })}
                  </span>
                </div>
              </div>

              <div className="mt-4 pt-4 border-t border-gray-200">
                <a
                  href={`${process.env.NEXT_PUBLIC_CDN_URL}/${host.host}/llm.txt`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
                >
                  View llm.txt manifest
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          ))}
        </div>
      )}

      {filteredHosts.length === 0 && !isLoading && (
        <div className="text-center py-12">
          <Globe className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-600">
            {searchTerm ? 'No hosts match your search' : 'No hosts crawled yet'}
          </p>
        </div>
      )}
    </div>
  )
}