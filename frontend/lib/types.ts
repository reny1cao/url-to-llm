export interface Host {
  host: string
  total_pages: number
  accessible_pages: number
  blocked_pages: number
  last_crawled: string
  manifest_hash: string
  change_frequency: string
}

export interface Page {
  url: string
  status_code: number
  is_blocked: boolean
  crawled_at: string
  content_hash: string
  error_message?: string
}

export interface CrawlStatus {
  session_id: number
  host: string
  status: 'running' | 'completed' | 'failed'
  progress: number
  pages_crawled: number
  pages_changed: number
  started_at: string
  eta?: string
}

// Documentation types
export interface DocumentationSite {
  host: string
  total_pages: number
  last_updated: string
  manifest_url: string
  search_url: string
  is_fresh: boolean
  is_stale: boolean
}

export interface DocumentationSearchResult {
  site: string
  url: string
  path: string
  title: string
  snippet: string
  relevance_score: number
  last_updated: string
}

export interface DocumentationStats {
  total_sites: number
  total_pages: number
  total_size_bytes: number
  oldest_update: string | null
  newest_update: string | null
  freshness: {
    fresh: number
    recent: number
    stale: number
  }
}

export interface SiteDetails {
  id: string
  host: string
  title: string
  description: string | null
  favicon_url: string | null
  language: string
  is_active: boolean
  created_at: string
  updated_at: string
  last_crawled_at: string | null
  total_pages: number
  total_size_bytes: number
}

export interface ConsolidatedManifest {
  generated_at: string
  total_sites: number
  total_pages: number
  sites: Record<string, {
    title: string
    description: string | null
    last_updated: string | null
    pages: number
    size_bytes: number
    manifest_url: string
    search_endpoint: string
    pages_endpoint: string
    recent_updates?: Array<{
      path: string
      title: string
      updated: string
    }>
  }>
}

export interface DocumentationContent {
  title: string
  description?: string
  content: string
  format: 'markdown' | 'html'
  path: string
  last_updated: string
}

export interface NavigationItem {
  title: string
  path: string
  children?: NavigationItem[]
  order?: number
}