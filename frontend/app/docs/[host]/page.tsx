'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { 
  ArrowLeft, 
  Search, 
  FileText, 
  ExternalLink,
  Loader2,
  ChevronRight
} from 'lucide-react'
import { api } from '@/lib/api'
import { SiteDetails } from '@/lib/types'
import { formatDistanceToNow } from 'date-fns'
import { formatBytes, cn } from '@/lib/utils'
import { HierarchicalNavigation } from '@/components/hierarchical-navigation'

export default function DocumentationSitePage() {
  const params = useParams()
  const router = useRouter()
  const host = params.host as string
  
  const [site, setSite] = useState<SiteDetails | null>(null)
  const [navigation, setNavigation] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [searching, setSearching] = useState(false)

  useEffect(() => {
    async function fetchData() {
      setLoading(true)
      try {
        const [siteData, navData] = await Promise.all([
          api.getSiteDetails(host),
          api.getDocumentationNavigation(host).catch(() => [])
        ])
        setSite(siteData)
        setNavigation(navData)
      } catch (error) {
        console.error('Failed to fetch site data:', error)
      } finally {
        setLoading(false)
      }
    }
    
    fetchData()
  }, [host])

  // Search functionality
  useEffect(() => {
    const delayDebounceFn = setTimeout(async () => {
      if (searchQuery.trim()) {
        setSearching(true)
        try {
          const results = await api.searchDocumentationSite(searchQuery, host)
          setSearchResults(results.results || [])
        } catch (err) {
          console.error('Search error:', err)
        } finally {
          setSearching(false)
        }
      } else {
        setSearchResults([])
      }
    }, 300)

    return () => clearTimeout(delayDebounceFn)
  }, [searchQuery, host])


  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <nav className="flex items-center gap-2 text-sm">
              <Link href="/" className="text-gray-500 hover:text-gray-700">
                Documentation
              </Link>
              <ChevronRight className="w-4 h-4 text-gray-400" />
              <span className="text-gray-900 font-medium">{host}</span>
            </nav>
            
            <a
              href={`https://${host}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700"
            >
              Visit Site
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* Site Info */}
        <div className="mb-8">
          <h1 className="text-3xl font-semibold text-gray-900 mb-2">
            {site?.title || host}
          </h1>
          {site?.description && (
            <p className="text-gray-600">{site.description}</p>
          )}
          <div className="flex items-center gap-4 mt-4 text-sm text-gray-500">
            <span>{site?.total_pages || 0} pages</span>
            <span>•</span>
            <span>{site?.total_size_bytes ? formatBytes(site.total_size_bytes) : '0 B'}</span>
            <span>•</span>
            <span>
              Updated {site?.last_crawled_at 
                ? formatDistanceToNow(new Date(site.last_crawled_at), { addSuffix: true })
                : 'never'}
            </span>
          </div>
        </div>

        {/* Search Bar */}
        <div className="mb-8">
          <div className="relative max-w-2xl">
            <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search documentation..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-3 bg-white border border-gray-200 rounded-lg text-lg focus:outline-none focus:ring-2 focus:ring-gray-900"
            />
          </div>
        </div>

        {/* Search Results or Navigation */}
        {searchQuery && searchResults.length > 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">
              Search Results ({searchResults.length})
            </h2>
            <div className="space-y-3">
              {searchResults.map((result, idx) => (
                <Link
                  key={idx}
                  href={`/docs/${host}/${result.path}`}
                  className="block p-4 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <h3 className="font-medium text-gray-900 mb-1">{result.title}</h3>
                  <p className="text-sm text-gray-600 line-clamp-2">{result.snippet}</p>
                  <p className="text-xs text-gray-400 mt-2">{result.path}</p>
                </Link>
              ))}
            </div>
          </div>
        ) : searchQuery && searching ? (
          <div className="text-center py-8">
            <Loader2 className="w-8 h-8 animate-spin text-gray-400 mx-auto" />
          </div>
        ) : searchQuery && searchResults.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-600">No results found for &ldquo;{searchQuery}&rdquo;</p>
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">
              Pages
            </h2>
            {navigation.length > 0 ? (
              <HierarchicalNavigation
                items={navigation}
                currentPath="/"
                host={host}
              />
            ) : (
              <div className="text-center py-8">
                <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-600">No pages found</p>
                <p className="text-sm text-gray-500 mt-2">
                  The site may still be crawling. Please check back in a few minutes.
                </p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}