import axios from 'axios'
import type { Host, Page, CrawlStatus } from './types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// PKCE helper functions
function generateRandomString(length: number): string {
  const array = new Uint8Array(length)
  crypto.getRandomValues(array)
  return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('')
}

function generateCodeVerifier(): string {
  const array = new Uint8Array(32)
  crypto.getRandomValues(array)
  return btoa(String.fromCharCode(...array))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '')
}

async function generateCodeChallenge(verifier: string): Promise<string> {
  const encoder = new TextEncoder()
  const data = encoder.encode(verifier)
  const digest = await crypto.subtle.digest('SHA-256', data)
  return btoa(String.fromCharCode(...new Uint8Array(digest)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '')
}

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
  // Crawl operations
  async startCrawl(url: string, maxPages: number = 100) {
    const { data } = await apiClient.post('/crawl/start', {
      host: new URL(url).hostname,
      max_pages: maxPages,
      follow_links: true,
      respect_robots_txt: true,
      priority: 1
    })
    return data
  },

  async getCrawlStatus(jobId: string) {
    const { data } = await apiClient.get(`/crawl/status/${jobId}`)
    return data
  },

  async getCrawlHistory(limit: number = 10, offset: number = 0, status?: string) {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString()
    })
    if (status) params.append('status', status)
    
    const { data } = await apiClient.get(`/crawl/history?${params}`)
    return data
  },

  async getJobProgress(jobId: string) {
    const { data } = await apiClient.get(`/crawl/jobs/${jobId}/progress`)
    return data
  },

  async cancelJob(jobId: string) {
    const { data } = await apiClient.post(`/crawl/jobs/${jobId}/cancel`)
    return data
  },

  async testCrawl(url: string) {
    const { data } = await apiClient.post('/crawl/test', { url })
    return data
  },

  // MCP operations
  async listHosts() {
    const { data } = await apiClient.get('/mcp/hosts')
    return data
  },

  async getManifest(host: string) {
    const { data } = await apiClient.get(`/mcp/manifest/${host}`)
    return data.content
  },

  async searchManifests(query: string) {
    const { data } = await apiClient.get(`/mcp/search?q=${encodeURIComponent(query)}`)
    return data
  },

  // User operations
  async register(email: string, username: string, password: string) {
    const { data } = await apiClient.post('/users/register', {
      email,
      username,
      password
    })
    return data
  },

  async getCurrentUser() {
    const { data } = await apiClient.get('/users/me')
    return data
  },

  async updateProfile(updates: { email?: string; username?: string }) {
    const { data } = await apiClient.patch('/users/me', updates)
    return data
  },

  async changePassword(currentPassword: string, newPassword: string) {
    await apiClient.post('/users/me/change-password', {
      current_password: currentPassword,
      new_password: newPassword
    })
  },

  // OAuth2.1 PKCE operations
  async startOAuthFlow() {
    // Generate PKCE challenge
    const codeVerifier = generateCodeVerifier()
    const codeChallenge = await generateCodeChallenge(codeVerifier)
    
    // Store verifier for later use
    sessionStorage.setItem('code_verifier', codeVerifier)
    
    // Build authorization URL
    const params = new URLSearchParams({
      response_type: 'code',
      client_id: process.env.NEXT_PUBLIC_OAUTH_CLIENT_ID || 'llm-ui',
      redirect_uri: `${window.location.origin}/auth/callback`,
      scope: 'read:llm write:crawl',
      state: generateRandomString(32),
      code_challenge: codeChallenge,
      code_challenge_method: 'S256'
    })
    
    sessionStorage.setItem('oauth_state', params.get('state')!)
    
    // Redirect to authorization endpoint
    window.location.href = `${API_URL}/auth/authorize?${params}`
  },

  async handleOAuthCallback(code: string, state: string) {
    // Verify state
    const savedState = sessionStorage.getItem('oauth_state')
    if (state !== savedState) {
      throw new Error('Invalid state parameter')
    }
    
    // Get code verifier
    const codeVerifier = sessionStorage.getItem('code_verifier')
    if (!codeVerifier) {
      throw new Error('Code verifier not found')
    }
    
    // Exchange code for tokens
    const { data } = await apiClient.post('/auth/token', {
      grant_type: 'authorization_code',
      code,
      redirect_uri: `${window.location.origin}/auth/callback`,
      code_verifier: codeVerifier,
      client_id: process.env.NEXT_PUBLIC_OAUTH_CLIENT_ID || 'llm-ui'
    })
    
    // Store tokens
    localStorage.setItem('access_token', data.access_token)
    if (data.refresh_token) {
      localStorage.setItem('refresh_token', data.refresh_token)
    }
    
    // Clean up
    sessionStorage.removeItem('code_verifier')
    sessionStorage.removeItem('oauth_state')
    
    return data
  },

  async refreshToken() {
    const refreshToken = localStorage.getItem('refresh_token')
    if (!refreshToken) {
      throw new Error('No refresh token available')
    }
    
    const { data } = await apiClient.post('/auth/token', {
      grant_type: 'refresh_token',
      refresh_token: refreshToken,
      client_id: process.env.NEXT_PUBLIC_OAUTH_CLIENT_ID || 'llm-ui'
    })
    
    localStorage.setItem('access_token', data.access_token)
    if (data.refresh_token) {
      localStorage.setItem('refresh_token', data.refresh_token)
    }
    
    return data
  },

  async logout() {
    const token = localStorage.getItem('access_token')
    if (token) {
      try {
        await apiClient.post('/auth/revoke', { token })
      } catch (error) {
        console.error('Failed to revoke token:', error)
      }
    }
    
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  },
}