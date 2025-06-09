'use client'

import { useState } from 'react'
import { FileText, Download, Eye, Search, ExternalLink } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { formatDistanceToNow } from 'date-fns'

export default function ManifestsPage() {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedManifest, setSelectedManifest] = useState<string | null>(null)
  
  const { data: hosts, isLoading } = useQuery({
    queryKey: ['hosts'],
    queryFn: api.listHosts,
  })

  const filteredHosts = hosts?.filter(host =>
    host.host.toLowerCase().includes(searchTerm.toLowerCase())
  ) || []

  const handleViewManifest = async (host: string) => {
    // In a real app, fetch the manifest content
    const mockManifest = `# ${host} llm.txt

Version: 1.0.0
Generated: ${new Date().toISOString()}

## Overview
This is the LLM manifest for ${host}. It provides structured information
about the site's content and access policies.

## Site Information
- Total pages: ${Math.floor(Math.random() * 1000)}
- Accessible pages: ${Math.floor(Math.random() * 900)}
- Last crawled: ${new Date().toISOString()}

## Access Guidelines
- Rate limit: 60 requests per minute
- Crawl delay: 1 second
- User-agent: *

## Content Structure
/
├── index.html
├── about/
├── blog/
├── products/
└── contact/

## License
Content is provided under the site's terms of service.
`
    setSelectedManifest(mockManifest)
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">LLM Manifests</h1>
        <p className="text-gray-600">
          Browse and download llm.txt files for all crawled domains
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <div className="mb-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search hosts..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-2 max-h-[600px] overflow-y-auto">
            {isLoading ? (
              [...Array(5)].map((_, i) => (
                <div key={i} className="p-3 bg-gray-100 rounded-lg animate-pulse">
                  <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                  <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                </div>
              ))
            ) : (
              filteredHosts.map((host) => (
                <div
                  key={host.host}
                  className="p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer"
                  onClick={() => handleViewManifest(host.host)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-gray-400" />
                      <span className="font-medium">{host.host}</span>
                    </div>
                    <Eye className="w-4 h-4 text-gray-400" />
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Updated {formatDistanceToNow(new Date(host.last_crawled), { addSuffix: true })}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="lg:col-span-2">
          {selectedManifest ? (
            <div className="card h-full">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Manifest Preview</h2>
                <div className="flex gap-2">
                  <button className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg">
                    <Download className="w-4 h-4" />
                  </button>
                  <button className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg">
                    <ExternalLink className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <pre className="bg-gray-50 p-4 rounded-lg overflow-x-auto text-sm">
                <code>{selectedManifest}</code>
              </pre>
            </div>
          ) : (
            <div className="card h-full flex items-center justify-center">
              <div className="text-center">
                <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-600">Select a host to view its manifest</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}