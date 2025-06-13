'use client'

import { useState } from 'react'
import { Copy, Check, ChevronDown, ChevronRight } from 'lucide-react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'

export default function ApiDocumentationPage() {
  const [copiedEndpoint, setCopiedEndpoint] = useState<string | null>(null)
  const [expandedSections, setExpandedSections] = useState<string[]>(['quick-start'])

  const copyToClipboard = (text: string, endpoint: string) => {
    navigator.clipboard.writeText(text)
    setCopiedEndpoint(endpoint)
    setTimeout(() => setCopiedEndpoint(null), 2000)
  }

  const toggleSection = (section: string) => {
    setExpandedSections(prev =>
      prev.includes(section)
        ? prev.filter(s => s !== section)
        : [...prev, section]
    )
  }

  const apiEndpoints = [
    {
      id: 'quick-start',
      title: 'Quick Start',
      description: 'Get started with the Documentation API',
      examples: [
        {
          title: 'Get all documentation sites',
          method: 'GET',
          endpoint: '/api/agent/sites',
          description: 'Returns all available documentation sites with freshness information',
          code: `curl -X GET "https://api.url-to-llm.com/api/agent/sites" \\
  -H "Authorization: Bearer YOUR_API_KEY"`,
          response: `[
  {
    "host": "react.dev",
    "total_pages": 542,
    "last_updated": "2024-12-06T10:00:00Z",
    "manifest_url": "/api/docs/react.dev/manifest",
    "search_url": "/api/docs/react.dev/search",
    "is_fresh": true,
    "is_stale": false
  }
]`
        },
        {
          title: 'Search across all documentation',
          method: 'GET',
          endpoint: '/api/agent/search',
          description: 'Search for content across all documentation sites',
          code: `curl -X GET "https://api.url-to-llm.com/api/agent/search?q=useEffect" \\
  -H "Authorization: Bearer YOUR_API_KEY"`,
          response: `[
  {
    "site": "react.dev",
    "url": "https://react.dev/reference/react/useEffect",
    "path": "/reference/react/useEffect",
    "title": "useEffect",
    "snippet": "<mark>useEffect</mark> is a React Hook that lets you synchronize a component with an external system.",
    "relevance_score": 0.98,
    "last_updated": "2024-12-06T10:00:00Z"
  }
]`
        }
      ]
    },
    {
      id: 'manifest',
      title: 'Manifest Operations',
      description: 'Get consolidated information about all documentation',
      examples: [
        {
          title: 'Get consolidated manifest',
          method: 'GET',
          endpoint: '/api/agent/manifest',
          description: 'Returns a consolidated manifest of all documentation sites',
          code: `curl -X GET "https://api.url-to-llm.com/api/agent/manifest?format=consolidated" \\
  -H "Authorization: Bearer YOUR_API_KEY"`,
          response: `{
  "generated_at": "2024-12-06T12:00:00Z",
  "total_sites": 18,
  "total_pages": 2847,
  "sites": {
    "react.dev": {
      "title": "React Documentation",
      "description": "The library for web and native user interfaces",
      "last_updated": "2024-12-06T10:00:00Z",
      "pages": 542,
      "size_bytes": 127000000,
      "manifest_url": "/api/docs/react.dev/manifest",
      "search_endpoint": "/api/docs/react.dev/search",
      "pages_endpoint": "/api/docs/react.dev/pages"
    }
  }
}`
        }
      ]
    },
    {
      id: 'content',
      title: 'Content Retrieval',
      description: 'Get specific documentation content',
      examples: [
        {
          title: 'Get documentation content',
          method: 'GET',
          endpoint: '/api/agent/content/{host}/{path}',
          description: 'Retrieve specific documentation page content',
          code: `curl -X GET "https://api.url-to-llm.com/api/agent/content/react.dev/reference/react/useEffect?format=markdown" \\
  -H "Authorization: Bearer YOUR_API_KEY"`,
          response: `{
  "host": "react.dev",
  "path": "/reference/react/useEffect",
  "title": "useEffect",
  "description": "useEffect is a React Hook that lets you synchronize a component with an external system.",
  "last_updated": "2024-12-06T10:00:00Z",
  "content": {
    "markdown": "# useEffect\\n\\n\`useEffect\` is a React Hook that lets you synchronize..."
  }
}`
        }
      ]
    },
    {
      id: 'stats',
      title: 'Statistics & Monitoring',
      description: 'Get statistics about documentation freshness',
      examples: [
        {
          title: 'Get documentation statistics',
          method: 'GET',
          endpoint: '/api/agent/stats',
          description: 'Returns overall statistics about the documentation system',
          code: `curl -X GET "https://api.url-to-llm.com/api/agent/stats" \\
  -H "Authorization: Bearer YOUR_API_KEY"`,
          response: `{
  "total_sites": 18,
  "total_pages": 2847,
  "total_size_bytes": 1234567890,
  "oldest_update": "2024-12-01T00:00:00Z",
  "newest_update": "2024-12-06T12:00:00Z",
  "freshness": {
    "fresh": 12,
    "recent": 4,
    "stale": 2
  }
}`
        }
      ]
    }
  ]

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Agent API Documentation</h1>
        <p className="text-gray-600">
          REST API endpoints optimized for AI agents to access framework documentation
        </p>
      </div>

      {/* API Key Section */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-8">
        <h2 className="text-lg font-semibold mb-2">Authentication</h2>
        <p className="text-gray-700 mb-4">
          All API requests require authentication using a Bearer token in the Authorization header.
        </p>
        <div className="bg-white rounded p-4 font-mono text-sm">
          Authorization: Bearer YOUR_API_KEY
        </div>
      </div>

      {/* Base URL */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold mb-2">Base URL</h2>
        <div className="bg-gray-100 rounded p-4 font-mono">
          https://api.url-to-llm.com
        </div>
      </div>

      {/* API Endpoints */}
      <div className="space-y-6">
        {apiEndpoints.map((section) => (
          <div key={section.id} className="border border-gray-200 rounded-lg">
            <button
              onClick={() => toggleSection(section.id)}
              className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center gap-3">
                {expandedSections.includes(section.id) ? (
                  <ChevronDown className="w-5 h-5 text-gray-500" />
                ) : (
                  <ChevronRight className="w-5 h-5 text-gray-500" />
                )}
                <div className="text-left">
                  <h3 className="text-lg font-semibold">{section.title}</h3>
                  <p className="text-sm text-gray-600">{section.description}</p>
                </div>
              </div>
            </button>

            {expandedSections.includes(section.id) && (
              <div className="border-t border-gray-200 p-6 space-y-8">
                {section.examples.map((example, idx) => (
                  <div key={idx} className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="text-lg font-medium">{example.title}</h4>
                      <span className={`px-3 py-1 text-sm rounded-full font-medium ${
                        example.method === 'GET' 
                          ? 'bg-green-100 text-green-700' 
                          : 'bg-blue-100 text-blue-700'
                      }`}>
                        {example.method}
                      </span>
                    </div>
                    
                    <div className="bg-gray-100 rounded px-4 py-2 font-mono text-sm flex items-center justify-between">
                      <span>{example.endpoint}</span>
                      <button
                        onClick={() => copyToClipboard(example.endpoint, example.endpoint)}
                        className="ml-2 p-1 hover:bg-gray-200 rounded"
                      >
                        {copiedEndpoint === example.endpoint ? (
                          <Check className="w-4 h-4 text-green-600" />
                        ) : (
                          <Copy className="w-4 h-4 text-gray-500" />
                        )}
                      </button>
                    </div>

                    <p className="text-gray-600">{example.description}</p>

                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <h5 className="text-sm font-medium text-gray-700">Example Request</h5>
                        <button
                          onClick={() => copyToClipboard(example.code, `${example.endpoint}-code`)}
                          className="text-sm text-blue-600 hover:text-blue-700"
                        >
                          {copiedEndpoint === `${example.endpoint}-code` ? 'Copied!' : 'Copy'}
                        </button>
                      </div>
                      <SyntaxHighlighter
                        language="bash"
                        style={oneDark}
                        customStyle={{ borderRadius: '0.5rem', fontSize: '0.875rem' }}
                      >
                        {example.code}
                      </SyntaxHighlighter>
                    </div>

                    <div>
                      <h5 className="text-sm font-medium text-gray-700 mb-2">Example Response</h5>
                      <SyntaxHighlighter
                        language="json"
                        style={oneDark}
                        customStyle={{ borderRadius: '0.5rem', fontSize: '0.875rem' }}
                      >
                        {example.response}
                      </SyntaxHighlighter>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Rate Limits */}
      <div className="mt-8 bg-gray-50 rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-2">Rate Limits</h2>
        <div className="space-y-2 text-gray-700">
          <p>• 1,000 requests per hour per API key</p>
          <p>• 10,000 requests per day per API key</p>
          <p>• Bulk operations count as single requests</p>
        </div>
      </div>
    </div>
  )
}