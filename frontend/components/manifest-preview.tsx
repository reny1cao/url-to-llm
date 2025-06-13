'use client'

import { useState, useEffect, useCallback } from 'react'
import { X, Copy, Check, Download, Search, FileText, Calendar, Globe } from 'lucide-react'
import { api } from '@/lib/api'
import { ConsolidatedManifest } from '@/lib/types'
import { formatBytes } from '@/lib/utils'
import { formatDistanceToNow } from 'date-fns'

interface ManifestPreviewProps {
  isOpen: boolean
  onClose: () => void
  siteHost?: string // If provided, show individual site manifest
}

export function ManifestPreview({ isOpen, onClose, siteHost }: ManifestPreviewProps) {
  const [manifest, setManifest] = useState<ConsolidatedManifest | null>(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [activeTab, setActiveTab] = useState<'overview' | 'sites' | 'json'>('overview')

  const fetchManifest = useCallback(async () => {
    setLoading(true)
    try {
      if (siteHost) {
        // Fetch individual site manifest (you'll need to implement this endpoint)
        const data = await api.getSiteDetails(siteHost)
        // Convert to consolidated format for consistency
        setManifest({
          generated_at: new Date().toISOString(),
          total_sites: 1,
          total_pages: data.total_pages,
          sites: {
            [data.host]: {
              title: data.title,
              description: data.description,
              last_updated: data.last_crawled_at,
              pages: data.total_pages,
              size_bytes: data.total_size_bytes,
              manifest_url: `/api/docs/${data.host}/manifest`,
              search_endpoint: `/api/docs/${data.host}/search`,
              pages_endpoint: `/api/docs/${data.host}/pages`
            }
          }
        })
      } else {
        const data = await api.getConsolidatedManifest('detailed')
        setManifest(data)
      }
    } catch (error) {
      console.error('Failed to fetch manifest:', error)
    } finally {
      setLoading(false)
    }
  }, [siteHost])

  useEffect(() => {
    if (isOpen) {
      fetchManifest()
    }
  }, [isOpen, fetchManifest])

  async function copyManifest() {
    if (!manifest) return
    await navigator.clipboard.writeText(JSON.stringify(manifest, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  async function downloadManifest() {
    if (!manifest) return
    const blob = new Blob([JSON.stringify(manifest, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = siteHost ? `${siteHost}-manifest.json` : 'consolidated-manifest.json'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/20 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative w-full max-w-4xl h-[80vh] mx-4 bg-white rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-100 bg-gray-50/50">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
              <FileText className="w-4 h-4 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                {siteHost ? `${siteHost} Manifest` : 'Documentation Manifest'}
              </h2>
              <p className="text-sm text-gray-500">
                {manifest ? `Generated ${formatDistanceToNow(new Date(manifest.generated_at))} ago` : 'Loading...'}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={copyManifest}
              disabled={!manifest}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              title="Copy to clipboard"
            >
              {copied ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
            </button>
            <button
              onClick={downloadManifest}
              disabled={!manifest}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              title="Download manifest"
            >
              <Download className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-gray-100">
          {[
            { id: 'overview', label: 'Overview' },
            { id: 'sites', label: 'Sites' },
            { id: 'json', label: 'JSON' }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-6 py-3 text-sm font-medium transition-colors relative ${
                activeTab === tab.id
                  ? 'text-blue-600 bg-blue-50/50'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }`}
            >
              {tab.label}
              {activeTab === tab.id && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600" />
              )}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : manifest ? (
            <>
              {activeTab === 'overview' && (
                <OverviewTab manifest={manifest} />
              )}
              {activeTab === 'sites' && (
                <SitesTab manifest={manifest} />
              )}
              {activeTab === 'json' && (
                <JsonTab manifest={manifest} />
              )}
            </>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              Failed to load manifest
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function OverviewTab({ manifest }: { manifest: ConsolidatedManifest }) {
  const totalSize = Object.values(manifest.sites).reduce((sum, site) => sum + site.size_bytes, 0)
  
  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-4">
          <div className="flex items-center gap-3">
            <Globe className="w-8 h-8 text-blue-600" />
            <div>
              <p className="text-2xl font-bold text-blue-900">{manifest.total_sites}</p>
              <p className="text-sm text-blue-700">Documentation Sites</p>
            </div>
          </div>
        </div>
        
        <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-xl p-4">
          <div className="flex items-center gap-3">
            <FileText className="w-8 h-8 text-green-600" />
            <div>
              <p className="text-2xl font-bold text-green-900">{manifest.total_pages.toLocaleString()}</p>
              <p className="text-sm text-green-700">Total Pages</p>
            </div>
          </div>
        </div>
        
        <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl p-4">
          <div className="flex items-center gap-3">
            <Search className="w-8 h-8 text-purple-600" />
            <div>
              <p className="text-2xl font-bold text-purple-900">{formatBytes(totalSize)}</p>
              <p className="text-sm text-purple-700">Total Size</p>
            </div>
          </div>
        </div>
      </div>

      {/* Agent Endpoints */}
      <div className="bg-gray-50 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Agent API Endpoints</h3>
        <div className="space-y-3">
          <EndpointCard
            method="GET"
            path="/agent/sites"
            description="List all documentation sites with freshness"
          />
          <EndpointCard
            method="GET"
            path="/agent/search?q=query"
            description="Search across all documentation"
          />
          <EndpointCard
            method="GET"
            path="/agent/manifest"
            description="Get this consolidated manifest"
          />
          <EndpointCard
            method="GET"
            path="/agent/content/{host}/{path}"
            description="Get specific page content"
          />
        </div>
      </div>
    </div>
  )
}

function SitesTab({ manifest }: { manifest: ConsolidatedManifest }) {
  return (
    <div className="space-y-4">
      {Object.entries(manifest.sites).map(([host, site]) => (
        <div key={host} className="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-sm transition-shadow">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">{host}</h3>
              <p className="text-gray-600">{site.title}</p>
              {site.description && (
                <p className="text-sm text-gray-500 mt-1">{site.description}</p>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-gray-400" />
              <span className="text-sm text-gray-500">
                {site.last_updated ? formatDistanceToNow(new Date(site.last_updated), { addSuffix: true }) : 'Never'}
              </span>
            </div>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-gray-500">Pages</p>
              <p className="font-medium">{site.pages.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-gray-500">Size</p>
              <p className="font-medium">{formatBytes(site.size_bytes)}</p>
            </div>
            <div>
              <p className="text-gray-500">Manifest</p>
              <a href={site.manifest_url} className="text-blue-600 hover:text-blue-700 font-medium">
                Download
              </a>
            </div>
            <div>
              <p className="text-gray-500">Search</p>
              <a href={site.search_endpoint} className="text-blue-600 hover:text-blue-700 font-medium">
                API
              </a>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function JsonTab({ manifest }: { manifest: ConsolidatedManifest }) {
  return (
    <div className="bg-gray-900 rounded-xl p-4 overflow-auto">
      <pre className="text-sm text-gray-100 whitespace-pre-wrap">
        {JSON.stringify(manifest, null, 2)}
      </pre>
    </div>
  )
}

function EndpointCard({ method, path, description }: { method: string, path: string, description: string }) {
  return (
    <div className="flex items-center gap-4 p-3 bg-white rounded-lg border border-gray-200">
      <span className={`px-2 py-1 text-xs font-medium rounded ${
        method === 'GET' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'
      }`}>
        {method}
      </span>
      <code className="font-mono text-sm text-gray-700 flex-1">{path}</code>
      <p className="text-sm text-gray-500">{description}</p>
    </div>
  )
}