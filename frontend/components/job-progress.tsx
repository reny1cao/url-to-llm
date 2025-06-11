"use client";

import { useState, useEffect } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { AlertCircle, CheckCircle, Clock, Loader2, XCircle } from 'lucide-react';

interface JobProgress {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  pages_crawled: number;
  pages_discovered: number;
  pages_failed: number;
  bytes_downloaded: number;
  current_url?: string;
  progress_percentage: number;
}

interface Job {
  id: string;
  host: string;
  status: string;
  max_pages: number;
  pages_crawled: number;
  pages_discovered: number;
  pages_failed: number;
  bytes_downloaded: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
  manifest_url?: string;
}

interface JobProgressProps {
  jobId: string;
  token: string;
}

export function JobProgress({ jobId, token }: JobProgressProps) {
  const [job, setJob] = useState<Job | null>(null);
  const [progress, setProgress] = useState<JobProgress | null>(null);
  const [progressHistory, setProgressHistory] = useState<JobProgress[]>([]);

  const { isConnected } = useWebSocket({
    url: `${process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'}/ws/jobs/${jobId}`,
    token,
    onMessage: (message) => {
      switch (message.type) {
        case 'job_status':
          setJob(message.job);
          break;
        case 'progress_update':
          setProgress(message.progress);
          setProgressHistory((prev) => [...prev, message.progress]);
          break;
        case 'progress_history':
          setProgressHistory(message.progress);
          break;
        case 'job_completed':
          setJob(message.job);
          break;
      }
    },
  });

  const getStatusIcon = () => {
    switch (job?.status) {
      case 'pending':
        return <Clock className="w-5 h-5 text-yellow-500" />;
      case 'running':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'cancelled':
        return <AlertCircle className="w-5 h-5 text-gray-500" />;
      default:
        return null;
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDuration = (start: string, end?: string) => {
    const startTime = new Date(start).getTime();
    const endTime = end ? new Date(end).getTime() : Date.now();
    const duration = Math.floor((endTime - startTime) / 1000);
    
    const hours = Math.floor(duration / 3600);
    const minutes = Math.floor((duration % 3600) / 60);
    const seconds = duration % 60;
    
    if (hours > 0) {
      return `${hours}h ${minutes}m ${seconds}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds}s`;
    } else {
      return `${seconds}s`;
    }
  };

  if (!job) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
          <span className="ml-2 text-gray-600">Loading job details...</span>
        </div>
      </div>
    );
  }

  const currentProgress = progress || {
    pages_crawled: job.pages_crawled,
    pages_discovered: job.pages_discovered,
    pages_failed: job.pages_failed,
    bytes_downloaded: job.bytes_downloaded,
    progress_percentage: job.max_pages > 0 ? (job.pages_crawled / job.max_pages) * 100 : 0,
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center">
            {getStatusIcon()}
            <h2 className="text-xl font-semibold ml-2">{job.host}</h2>
          </div>
          <div className="flex items-center gap-2">
            {!isConnected && job.status === 'running' && (
              <span className="text-sm text-orange-600 bg-orange-100 px-2 py-1 rounded">
                Reconnecting...
              </span>
            )}
            <span className={`text-sm px-3 py-1 rounded-full font-medium ${
              job.status === 'completed' ? 'bg-green-100 text-green-800' :
              job.status === 'failed' ? 'bg-red-100 text-red-800' :
              job.status === 'running' ? 'bg-blue-100 text-blue-800' :
              job.status === 'cancelled' ? 'bg-gray-100 text-gray-800' :
              'bg-yellow-100 text-yellow-800'
            }`}>
              {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
            </span>
          </div>
        </div>

        {job.error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-4">
            <p className="text-sm text-red-800">{job.error}</p>
          </div>
        )}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <div>
            <p className="text-sm text-gray-600">Pages Crawled</p>
            <p className="text-2xl font-semibold">
              {currentProgress.pages_crawled} / {job.max_pages}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Pages Discovered</p>
            <p className="text-2xl font-semibold">{currentProgress.pages_discovered}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Failed Pages</p>
            <p className="text-2xl font-semibold text-red-600">
              {currentProgress.pages_failed}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Data Downloaded</p>
            <p className="text-2xl font-semibold">
              {formatBytes(currentProgress.bytes_downloaded)}
            </p>
          </div>
        </div>

        {job.status === 'running' && (
          <>
            <div className="mb-4">
              <div className="flex justify-between text-sm text-gray-600 mb-1">
                <span>Progress</span>
                <span>{currentProgress.progress_percentage.toFixed(1)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${currentProgress.progress_percentage}%` }}
                />
              </div>
            </div>

            {progress?.current_url && (
              <div className="bg-gray-50 rounded-md p-3">
                <p className="text-sm text-gray-600">Currently crawling:</p>
                <p className="text-sm font-mono text-gray-800 truncate">
                  {progress.current_url}
                </p>
              </div>
            )}
          </>
        )}

        <div className="flex flex-wrap gap-4 text-sm text-gray-600 mt-4">
          <div>
            <span className="font-medium">Created:</span>{' '}
            {new Date(job.created_at).toLocaleString()}
          </div>
          {job.started_at && (
            <div>
              <span className="font-medium">Duration:</span>{' '}
              {formatDuration(job.started_at, job.completed_at)}
            </div>
          )}
        </div>

        {job.manifest_url && (
          <div className="mt-4 pt-4 border-t">
            <a
              href={job.manifest_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
            >
              View Manifest
            </a>
          </div>
        )}
      </div>

      {progressHistory.length > 0 && (
        <div className="border-t pt-4">
          <h3 className="text-lg font-medium mb-3">Progress History</h3>
          <div className="max-h-40 overflow-y-auto">
            {progressHistory.slice(-10).reverse().map((p, index) => (
              <div key={index} className="text-sm py-1 border-b last:border-0">
                <span className="text-gray-600">
                  {p.pages_crawled} pages • {formatBytes(p.bytes_downloaded)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}