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