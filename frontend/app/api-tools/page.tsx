'use client'

import { Code, Copy, Terminal, Book } from 'lucide-react'
import { useState } from 'react'

export default function ApiToolsPage() {
  const [copiedSection, setCopiedSection] = useState<string | null>(null)

  const copyToClipboard = (text: string, section: string) => {
    navigator.clipboard.writeText(text)
    setCopiedSection(section)
    setTimeout(() => setCopiedSection(null), 2000)
  }

  const codeExamples = {
    listHosts: `curl -X GET "http://localhost:8000/tools/llm.list_hosts" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"`,
    
    getManifest: `curl -X POST "http://localhost:8000/tools/llm.fetch_manifest" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"host": "example.com"}'`,
    
    fetchPage: `curl -X POST "http://localhost:8000/tools/llm.fetch_page" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"url": "https://example.com/page"}'`,
    
    pythonExample: `import requests

# Configure API client
API_URL = "http://localhost:8000"
headers = {"Authorization": "Bearer YOUR_ACCESS_TOKEN"}

# List all hosts
response = requests.get(f"{API_URL}/tools/llm.list_hosts", headers=headers)
hosts = response.json()

# Fetch manifest for a host
manifest_data = {
    "host": "example.com"
}
response = requests.post(
    f"{API_URL}/tools/llm.fetch_manifest",
    json=manifest_data,
    headers=headers
)
manifest = response.json()`,

    mcpConfig: `{
  "mcpServers": {
    "url-to-llm": {
      "url": "http://localhost:8000",
      "apiKey": "YOUR_API_KEY"
    }
  }
}`
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">API & MCP Tools</h1>
        <p className="text-gray-600">
          Integrate with the URL to LLM API and Model Context Protocol
        </p>
      </div>

      <div className="space-y-6">
        <div className="card">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Terminal className="w-5 h-5" />
            API Endpoints
          </h2>
          
          <div className="space-y-4">
            <div>
              <h3 className="font-medium mb-2">List All Hosts</h3>
              <p className="text-sm text-gray-600 mb-2">
                Get a list of all crawled hosts with their manifests
              </p>
              <div className="relative">
                <pre className="bg-gray-50 p-3 rounded-lg text-sm overflow-x-auto">
                  <code>{codeExamples.listHosts}</code>
                </pre>
                <button
                  onClick={() => copyToClipboard(codeExamples.listHosts, 'listHosts')}
                  className="absolute top-2 right-2 p-1 text-gray-500 hover:text-gray-700"
                >
                  <Copy className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div>
              <h3 className="font-medium mb-2">Fetch Manifest</h3>
              <p className="text-sm text-gray-600 mb-2">
                Get the llm.txt manifest for a specific host
              </p>
              <div className="relative">
                <pre className="bg-gray-50 p-3 rounded-lg text-sm overflow-x-auto">
                  <code>{codeExamples.getManifest}</code>
                </pre>
                <button
                  onClick={() => copyToClipboard(codeExamples.getManifest, 'getManifest')}
                  className="absolute top-2 right-2 p-1 text-gray-500 hover:text-gray-700"
                >
                  <Copy className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div>
              <h3 className="font-medium mb-2">Fetch Page Content</h3>
              <p className="text-sm text-gray-600 mb-2">
                Get the content of a specific page
              </p>
              <div className="relative">
                <pre className="bg-gray-50 p-3 rounded-lg text-sm overflow-x-auto">
                  <code>{codeExamples.fetchPage}</code>
                </pre>
                <button
                  onClick={() => copyToClipboard(codeExamples.fetchPage, 'fetchPage')}
                  className="absolute top-2 right-2 p-1 text-gray-500 hover:text-gray-700"
                >
                  <Copy className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Code className="w-5 h-5" />
            Python Example
          </h2>
          <div className="relative">
            <pre className="bg-gray-50 p-3 rounded-lg text-sm overflow-x-auto">
              <code>{codeExamples.pythonExample}</code>
            </pre>
            <button
              onClick={() => copyToClipboard(codeExamples.pythonExample, 'python')}
              className="absolute top-2 right-2 p-1 text-gray-500 hover:text-gray-700"
            >
              <Copy className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="card">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Book className="w-5 h-5" />
            MCP Configuration
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            Add this to your AI agent&apos;s MCP configuration:
          </p>
          <div className="relative">
            <pre className="bg-gray-50 p-3 rounded-lg text-sm overflow-x-auto">
              <code>{codeExamples.mcpConfig}</code>
            </pre>
            <button
              onClick={() => copyToClipboard(codeExamples.mcpConfig, 'mcp')}
              className="absolute top-2 right-2 p-1 text-gray-500 hover:text-gray-700"
            >
              <Copy className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-blue-800">
            <strong>Authentication:</strong> All API endpoints require a valid OAuth 2.0 access token.
            Use the authorization flow to obtain tokens for your application.
          </p>
        </div>
      </div>

      {copiedSection && (
        <div className="fixed bottom-4 right-4 bg-gray-800 text-white px-4 py-2 rounded-lg shadow-lg">
          Copied to clipboard!
        </div>
      )}
    </div>
  )
}