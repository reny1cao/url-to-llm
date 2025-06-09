'use client'

import { Globe, FileText, Clock, TrendingUp } from 'lucide-react'
import type { Host } from '@/lib/types'

interface CrawlStatsProps {
  hosts?: Host[]
}

export function CrawlStats({ hosts = [] }: CrawlStatsProps) {
  const totalHosts = hosts.length
  const totalPages = hosts.reduce((sum, host) => sum + host.total_pages, 0)
  const accessiblePages = hosts.reduce((sum, host) => sum + host.accessible_pages, 0)
  const crawlRate = totalPages > 0 ? Math.round((accessiblePages / totalPages) * 100) : 0

  const stats = [
    {
      name: 'Total Hosts',
      value: totalHosts,
      icon: Globe,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
    },
    {
      name: 'Total Pages',
      value: totalPages.toLocaleString(),
      icon: FileText,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
    },
    {
      name: 'Success Rate',
      value: `${crawlRate}%`,
      icon: TrendingUp,
      color: 'text-purple-600',
      bgColor: 'bg-purple-100',
    },
    {
      name: 'Last Activity',
      value: hosts.length > 0 ? 'Active' : 'N/A',
      icon: Clock,
      color: 'text-orange-600',
      bgColor: 'bg-orange-100',
    },
  ]

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
      {stats.map((stat) => (
        <div key={stat.name} className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">{stat.name}</p>
              <p className="text-2xl font-bold mt-1">{stat.value}</p>
            </div>
            <div className={`${stat.bgColor} p-3 rounded-lg`}>
              <stat.icon className={`w-6 h-6 ${stat.color}`} />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}