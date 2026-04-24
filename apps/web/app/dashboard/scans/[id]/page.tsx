import { ScanDetailContent } from '@/components/scans/ScanDetailContent';

// Next.js 15: params is a Promise — await it in an async Server Component.
export default async function ScanDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  
  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <ScanDetailContent scanId={id} />
    </div>
  );
}
