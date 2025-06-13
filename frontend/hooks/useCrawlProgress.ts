import { useEffect, useRef, useState, useCallback } from 'react'

interface CrawlProgress {
  pages_crawled: number
  pages_discovered: number
  pages_added: number
  pages_updated: number
  current_url?: string
  bytes_downloaded: number
  progress_percent: number
}

interface CrawlResult {
  pages_crawled: number
  pages_added: number
  pages_updated: number
  errors: string[]
  success: boolean
}

export function useCrawlProgress(host: string | null) {
  const [progress, setProgress] = useState<CrawlProgress | null>(null)
  const [isComplete, setIsComplete] = useState(false)
  const [result, setResult] = useState<CrawlResult | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  const connect = useCallback(() => {
    if (!host) return
    
    // Close existing connection if any
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    const wsUrl = `ws://localhost:8000/ws/crawl/${host}`
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log(`Connected to crawl progress for ${host}`)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'progress') {
          setProgress({
            pages_crawled: data.pages_crawled,
            pages_discovered: data.pages_discovered,
            pages_added: data.pages_added,
            pages_updated: data.pages_updated,
            current_url: data.current_url,
            bytes_downloaded: data.bytes_downloaded,
            progress_percent: data.progress_percent
          })
          setIsComplete(false)
        } else if (data.type === 'complete') {
          setResult({
            pages_crawled: data.pages_crawled,
            pages_added: data.pages_added,
            pages_updated: data.pages_updated,
            errors: data.errors || [],
            success: data.success
          })
          setIsComplete(true)
          setProgress(null)
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.onclose = () => {
      console.log(`Disconnected from crawl progress for ${host}`)
      // Only reconnect if we haven't completed and this is the current host
      if (host && !isComplete && wsRef.current === ws) {
        setTimeout(() => connect(), 5000)
      }
    }

    wsRef.current = ws

    // Send periodic pings to keep connection alive
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping')
      }
    }, 30000)

    return () => {
      clearInterval(pingInterval)
    }
  }, [host])

  useEffect(() => {
    if (host) {
      connect()
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [host, connect])

  const reset = useCallback(() => {
    setProgress(null)
    setResult(null)
    setIsComplete(false)
  }, [])

  return {
    progress,
    isComplete,
    result,
    reset,
    isConnected: wsRef.current?.readyState === WebSocket.OPEN
  }
}