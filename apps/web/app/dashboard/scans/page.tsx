'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Shield, ShieldAlert, ShieldCheck, Loader2, ExternalLink } from 'lucide-react';
import { listScans } from '@/lib/api';

interface ScanRow {
  id: string;
  target?: { host: string; name?: string };
  target_host?: string;
  status: string;
  total_findings?: number;
  critical_count?: number;
  high_count?: number;
  medium_count?: number;
  low_count?: number;
  created_at: string;
  completed_at?: string;
}

const statusBadge: Record<string, { bg: string; text: string }> = {
  completed:  { bg: 'bg-green-900/30 border-green-700',  text: 'text-neon-green' },
  running:    { bg: 'bg-yellow-900/30 border-yellow-700', text: 'text-yellow-400' },
  queued:     { bg: 'bg-blue-900/30 border-blue-700',     text: 'text-blue-400' },
  pending:    { bg: 'bg-gray-800/30 border-gray-600',     text: 'text-gray-400' },
  failed:     { bg: 'bg-red-900/30 border-red-700',       text: 'text-red-400' },
  cancelled:  { bg: 'bg-gray-800/30 border-gray-600',     text: 'text-gray-500' },
};

export default function ScansPage() {
  const router = useRouter();
  const [scans, setScans] = useState<ScanRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    listScans()
      .then((data) => {
        // Handle both raw arrays and paginated responses { results: [], count: ... }
        const list = Array.isArray(data) ? data : (data as any)?.results ?? [];
        setScans(list);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-mono font-bold text-foreground">Scans</h1>

      {loading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 text-neon-green animate-spin" />
          <span className="ml-3 font-mono text-gray-400">Loading scans…</span>
        </div>
      )}

      {error && (
        <div className="bg-red-900/20 border border-red-700 rounded-lg p-4 font-mono text-red-400 text-sm">
          Failed to load scans. Check that the API is running.
        </div>
      )}

      {!loading && !error && scans.length === 0 && (
        <div className="bg-card-bg border border-card-border rounded-lg p-12 text-center">
          <Shield className="w-12 h-12 text-gray-500 mx-auto mb-4" />
          <p className="text-gray-400 font-mono">No scans found.</p>
          <p className="text-gray-500 font-mono text-sm mt-1">
            Go to the Dashboard to launch your first scan.
          </p>
        </div>
      )}

      {!loading && !error && scans.length > 0 && (
        <div className="bg-card-bg border border-card-border rounded-lg overflow-hidden">
          <table className="w-full text-left font-mono text-sm">
            <thead>
              <tr className="border-b border-card-border bg-background">
                <th className="px-4 py-3 text-gray-400 font-medium">Target</th>
                <th className="px-4 py-3 text-gray-400 font-medium">Status</th>
                <th className="px-4 py-3 text-gray-400 font-medium text-center">Findings</th>
                <th className="px-4 py-3 text-gray-400 font-medium text-center">Critical</th>
                <th className="px-4 py-3 text-gray-400 font-medium">Date</th>
                <th className="px-4 py-3 text-gray-400 font-medium text-center">Details</th>
              </tr>
            </thead>
            <tbody>
              {scans.map((scan) => {
                const badge = statusBadge[scan.status] ?? statusBadge.pending;
                return (
                  <tr
                    key={scan.id}
                    className="border-b border-card-border last:border-0 hover:bg-neon-green-dim/30 transition-colors"
                  >
                    <td className="px-4 py-3 text-foreground">
                      {scan.target_host ?? 'Unknown'}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-block px-2 py-0.5 rounded border text-xs uppercase ${badge.bg} ${badge.text}`}>
                        {scan.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center text-gray-300">
                      {scan.total_findings ?? 0}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={(scan.critical_count ?? 0) > 0 ? 'text-red-400 font-bold' : 'text-gray-500'}>
                        {scan.critical_count ?? 0}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs">
                      {new Date(scan.created_at).toLocaleDateString('pt-BR', {
                        day: '2-digit',
                        month: 'short',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        className="text-neon-green hover:underline text-xs inline-flex items-center gap-1"
                        onClick={() => router.push(`/dashboard/scans/${scan.id}`)}
                      >
                        View <ExternalLink className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
