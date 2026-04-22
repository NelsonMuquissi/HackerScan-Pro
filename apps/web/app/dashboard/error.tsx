'use client';

import { useEffect } from 'react';
import { AlertCircle, RefreshCcw } from 'lucide-react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Dashboard Error:', error);
  }, [error]);

  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center rounded-3xl border border-red-500/20 bg-red-500/5 p-12 text-center shadow-2xl">
      <div className="mb-6 rounded-full bg-red-500 p-4 shadow-[0_0_30px_rgba(239,68,68,0.3)]">
        <AlertCircle className="h-8 w-8 text-black" />
      </div>
      
      <h2 className="mb-2 text-2xl font-black text-white uppercase tracking-tighter">System Malfunction Detected</h2>
      <p className="mb-8 font-mono text-sm text-red-200/60 max-w-md">
        An unhandled exception occurred in the dashboard kernel. Error Digest: <span className="text-red-400">{error.digest || 'HS-ERR-UNKNOWN'}</span>
      </p>

      <div className="flex gap-4">
        <button
          onClick={() => reset()}
          className="flex items-center gap-2 rounded-xl bg-red-500 px-6 py-3 font-bold text-black transition-all hover:bg-red-400"
        >
          <RefreshCcw className="h-4 w-4" /> REBOOT COMPONENT
        </button>
        <button
          onClick={() => window.location.reload()}
          className="rounded-xl border border-red-500/30 px-6 py-3 font-bold text-red-500 transition-all hover:bg-red-500/10"
        >
          FULL SYSTEM RESTART
        </button>
      </div>
    </div>
  );
}
