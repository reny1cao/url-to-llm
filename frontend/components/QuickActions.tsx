'use client'

import { Plus, RefreshCw, Download } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { api } from '@/lib/api'

export function QuickActions() {
  const [isAddingHost, setIsAddingHost] = useState(false)
  const [newHost, setNewHost] = useState('')

  const handleAddHost = async () => {
    if (!newHost) {
      toast.error('Please enter a host')
      return
    }

    try {
      await api.startCrawl(newHost)
      toast.success(`Started crawling ${newHost}`)
      setNewHost('')
      setIsAddingHost(false)
    } catch (error) {
      toast.error('Failed to start crawl')
    }
  }

  return (
    <div className="flex items-center gap-3">
      {isAddingHost ? (
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="example.com"
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-llm-primary"
            value={newHost}
            onChange={(e) => setNewHost(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleAddHost()}
            autoFocus
          />
          <button
            onClick={handleAddHost}
            className="btn-primary"
          >
            Start Crawl
          </button>
          <button
            onClick={() => {
              setIsAddingHost(false)
              setNewHost('')
            }}
            className="btn-secondary"
          >
            Cancel
          </button>
        </div>
      ) : (
        <>
          <button
            onClick={() => setIsAddingHost(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Add Host
          </button>
          
          <button className="btn-secondary flex items-center gap-2">
            <RefreshCw className="w-4 h-4" />
            Refresh All
          </button>
          
          <button className="btn-secondary flex items-center gap-2">
            <Download className="w-4 h-4" />
            Export
          </button>
        </>
      )}
    </div>
  )
}