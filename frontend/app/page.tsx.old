'use client'

import { useQuery } from '@tanstack/react-query'
import { HostTable } from '@/components/HostTable'
import { CrawlStats } from '@/components/CrawlStats'
import { QuickActions } from '@/components/QuickActions'
import { api } from '@/lib/api'

export default function DashboardPage() {
  const { data: hosts, isLoading } = useQuery({
    queryKey: ['hosts'],
    queryFn: api.listHosts,
    refetchInterval: 30000, // Refetch every 30 seconds
  })

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <QuickActions />
      </div>

      <CrawlStats hosts={hosts} />

      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Crawled Hosts</h2>
        <HostTable hosts={hosts} isLoading={isLoading} />
      </div>
    </div>
  )
}