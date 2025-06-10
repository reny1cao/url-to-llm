'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { 
  Home, 
  Globe, 
  FileText, 
  Settings, 
  BarChart3,
  Zap,
  TestTube
} from 'lucide-react'
import { cn } from '@/lib/utils'

const navigation = [
  { name: 'Dashboard', href: '/', icon: Home },
  { name: 'Hosts', href: '/hosts', icon: Globe },
  { name: 'Manifests', href: '/manifests', icon: FileText },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'API Tools', href: '/api-tools', icon: Zap },
  { name: 'Test Crawler', href: '/test-crawler', icon: TestTube },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <div className="w-64 bg-gray-900 text-white">
      <div className="p-6">
        <h2 className="text-2xl font-bold">URL → LLM</h2>
        <p className="text-sm text-gray-400 mt-1">Manifest Generator</p>
      </div>
      
      <nav className="px-4 pb-6">
        <ul className="space-y-2">
          {navigation.map((item) => {
            const isActive = pathname === item.href
            return (
              <li key={item.name}>
                <Link
                  href={item.href}
                  className={cn(
                    'flex items-center gap-3 px-4 py-2 rounded-lg transition-colors',
                    isActive
                      ? 'bg-llm-primary text-white'
                      : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                  )}
                >
                  <item.icon className="w-5 h-5" />
                  {item.name}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>
      
      <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-800">
        <div className="text-sm text-gray-400">
          <p>System Status: <span className="text-green-400">Operational</span></p>
          <p className="mt-1">v0.1.0</p>
        </div>
      </div>
    </div>
  )
}