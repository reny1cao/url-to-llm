'use client'

import { useParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { ManifestViewer } from '@/components/ManifestViewer'
import { PageExplorer } from '@/components/PageExplorer'
import { CrawlProgress } from '@/components/CrawlProgress'
import { api } from '@/lib/api'
import { ArrowLeft } from 'lucide-react'
import Link from 'next/link'

export default function HostDetailPage() {
  const params = useParams()
  const host = params.host as string

  const { data: manifest, isLoading: manifestLoading } = useQuery({
    queryKey: ['manifest', host],
    queryFn: () => api.getManifest(host),
  })

  const { data: pages, isLoading: pagesLoading } = useQuery({
    queryKey: ['pages', host],
    queryFn: () => api.getHostPages(host),
  })

  const { data: crawlStatus } = useQuery({
    queryKey: ['crawl-status', host],
    queryFn: () => api.getCrawlStatus(host),
    refetchInterval: 5000, // Poll every 5 seconds
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/" className="text-gray-600 hover:text-gray-900">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <h1 className="text-3xl font-bold text-gray-900">{host}</h1>
      </div>

      {crawlStatus && crawlStatus.status === 'running' && (
        <CrawlProgress status={crawlStatus} />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">LLM Manifest</h2>
          <ManifestViewer 
            host={host} 
            manifest={manifest} 
            isLoading={manifestLoading} 
          />
        </div>

        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Crawled Pages</h2>
          <PageExplorer 
            pages={pages} 
            isLoading={pagesLoading} 
          />
        </div>
      </div>
    </div>
  )
}