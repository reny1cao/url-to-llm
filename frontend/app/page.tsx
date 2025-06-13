'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Search, Plus, Loader2, BookOpen } from 'lucide-react'
import { api } from '@/lib/api'
import { DocumentationSite, DocumentationStats } from '@/lib/types'
import { DocumentationSiteCard } from '@/components/documentation-site-card'

export default function HomePage() {
  const [sites, setSites] = useState<DocumentationSite[]>([])
  const [stats, setStats] = useState<DocumentationStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [newSiteUrl, setNewSiteUrl] = useState('')
  const [isAddingSite, setIsAddingSite] = useState(false)
  const [crawlingHosts, setCrawlingHosts] = useState<Set<string>>(new Set())

  useEffect(() => {
    fetchData()
    // Poll for updates every 60 seconds to refresh site data
    const interval = setInterval(() => {
      // Only fetch if not too many sites are crawling
      if (crawlingHosts.size < 5) {
        fetchData()
      }
    }, 60000)
    return () => clearInterval(interval)
  }, [crawlingHosts.size])

  async function fetchData() {
    try {
      const [sitesData, statsData] = await Promise.all([
        api.getDocumentationSites().catch(err => {
          console.error('Failed to fetch sites:', err)
          return sites // Return current sites on error
        }),
        api.getDocumentationStats().catch(err => {
          console.error('Failed to fetch stats:', err)
          return stats // Return current stats on error
        })
      ])
      setSites(sitesData || [])
      setStats(statsData || null)
    } catch (error) {
      console.error('Failed to fetch documentation data:', error)
    } finally {
      setLoading(false)
    }
  }

  async function handleAddSite() {
    if (!newSiteUrl.trim()) return
    
    setIsAddingSite(true)
    try {
      const response = await api.recrawlSite(newSiteUrl)
      setShowAddModal(false)
      setNewSiteUrl('')
      
      // Extract hostname from URL
      const hostname = new URL(newSiteUrl).hostname
      setCrawlingHosts(prev => new Set([...prev, hostname]))
      
      // Refresh data after a moment
      setTimeout(fetchData, 2000)
    } catch (error) {
      console.error('Failed to add documentation site:', error)
    } finally {
      setIsAddingSite(false)
    }
  }

  const filteredSites = sites.filter(site => 
    site.host.toLowerCase().includes(searchQuery.toLowerCase())
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Clean Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-gray-900">Documentation</h1>
              <p className="text-sm text-gray-500 mt-1">
                AI-optimized documentation hosting
              </p>
            </div>
            
            <div className="flex items-center gap-4">
              <Link 
                href="/docs/api" 
                className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
              >
                API Reference
              </Link>
              
              <button
                onClick={() => setShowAddModal(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors"
              >
                <Plus className="w-4 h-4" />
                Add Site
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Search Bar */}
        <div className="mb-8">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search documentation..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
            />
          </div>
        </div>

        {/* Sites Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredSites.map((site) => (
            <DocumentationSiteCard
              key={site.host}
              site={site}
              isCrawling={crawlingHosts.has(site.host)}
              onCrawlStart={(host) => {
                setCrawlingHosts(prev => new Set([...prev, host]))
              }}
              onCrawlComplete={(host) => {
                setCrawlingHosts(prev => {
                  const next = new Set(prev)
                  next.delete(host)
                  return next
                })
                // Refresh data after crawl completes
                setTimeout(fetchData, 1000)
              }}
            />
          ))}
        </div>

        {/* Empty State */}
        {filteredSites.length === 0 && (
          <div className="text-center py-16">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-gray-100 rounded-full mb-4">
              <BookOpen className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              {searchQuery ? 'No results found' : 'No documentation sites yet'}
            </h3>
            <p className="text-gray-500 mb-6 max-w-sm mx-auto">
              {searchQuery 
                ? 'Try adjusting your search term.' 
                : 'Add your first documentation site to get started.'}
            </p>
            {!searchQuery && (
              <button
                onClick={() => setShowAddModal(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors"
              >
                <Plus className="w-4 h-4" />
                Add Your First Site
              </button>
            )}
          </div>
        )}
      </main>

      {/* Add Site Modal - Simplified */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div 
            className="absolute inset-0 bg-black/50"
            onClick={() => setShowAddModal(false)}
          />
          
          <div className="relative w-full max-w-md bg-white rounded-2xl shadow-xl p-6">
            <h2 className="text-xl font-semibold mb-4">Add Documentation Site</h2>
            
            <input
              type="url"
              placeholder="https://docs.example.com"
              value={newSiteUrl}
              onChange={(e) => setNewSiteUrl(e.target.value)}
              className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent mb-4"
              onKeyDown={(e) => e.key === 'Enter' && handleAddSite()}
              autoFocus
            />
            
            <div className="text-sm text-gray-500 mb-6">
              Examples: react.dev, nextjs.org/docs, tailwindcss.com
            </div>
            
            <div className="flex gap-3">
              <button
                onClick={() => setShowAddModal(false)}
                className="flex-1 px-4 py-2 border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAddSite}
                disabled={isAddingSite || !newSiteUrl.trim()}
                className="flex-1 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              >
                {isAddingSite ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Adding...
                  </>
                ) : (
                  'Add Site'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}