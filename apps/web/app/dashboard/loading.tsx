import { Loader2 } from 'lucide-react';

export default function DashboardLoading() {
  return (
    <div className="flex h-full w-full items-center justify-center p-12">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-neon-green" />
        <p className="text-sm font-mono text-gray-400 animate-pulse">
          Intercepting data...
        </p>
      </div>
    </div>
  );
}
