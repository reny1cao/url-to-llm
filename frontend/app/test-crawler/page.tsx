'use client';

import { useState } from 'react';

// Helper function to render manifest as markdown
function renderMarkdown(manifest: string): React.ReactNode {
  const lines = manifest.split('\n');
  const elements: React.ReactNode[] = [];
  let inCodeBlock = false;
  let codeBlockContent: string[] = [];
  
  lines.forEach((line, index) => {
    // Handle code blocks
    if (line.trim().startsWith('```')) {
      if (!inCodeBlock) {
        inCodeBlock = true;
        codeBlockContent = [];
      } else {
        // End of code block
        elements.push(
          <pre key={`code-${index}`} className="bg-gray-100 dark:bg-gray-800 p-4 rounded-md overflow-x-auto my-2">
            <code className="text-sm">{codeBlockContent.join('\n')}</code>
          </pre>
        );
        inCodeBlock = false;
        codeBlockContent = [];
      }
      return;
    }
    
    if (inCodeBlock) {
      codeBlockContent.push(line);
      return;
    }
    
    // Handle different markdown elements
    if (line.startsWith('# ')) {
      elements.push(<h1 key={index} className="text-3xl font-bold mt-6 mb-4">{line.substring(2)}</h1>);
    } else if (line.startsWith('## ')) {
      elements.push(<h2 key={index} className="text-2xl font-semibold mt-5 mb-3">{line.substring(3)}</h2>);
    } else if (line.startsWith('### ')) {
      elements.push(<h3 key={index} className="text-xl font-semibold mt-4 mb-2">{line.substring(4)}</h3>);
    } else if (line.startsWith('#### ')) {
      elements.push(<h4 key={index} className="text-lg font-medium mt-3 mb-2">{line.substring(5)}</h4>);
    } else if (line.startsWith('- ')) {
      // Handle list items with potential bold text
      const content = line.substring(2);
      const formattedContent = formatInlineElements(content);
      elements.push(
        <li key={index} className="ml-6 mb-1 list-disc">
          {formattedContent}
        </li>
      );
    } else if (line.startsWith('> ')) {
      elements.push(
        <blockquote key={index} className="border-l-4 border-gray-300 pl-4 my-2 italic text-gray-600 dark:text-gray-400">
          {line.substring(2)}
        </blockquote>
      );
    } else if (line.trim() === '---') {
      elements.push(<hr key={index} className="my-6 border-gray-300 dark:border-gray-700" />);
    } else if (line.trim() === '') {
      elements.push(<div key={index} className="h-2" />);
    } else if (line.startsWith('*') && line.endsWith('*')) {
      elements.push(<p key={index} className="italic text-gray-600 dark:text-gray-400 my-2">{line.slice(1, -1)}</p>);
    } else {
      elements.push(<p key={index} className="mb-2">{formatInlineElements(line)}</p>);
    }
  });
  
  return <>{elements}</>;
}

// Helper function to format inline elements (bold, code)
function formatInlineElements(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    } else if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={index} className="bg-gray-200 dark:bg-gray-700 px-1 py-0.5 rounded text-sm">{part.slice(1, -1)}</code>;
    }
    return part;
  });
}

// Helper function to copy text to clipboard
async function copyToClipboard(text: string) {
  try {
    await navigator.clipboard.writeText(text);
    alert('Manifest copied to clipboard!');
  } catch (err) {
    console.error('Failed to copy:', err);
    alert('Failed to copy to clipboard');
  }
}

// Helper function to download manifest
function downloadManifest(host: string, content: string) {
  const blob = new Blob([content], { type: 'text/plain' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${host}-llm.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
}

export default function TestCrawlerPage() {
  const [url, setUrl] = useState('https://example.com');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'markdown' | 'raw'>('markdown');

  const handleCrawl = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch('/api/crawl/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to crawl');
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto py-8 px-4">
      <h1 className="text-3xl font-bold mb-8">Test Crawler</h1>

      <div className="bg-white rounded-lg shadow-md p-6 mb-8">
        <h2 className="text-xl font-semibold mb-4">Crawl a URL</h2>
        <div className="flex gap-4">
          <input
            type="url"
            placeholder="Enter URL to crawl"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleCrawl}
            disabled={loading || !url}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Crawling...' : 'Crawl'}
          </button>
        </div>
      </div>

      {loading && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-8 text-center">
          <div className="inline-flex items-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mr-3"></div>
            <span className="text-lg">Crawling website...</span>
          </div>
          <p className="text-sm text-gray-600 mt-2">This may take a few seconds</p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-500 rounded-lg p-6 mb-8">
          <h2 className="text-xl font-semibold text-red-700 mb-2">Error</h2>
          <pre className="text-sm text-red-600">{error}</pre>
        </div>
      )}

      {result && (
        <>
          <div className="bg-white rounded-lg shadow-md p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4">Crawl Results</h2>
            <div className="space-y-2">
              <p><strong>Host:</strong> {result.host}</p>
              <p><strong>Pages Crawled:</strong> {result.pages_crawled}</p>
              <p><strong>Pages Changed:</strong> {result.pages_changed}</p>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">Generated LLM.txt Manifest</h2>
              <div className="flex gap-2">
                <button
                  onClick={() => setViewMode(viewMode === 'markdown' ? 'raw' : 'markdown')}
                  className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors"
                >
                  {viewMode === 'markdown' ? 'View Raw' : 'View Formatted'}
                </button>
              </div>
            </div>
            
            {viewMode === 'markdown' ? (
              <div className="prose prose-gray max-w-none dark:prose-invert">
                {renderMarkdown(result.manifest)}
              </div>
            ) : (
              <div className="bg-gray-900 text-gray-100 p-6 rounded-lg overflow-x-auto">
                <pre className="text-sm font-mono whitespace-pre-wrap">
                  <code>{result.manifest}</code>
                </pre>
              </div>
            )}
            
            <div className="mt-6 flex gap-2 border-t pt-4">
              <button
                onClick={() => copyToClipboard(result.manifest)}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition-colors"
              >
                Copy Manifest
              </button>
              <button
                onClick={() => downloadManifest(result.host, result.manifest)}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
              >
                Download as llm.txt
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}