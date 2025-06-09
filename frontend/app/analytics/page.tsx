'use client'

import { TrendingUp, Clock, Globe, FileText, Activity, BarChart3 } from 'lucide-react'

export default function AnalyticsPage() {
  // Mock data - would come from API
  const stats = {
    totalHosts: 42,
    totalPages: 3567,
    avgCrawlTime: 12.5,
    successRate: 87.3,
    crawlsToday: 15,
    pageGrowth: 23.5,
  }

  const topHosts = [
    { host: 'example.com', pages: 234, growth: 12.5 },
    { host: 'test.org', pages: 189, growth: -5.2 },
    { host: 'demo.io', pages: 156, growth: 34.7 },
    { host: 'sample.net', pages: 145, growth: 8.9 },
    { host: 'docs.ai', pages: 123, growth: 0 },
  ]

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Analytics</h1>
        <p className="text-gray-600">
          Track crawler performance and content growth
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">Total Hosts</h3>
            <Globe className="w-5 h-5 text-blue-600" />
          </div>
          <p className="text-2xl font-bold">{stats.totalHosts}</p>
          <p className="text-sm text-gray-500 mt-1">Active domains</p>
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">Total Pages</h3>
            <FileText className="w-5 h-5 text-green-600" />
          </div>
          <p className="text-2xl font-bold">{stats.totalPages.toLocaleString()}</p>
          <p className="text-sm text-green-600 mt-1">+{stats.pageGrowth}% this week</p>
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">Success Rate</h3>
            <TrendingUp className="w-5 h-5 text-purple-600" />
          </div>
          <p className="text-2xl font-bold">{stats.successRate}%</p>
          <p className="text-sm text-gray-500 mt-1">Accessible pages</p>
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">Avg Crawl Time</h3>
            <Clock className="w-5 h-5 text-orange-600" />
          </div>
          <p className="text-2xl font-bold">{stats.avgCrawlTime}s</p>
          <p className="text-sm text-gray-500 mt-1">Per page</p>
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">Crawls Today</h3>
            <Activity className="w-5 h-5 text-red-600" />
          </div>
          <p className="text-2xl font-bold">{stats.crawlsToday}</p>
          <p className="text-sm text-gray-500 mt-1">Completed</p>
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">API Usage</h3>
            <BarChart3 className="w-5 h-5 text-indigo-600" />
          </div>
          <p className="text-2xl font-bold">1.2k</p>
          <p className="text-sm text-gray-500 mt-1">Requests today</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Top Hosts by Page Count</h2>
          <div className="space-y-3">
            {topHosts.map((host) => (
              <div key={host.host} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Globe className="w-4 h-4 text-gray-400" />
                  <span className="font-medium">{host.host}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-gray-600">{host.pages} pages</span>
                  <span className={`text-sm font-medium ${
                    host.growth > 0 ? 'text-green-600' : host.growth < 0 ? 'text-red-600' : 'text-gray-600'
                  }`}>
                    {host.growth > 0 && '+'}{host.growth}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Crawl Activity</h2>
          <div className="h-64 flex items-center justify-center bg-gray-50 rounded-lg">
            <p className="text-gray-500">Activity chart would go here</p>
          </div>
        </div>
      </div>
    </div>
  )
}