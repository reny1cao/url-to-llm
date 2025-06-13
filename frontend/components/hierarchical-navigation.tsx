'use client'

import { useState } from 'react'
import Link from 'next/link'
import { ChevronRight, ChevronDown, FileText, Folder, FolderOpen } from 'lucide-react'
import { cn } from '@/lib/utils'

interface BackendNavigationItem {
  id: string
  page_id: string
  parent_id: string | null
  title: string
  path: string
  url: string
  description?: string
  order_index: number
  level: number
  is_expanded: boolean
  metadata?: any
  children: BackendNavigationItem[]
}

interface HierarchicalNavigationProps {
  items: BackendNavigationItem[]
  currentPath: string
  host: string
  onNavigate?: () => void
  className?: string
}

interface ProcessedNavItem {
  id: string
  title: string
  path: string
  isFolder: boolean
  children: ProcessedNavItem[]
  level: number
  order: number
}

function buildNavigationTree(items: BackendNavigationItem[]): ProcessedNavItem[] {
  // Group items by path segments to create a proper folder structure
  const pathMap = new Map<string, ProcessedNavItem>()
  const rootItems: ProcessedNavItem[] = []

  // Sort items by path depth and then by path
  const sortedItems = [...items].sort((a, b) => {
    const aDepth = (a.path.match(/\//g) || []).length
    const bDepth = (b.path.match(/\//g) || []).length
    if (aDepth !== bDepth) return aDepth - bDepth
    return a.path.localeCompare(b.path)
  })

  for (const item of sortedItems) {
    const pathParts = item.path.split('/').filter(Boolean)
    
    // Create folders for each path segment
    let currentPath = ''
    let currentLevel = 0
    let parentItem: ProcessedNavItem | null = null

    for (let i = 0; i < pathParts.length; i++) {
      const segment = pathParts[i]
      const isLastSegment = i === pathParts.length - 1
      currentPath += '/' + segment
      currentLevel++

      if (!pathMap.has(currentPath)) {
        const newItem: ProcessedNavItem = {
          id: isLastSegment ? item.id : `folder-${currentPath}`,
          title: isLastSegment ? item.title : segment.replace(/[-_]/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
          path: currentPath,
          isFolder: !isLastSegment,
          children: [],
          level: currentLevel,
          order: isLastSegment ? item.order_index : 0
        }

        pathMap.set(currentPath, newItem)

        if (parentItem) {
          parentItem.children.push(newItem)
        } else {
          rootItems.push(newItem)
        }
      }

      parentItem = pathMap.get(currentPath)!
    }
  }

  // Sort children recursively
  function sortChildren(items: ProcessedNavItem[]) {
    items.sort((a, b) => {
      // Folders first, then files
      if (a.isFolder !== b.isFolder) {
        return a.isFolder ? -1 : 1
      }
      // Then by title
      return a.title.localeCompare(b.title)
    })

    items.forEach(item => {
      if (item.children.length > 0) {
        sortChildren(item.children)
      }
    })
  }

  sortChildren(rootItems)
  return rootItems
}

export function HierarchicalNavigation({ 
  items, 
  currentPath, 
  host, 
  onNavigate, 
  className 
}: HierarchicalNavigationProps) {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set())
  const processedItems = buildNavigationTree(items)

  const toggleFolder = (path: string) => {
    setExpandedFolders(prev => {
      const next = new Set(prev)
      if (next.has(path)) {
        next.delete(path)
      } else {
        next.add(path)
      }
      return next
    })
  }

  const renderNavItem = (item: ProcessedNavItem, level = 0) => {
    const isExpanded = expandedFolders.has(item.path)
    const isCurrentPath = currentPath === item.path
    const hasChildren = item.children.length > 0

    return (
      <div key={item.id} className="select-none">
        {item.isFolder ? (
          // Folder
          <button
            onClick={() => toggleFolder(item.path)}
            className={cn(
              'flex items-center gap-2 w-full px-3 py-1.5 text-left rounded-md transition-colors text-sm',
              'hover:bg-gray-100 dark:hover:bg-gray-800',
              'text-gray-700 dark:text-gray-300'
            )}
            style={{ paddingLeft: `${12 + level * 16}px` }}
          >
            {hasChildren ? (
              isExpanded ? (
                <ChevronDown className="w-3 h-3 flex-shrink-0" />
              ) : (
                <ChevronRight className="w-3 h-3 flex-shrink-0" />
              )
            ) : (
              <div className="w-3 h-3 flex-shrink-0" />
            )}
            {isExpanded ? (
              <FolderOpen className="w-4 h-4 flex-shrink-0 text-blue-500" />
            ) : (
              <Folder className="w-4 h-4 flex-shrink-0 text-blue-500" />
            )}
            <span className="truncate font-medium">{item.title}</span>
          </button>
        ) : (
          // File
          <Link
            href={`/docs/${host}${item.path}`}
            onClick={onNavigate}
            className={cn(
              'flex items-center gap-2 px-3 py-1.5 rounded-md transition-colors text-sm',
              'hover:bg-gray-100 dark:hover:bg-gray-800',
              isCurrentPath 
                ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 font-medium border-r-2 border-blue-500' 
                : 'text-gray-600 dark:text-gray-400'
            )}
            style={{ paddingLeft: `${12 + level * 16}px` }}
          >
            <div className="w-3 h-3 flex-shrink-0" />
            <FileText className="w-4 h-4 flex-shrink-0" />
            <span className="truncate">{item.title}</span>
          </Link>
        )}

        {/* Render children if folder is expanded */}
        {item.isFolder && isExpanded && hasChildren && (
          <div className="mt-1">
            {item.children.map(child => renderNavItem(child, level + 1))}
          </div>
        )}
      </div>
    )
  }

  // Auto-expand folders that contain the current path
  useState(() => {
    if (currentPath) {
      const pathParts = currentPath.split('/').filter(Boolean)
      let buildPath = ''
      const foldersToExpand = new Set<string>()
      
      for (let i = 0; i < pathParts.length - 1; i++) {
        buildPath += '/' + pathParts[i]
        foldersToExpand.add(buildPath)
      }
      
      setExpandedFolders(foldersToExpand)
    }
  })

  return (
    <nav className={cn("space-y-1 text-sm", className)}>
      {processedItems.length > 0 ? (
        <>
          <div className="pb-2 mb-2 border-b border-gray-200 dark:border-gray-700">
            <h3 className="font-semibold text-gray-900 dark:text-gray-100 text-xs uppercase tracking-wide">
              Documentation
            </h3>
          </div>
          {processedItems.map(item => renderNavItem(item))}
        </>
      ) : (
        <div className="p-4 text-center text-gray-500 dark:text-gray-400">
          <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No pages found</p>
        </div>
      )}
    </nav>
  )
}