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

  // Get crawl history for this host
  const { data: jobHistory } = useQuery({
    queryKey: ['job-history', host],
    queryFn: async () => {
      const jobs = await api.getCrawlHistory(10, 0)
      // Filter jobs for this specific host
      return jobs.filter((job: any) => job.host === host)
    },
  })

  // Get the latest job for this host
  const latestJob = jobHistory?.[0]
  
  // Get job status if there's an active job
  const { data: crawlStatus } = useQuery({
    queryKey: ['crawl-status', latestJob?.id],
    queryFn: () => latestJob ? api.getCrawlStatus(latestJob.id) : null,
    enabled: !!latestJob?.id && ['pending', 'running'].includes(latestJob?.status),
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
          <h2 className="text-xl font-semibold mb-4">Crawl History</h2>
          {jobHistory && jobHistory.length > 0 ? (
            <div className="space-y-4">
              {jobHistory.map((job: any) => (
                <div key={job.id} className="border rounded-lg p-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium">Job {job.id.slice(0, 8)}</p>
                      <p className="text-sm text-gray-600">
                        Status: <span className={`font-medium ${
                          job.status === 'completed' ? 'text-green-600' :
                          job.status === 'running' ? 'text-blue-600' :
                          job.status === 'failed' ? 'text-red-600' :
                          'text-yellow-600'
                        }`}>{job.status}</span>
                      </p>
                      <p className="text-sm text-gray-600">
                        Pages: {job.pages_crawled || 0} crawled, {job.pages_changed || 0} changed
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {new Date(job.created_at).toLocaleString()}
                      </p>
                    </div>
                    <Link 
                      href={`/jobs/${job.id}`}
                      className="text-blue-600 hover:text-blue-800 text-sm"
                    >
                      View Details →
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">No crawl history for this host</p>
          )}
        </div>
      </div>
    </div>
  )
}