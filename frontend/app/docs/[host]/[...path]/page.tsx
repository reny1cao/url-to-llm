'use client'

import { useEffect, useState, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { 
  ArrowLeft,
  Search, 
  Moon,
  Sun,
  Copy,
  Check,
  ChevronRight,
  FileText,
  Loader2
} from 'lucide-react'
import { api } from '@/lib/api'
import { DocumentationContent } from '@/lib/types'
import { cn } from '@/lib/utils'
import { HierarchicalNavigation } from '@/components/hierarchical-navigation'
import { Breadcrumb } from '@/components/breadcrumb'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'

export default function DocumentationViewerPage() {
  const params = useParams()
  const router = useRouter()
  const host = params.host as string
  const path = params.path ? (params.path as string[]).join('/') : ''
  
  const [content, setContent] = useState<DocumentationContent | null>(null)
  const [navigation, setNavigation] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [searching, setSearching] = useState(false)
  const [darkMode, setDarkMode] = useState(false)
  const [copied, setCopied] = useState(false)
  const [showNavigation, setShowNavigation] = useState(false)

  // Load user preference for dark mode
  useEffect(() => {
    const savedMode = localStorage.getItem('darkMode')
    setDarkMode(savedMode === 'true')
  }, [])

  // Apply dark mode class to body
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    localStorage.setItem('darkMode', darkMode.toString())
  }, [darkMode])

  // Fetch content and navigation
  useEffect(() => {
    async function fetchData() {
      setLoading(true)
      setError(null)
      
      try {
        // Try to fetch both content and navigation, but handle errors separately
        const contentPromise = api.getDocumentationContent(host, path || '', 'markdown')
        const navPromise = api.getDocumentationNavigation(host).catch(err => {
          console.error('Failed to load navigation:', err)
          return [] // Return empty navigation on error
        })
        
        const [contentData, navData] = await Promise.all([contentPromise, navPromise])
        
        setContent(contentData)
        setNavigation(navData)
      } catch (err) {
        setError('Failed to load documentation')
        console.error('Error loading documentation:', err)
      } finally {
        setLoading(false)
      }
    }
    
    fetchData()
  }, [host, path])

  // Search functionality
  useEffect(() => {
    const delayDebounceFn = setTimeout(async () => {
      if (searchQuery.trim()) {
        setSearching(true)
        try {
          const results = await api.searchDocumentation(searchQuery, host)
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

  const copyToClipboard = async () => {
    await navigator.clipboard.writeText(window.location.href)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }


  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <p className="text-red-600 dark:text-red-400 mb-4">{error}</p>
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Documentation
        </Link>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900">
      {/* Minimal Header */}
      <header className="sticky top-0 z-40 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            {/* Breadcrumb */}
            <nav className="flex items-center gap-2 text-sm">
              <Link href="/" className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                Documentation
              </Link>
              <ChevronRight className="w-4 h-4 text-gray-400" />
              <Link href={`/docs/${host}`} className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                {host}
              </Link>
              {path && (
                <>
                  <ChevronRight className="w-4 h-4 text-gray-400" />
                  <span className="text-gray-900 dark:text-gray-100 font-medium truncate max-w-xs">
                    {content?.title || path}
                  </span>
                </>
              )}
            </nav>

            {/* Actions */}
            <div className="flex items-center gap-2">
              <button
                onClick={copyToClipboard}
                className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
                title="Copy link"
              >
                {copied ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
              </button>
              <button
                onClick={() => setDarkMode(!darkMode)}
                className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
                title="Toggle dark mode"
              >
                {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Layout with Sidebar */}
      <div className="flex min-h-screen">
        {/* Sidebar - Desktop Only */}
        {navigation.length > 0 && (
          <aside className="hidden lg:flex lg:flex-col lg:w-80 lg:border-r lg:border-gray-200 dark:lg:border-gray-700 lg:bg-gray-50 dark:lg:bg-gray-900">
            <div className="flex-1 overflow-y-auto p-6">
              <HierarchicalNavigation
                items={navigation}
                currentPath={path || '/'}
                host={host}
                className="sticky top-6"
              />
            </div>
          </aside>
        )}

        {/* Main Content */}
        <main className="flex-1 max-w-4xl mx-auto px-6 py-12">
          {/* Search Bar */}
          {navigation.length > 0 && (
            <div className="mb-8">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search this documentation..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 dark:focus:ring-gray-100"
                />
              </div>

              {/* Search Results */}
              {searchQuery && searchResults.length > 0 && (
                <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                    {searching ? 'Searching...' : `${searchResults.length} results`}
                  </p>
                  <div className="space-y-2">
                    {searchResults.slice(0, 5).map((result, idx) => (
                      <Link
                        key={idx}
                        href={`/docs/${host}/${result.path}`}
                        className="block p-3 bg-white dark:bg-gray-900 rounded-lg hover:shadow-sm transition-all"
                      >
                        <p className="font-medium text-sm text-gray-900 dark:text-gray-100">
                          {result.title}
                        </p>
                        <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-2 mt-1">
                          {result.snippet}
                        </p>
                      </Link>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Navigation Toggle for Mobile */}
          {navigation.length > 0 && (
            <button
              onClick={() => setShowNavigation(!showNavigation)}
              className="mb-6 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors lg:hidden"
            >
              {showNavigation ? 'Hide' : 'Show'} Navigation ({navigation.length} pages)
            </button>
          )}

          {/* Navigation Panel for Mobile */}
          {showNavigation && navigation.length > 0 && (
            <div className="mb-8 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg lg:hidden">
              <HierarchicalNavigation
                items={navigation}
                currentPath={path || '/'}
                host={host}
                onNavigate={() => setShowNavigation(false)}
              />
            </div>
          )}

          {/* Breadcrumb */}
          <Breadcrumb host={host} path={path || '/'} className="mb-6" />

          {/* Main Content */}
          <article>
          {content && (
            <>
              <h1 className="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-4">
                {content.title}
              </h1>
              
              {content.description && (
                <p className="text-lg text-gray-600 dark:text-gray-400 mb-8">
                  {content.description}
                </p>
              )}

              <div className="prose prose-lg dark:prose-invert max-w-none">
                <ReactMarkdown
                  components={{
                    code({ node, className, children, ...props }: any) {
                      const match = /language-(\w+)/.exec(className || '')
                      const inline = !match
                      return !inline && match ? (
                        <SyntaxHighlighter
                          style={darkMode ? oneDark : oneLight}
                          language={match[1]}
                          PreTag="div"
                          className="rounded-xl my-4"
                        >
                          {String(children).replace(/\n$/, '')}
                        </SyntaxHighlighter>
                      ) : (
                        <code className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-sm" {...props}>
                          {children}
                        </code>
                      )
                    },
                    a({ href, children }) {
                      const isExternal = href?.startsWith('http')
                      return (
                        <a
                          href={href}
                          target={isExternal ? '_blank' : undefined}
                          rel={isExternal ? 'noopener noreferrer' : undefined}
                          className="text-blue-600 dark:text-blue-400 hover:underline"
                        >
                          {children}
                        </a>
                      )
                    },
                  }}
                >
                  {content.content}
                </ReactMarkdown>
              </div>
            </>
          )}
        </article>

        </main>
      </div>
    </div>
  )
}