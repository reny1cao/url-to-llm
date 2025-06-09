import axios from 'axios'
import type { Host, Page, CrawlStatus } from './types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests if available
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const api = {
  // Host operations
  async listHosts(): Promise<Host[]> {
    // Use dev endpoint in development
    const endpoint = process.env.NODE_ENV === 'development' 
      ? '/dev/hosts'
      : '/tools/llm.list_hosts'
    const { data } = await apiClient.get(endpoint)
    return data
  },

  async getManifest(host: string): Promise<string> {
    const response = await fetch(`${process.env.NEXT_PUBLIC_CDN_URL}/llm/${host}/llm.txt`)
    if (!response.ok) throw new Error('Failed to fetch manifest')
    return response.text()
  },

  async getHostPages(host: string): Promise<Page[]> {
    // This would need to be implemented in the backend
    // For now, return mock data
    return [
      {
        url: `https://${host}/`,
        status_code: 200,
        is_blocked: false,
        crawled_at: new Date().toISOString(),
        content_hash: 'abc123',
      },
      {
        url: `https://${host}/about`,
        status_code: 200,
        is_blocked: false,
        crawled_at: new Date().toISOString(),
        content_hash: 'def456',
      },
    ]
  },

  async getCrawlStatus(host: string): Promise<CrawlStatus | null> {
    // Mock crawl status - would be implemented in backend
    return null
  },

  async startCrawl(host: string) {
    // This would trigger a crawl via the backend
    // For now, just simulate it
    await new Promise(resolve => setTimeout(resolve, 1000))
    return { success: true }
  },

  // Auth operations
  async login(username: string, password: string) {
    const { data } = await apiClient.post('/auth/token', {
      username,
      password,
      grant_type: 'password',
    })
    localStorage.setItem('access_token', data.access_token)
    return data
  },

  async logout() {
    localStorage.removeItem('access_token')
  },
}