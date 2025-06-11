'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { JobProgress } from '@/components/job-progress';
import { ArrowLeft, Ban } from 'lucide-react';

interface JobDetailsClientProps {
  jobId: string;
}

export function JobDetailsClient({ jobId }: JobDetailsClientProps) {
  const router = useRouter();
  const [token, setToken] = useState<string>('');
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    // Get token from localStorage or auth context
    const authToken = localStorage.getItem('token') || 'demo-token';
    setToken(authToken);
  }, []);

  const handleCancel = async () => {
    if (!confirm('Are you sure you want to cancel this job?')) {
      return;
    }

    setCancelling(true);
    try {
      const response = await fetch(`/api/crawl/jobs/${jobId}/cancel`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to cancel job');
      }

      // Refresh the page to show updated status
      window.location.reload();
    } catch (error) {
      console.error('Failed to cancel job:', error);
      alert('Failed to cancel job');
    } finally {
      setCancelling(false);
    }
  };

  if (!token) {
    return (
      <div className="container mx-auto py-8 px-4">
        <div className="bg-white rounded-lg shadow-md p-6">
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-6">
        <button
          onClick={() => router.push('/jobs')}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Jobs
        </button>
      </div>

      <div className="flex justify-between items-start mb-6">
        <h1 className="text-3xl font-bold">Job Details</h1>
        
        <button
          onClick={handleCancel}
          disabled={cancelling}
          className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Ban className="w-4 h-4" />
          {cancelling ? 'Cancelling...' : 'Cancel Job'}
        </button>
      </div>

      <JobProgress jobId={jobId} token={token} />
    </div>
  );
}