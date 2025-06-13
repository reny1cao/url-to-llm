'use client'

import Link from 'next/link'
import { ChevronRight, Home } from 'lucide-react'
import { cn } from '@/lib/utils'

interface BreadcrumbProps {
  host: string
  path: string
  className?: string
}

export function Breadcrumb({ host, path, className }: BreadcrumbProps) {
  const pathSegments = path.split('/').filter(Boolean)
  
  const breadcrumbItems = [
    { label: host, href: `/docs/${host}`, isHome: true },
    ...pathSegments.map((segment, index) => {
      const href = `/docs/${host}/${pathSegments.slice(0, index + 1).join('/')}`
      const label = segment
        .replace(/[-_]/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase())
        .replace(/\.(html|md|htm)$/i, '')
      
      return {
        label,
        href,
        isHome: false
      }
    })
  ]

  return (
    <nav className={cn("flex items-center space-x-1 text-sm text-gray-500 dark:text-gray-400", className)}>
      {breadcrumbItems.map((item, index) => (
        <div key={item.href} className="flex items-center">
          {index > 0 && <ChevronRight className="w-4 h-4 mx-1 flex-shrink-0" />}
          
          {index === breadcrumbItems.length - 1 ? (
            // Current page - not clickable
            <span className="font-medium text-gray-900 dark:text-gray-100 truncate max-w-32 sm:max-w-48">
              {item.isHome && <Home className="w-4 h-4 inline mr-1" />}
              {item.label}
            </span>
          ) : (
            // Clickable breadcrumb
            <Link
              href={item.href}
              className="hover:text-gray-700 dark:hover:text-gray-200 transition-colors truncate max-w-32 sm:max-w-48 flex items-center"
            >
              {item.isHome && <Home className="w-4 h-4 mr-1 flex-shrink-0" />}
              {item.label}
            </Link>
          )}
        </div>
      ))}
    </nav>
  )
}