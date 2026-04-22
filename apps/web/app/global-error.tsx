'use client';

import './globals.css';
import { ShieldAlert, RefreshCcw } from 'lucide-react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html>
      <body className="bg-black text-white antialiased">
        <div className="flex h-screen w-screen flex-col items-center justify-center p-6 text-center">
          <div className="mb-8 rounded-full bg-red-500/20 p-8 border border-red-500/50">
            <ShieldAlert className="h-16 w-16 text-red-500" />
          </div>
          <h1 className="mb-4 text-4xl font-black uppercase tracking-tighter">Critical System Failure</h1>
          <p className="mb-12 font-mono text-gray-500 max-w-xl text-lg">
            A kernel-level exception occurred that crashed the entire application runtime. 
            Security protocols are attempting to restore functionality.
          </p>
          <button
            onClick={() => reset()}
            className="flex items-center gap-3 rounded-2xl bg-white px-10 py-5 text-xl font-black text-black transition-all hover:bg-gray-200"
          >
            <RefreshCcw className="h-6 w-6" /> FORCE KERNEL RECOVERY
          </button>
        </div>
      </body>
    </html>
  );
}
