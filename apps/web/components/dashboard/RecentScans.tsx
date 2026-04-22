import Link from 'next/link';
import { Shield, ShieldAlert, ShieldCheck, ShieldQuestion, Info } from 'lucide-react';

interface RecentScan {
  id: string;
  target_host?: string;
  status: string;
  total_findings?: number;
  critical_count?: number;
  high_count?: number;
  created_at: string;
}

interface RecentScansProps {
  scans: RecentScan[];
}

const statusColors: Record<string, string> = {
  completed: 'text-neon-green',
  running: 'text-yellow-400',
  queued: 'text-blue-400',
  pending: 'text-gray-400',
  failed: 'text-red-500',
  cancelled: 'text-gray-500',
};

export function RecentScans({ scans }: RecentScansProps) {
  if (!scans || scans.length === 0) {
    return (
      <div className="bg-card-bg border border-card-border rounded-lg p-6">
        <h3 className="text-lg font-mono font-bold text-foreground mb-4">Recent Scans</h3>
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <ShieldQuestion className="w-10 h-10 text-gray-500 mb-3" />
          <p className="text-gray-400 font-mono text-sm">No scans yet.</p>
          <p className="text-gray-500 font-mono text-xs mt-1">Run your first scan to see results here.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card-bg border border-card-border rounded-lg p-6">
      <h3 className="text-lg font-mono font-bold text-foreground mb-4">Recent Scans</h3>
      <div className="space-y-3">
        {scans.map((scan) => {
          const hasCritical = (scan.critical_count ?? 0) > 0;
          const hasHigh = (scan.high_count ?? 0) > 0;

          return (
            <Link
              key={scan.id}
              href={`/dashboard/scans/${scan.id}`}
              className="flex items-center justify-between bg-background border border-card-border rounded-md px-4 py-3 hover:border-neon-green/50 transition-all group/row"
            >
              <div className="flex items-center gap-3">
                {hasCritical ? (
                  <ShieldAlert className="w-5 h-5 text-red-500" />
                ) : hasHigh ? (
                  <Shield className="w-5 h-5 text-orange-400" />
                ) : (
                  <ShieldCheck className="w-5 h-5 text-neon-green" />
                )}
                <div>
                  <p className="font-mono text-sm text-foreground">
                    {scan.target_host ?? 'Unknown target'}
                  </p>
                  <p className="font-mono text-xs text-gray-500">
                    {new Date(scan.created_at).toLocaleDateString('pt-BR', {
                      day: '2-digit',
                      month: 'short',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <span className="font-mono text-xs text-gray-400">
                  {scan.total_findings ?? 0} findings
                </span>
                <span className={`font-mono text-xs uppercase ${statusColors[scan.status] ?? 'text-gray-400'}`}>
                  {scan.status}
                </span>
                <div className="w-6 h-6 rounded bg-neon-green/10 flex items-center justify-center text-neon-green opacity-0 group-hover/row:opacity-100 transition-opacity">
                  <Info className="w-3.5 h-3.5" />
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
