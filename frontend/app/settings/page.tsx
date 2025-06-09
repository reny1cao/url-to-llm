'use client'

import { useState } from 'react'
import { Save, AlertCircle } from 'lucide-react'

export default function SettingsPage() {
  const [settings, setSettings] = useState({
    crawlRateLimit: 4,
    crawlTimeout: 30,
    maxCrawlDepth: 10,
    respectRobotsTxt: true,
    enableStealth: true,
    autoCrawlEnabled: false,
    autoCrawlInterval: 24,
  })

  const [saved, setSaved] = useState(false)

  const handleSave = () => {
    // In a real app, this would save to backend
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Settings</h1>
        <p className="text-gray-600">
          Configure crawler behavior and system preferences
        </p>
      </div>

      <div className="space-y-6">
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Crawler Configuration</h2>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Rate Limit (requests per minute)
              </label>
              <input
                type="number"
                min="1"
                max="60"
                value={settings.crawlRateLimit}
                onChange={(e) => setSettings({ ...settings, crawlRateLimit: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <p className="text-sm text-gray-500 mt-1">
                Maximum requests per minute per domain
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Timeout (seconds)
              </label>
              <input
                type="number"
                min="5"
                max="120"
                value={settings.crawlTimeout}
                onChange={(e) => setSettings({ ...settings, crawlTimeout: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Maximum Crawl Depth
              </label>
              <input
                type="number"
                min="1"
                max="50"
                value={settings.maxCrawlDepth}
                onChange={(e) => setSettings({ ...settings, maxCrawlDepth: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div className="space-y-2">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={settings.respectRobotsTxt}
                  onChange={(e) => setSettings({ ...settings, respectRobotsTxt: e.target.checked })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm font-medium text-gray-700">
                  Respect robots.txt
                </span>
              </label>

              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={settings.enableStealth}
                  onChange={(e) => setSettings({ ...settings, enableStealth: e.target.checked })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm font-medium text-gray-700">
                  Enable stealth mode
                </span>
              </label>
            </div>
          </div>
        </div>

        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Automatic Crawling</h2>
          
          <div className="space-y-4">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={settings.autoCrawlEnabled}
                onChange={(e) => setSettings({ ...settings, autoCrawlEnabled: e.target.checked })}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm font-medium text-gray-700">
                Enable automatic re-crawling
              </span>
            </label>

            {settings.autoCrawlEnabled && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Re-crawl interval (hours)
                </label>
                <input
                  type="number"
                  min="1"
                  max="168"
                  value={settings.autoCrawlInterval}
                  onChange={(e) => setSettings({ ...settings, autoCrawlInterval: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            )}
          </div>
        </div>

        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex gap-3">
            <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-yellow-800">
                These settings affect all crawl operations. Changes will apply to new crawls only.
              </p>
            </div>
          </div>
        </div>

        <div className="flex justify-end">
          <button
            onClick={handleSave}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
          >
            <Save className="w-4 h-4" />
            Save Settings
          </button>
        </div>

        {saved && (
          <div className="fixed bottom-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg">
            Settings saved successfully!
          </div>
        )}
      </div>
    </div>
  )
}