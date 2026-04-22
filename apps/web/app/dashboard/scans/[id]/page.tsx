import { use } from 'react';
import { ScanDetailContent } from '@/components/scans/ScanDetailContent';

// Next.js 15: params is a Promise — unwrap it with use() in a Server Component.
export default function ScanDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <ScanDetailContent scanId={id} />
    </div>
  );
}
