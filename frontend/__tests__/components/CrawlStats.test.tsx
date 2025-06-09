import { render, screen } from '@testing-library/react'
import { CrawlStats } from '@/components/CrawlStats'

describe('CrawlStats', () => {
  it('renders with empty hosts', () => {
    render(<CrawlStats hosts={[]} />)
    
    expect(screen.getByText('Total Hosts')).toBeInTheDocument()
    expect(screen.getByText('0')).toBeInTheDocument()
    expect(screen.getByText('Total Pages')).toBeInTheDocument()
    expect(screen.getByText('Success Rate')).toBeInTheDocument()
    expect(screen.getByText('0%')).toBeInTheDocument()
  })

  it('renders with host data', () => {
    const mockHosts = [
      {
        host: 'example.com',
        total_pages: 100,
        accessible_pages: 85,
        blocked_pages: 15,
        last_crawled: '2024-01-01T00:00:00Z',
        manifest_hash: 'abc123',
        change_frequency: 'daily',
      },
      {
        host: 'test.org',
        total_pages: 50,
        accessible_pages: 48,
        blocked_pages: 2,
        last_crawled: '2024-01-02T00:00:00Z',
        manifest_hash: 'def456',
        change_frequency: 'weekly',
      },
    ]

    render(<CrawlStats hosts={mockHosts} />)
    
    expect(screen.getByText('2')).toBeInTheDocument() // Total hosts
    expect(screen.getByText('150')).toBeInTheDocument() // Total pages
    expect(screen.getByText('89%')).toBeInTheDocument() // Success rate
    expect(screen.getByText('Active')).toBeInTheDocument() // Last activity
  })
})