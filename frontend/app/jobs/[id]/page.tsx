import { JobDetailsClient } from './job-details-client';

interface PageProps {
  params: Promise<{
    id: string;
  }>;
}

export default async function JobDetailsPage({ params }: PageProps) {
  const { id } = await params;
  
  return <JobDetailsClient jobId={id} />;
}