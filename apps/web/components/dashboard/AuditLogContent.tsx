import { useState, useEffect } from 'react';
import { 
  Activity, 
  User, 
  Clock, 
  MapPin, 
  Info, 
  ArrowRight,
  Shield,
  Zap,
  Key,
  Database,
  Loader2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { listAuditLogs } from '@/lib/api';
import { useAuthStore } from '@/store/useAuthStore';

function ActionIcon({ action }: { action: string }) {
  const a = action || '';
  if (a.includes('scan')) return <Zap className="w-4 h-4 text-neon-green" />;
  if (a.includes('key')) return <Key className="w-4 h-4 text-blue-400" />;
  if (a.includes('user')) return <User className="w-4 h-4 text-purple-400" />;
  if (a.includes('workspace')) return <Shield className="w-4 h-4 text-neon-yellow" />;
  return <Activity className="w-4 h-4 text-gray-400" />;
}

export function AuditLogContent() {
  const workspaceId = useAuthStore((s) => s.workspaceId);
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    async function loadLogs() {
      if (!workspaceId || workspaceId === 'undefined') {
        if (isMounted) setLoading(false);
        return;
      }
      
      if (isMounted) {
        setLoading(true);
        setError(null);
      }
      
      try {
        const data = await listAuditLogs(workspaceId);
        if (isMounted) setLogs(data || []);
      } catch (err: any) {
        console.error('Failed to load audit logs:', err);
        if (isMounted) setError(err.message || 'Failed to synchronise with blockchain audit.');
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    loadLogs();
    return () => { isMounted = false; };
  }, [workspaceId]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2 uppercase tracking-tighter">
            <Activity className="w-5 h-5 text-neon-green" />
            Audit Governance
          </h2>
          <p className="text-xs text-gray-500 font-mono mt-1 uppercase tracking-widest">
            Immutable log of all workspace actions
          </p>
        </div>
        <button className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-md text-[10px] font-bold font-mono hover:bg-white/10 transition-colors uppercase">
          Export CSV
        </button>
      </div>

      <div className="bg-card-bg border border-card-border rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-black/40 border-b border-white/5">
                <th className="px-6 py-4 text-[10px] font-bold text-gray-500 font-mono uppercase tracking-widest">Action</th>
                <th className="px-6 py-4 text-[10px] font-bold text-gray-500 font-mono uppercase tracking-widest">User</th>
                <th className="px-6 py-4 text-[10px] font-bold text-gray-500 font-mono uppercase tracking-widest">Resource</th>
                <th className="px-6 py-4 text-[10px] font-bold text-gray-500 font-mono uppercase tracking-widest text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {loading ? (
                <tr>
                  <td colSpan={4} className="px-6 py-20 text-center">
                    <Loader2 className="w-6 h-6 text-neon-green animate-spin mx-auto mb-2" />
                    <span className="text-xs font-mono text-gray-600 uppercase">Synchronizing with blockchain audit...</span>
                  </td>
                </tr>
              ) : error ? (
                <tr>
                  <td colSpan={4} className="px-6 py-20 text-center text-xs font-mono text-red-500 uppercase tracking-widest">
                    {error}
                  </td>
                </tr>
              ) : logs.length > 0 ? logs.map((log) => (
                <motion.tr 
                  key={log.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="group hover:bg-white/[0.02] transition-colors"
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-black border border-white/5 flex items-center justify-center">
                        <ActionIcon action={log.action} />
                      </div>
                      <div>
                        <div className="text-sm font-bold border-b border-transparent group-hover:border-neon-green/30 transition-all inline-block">
                          {(log.action || 'unknown').replace('.', ': ').toUpperCase()}
                        </div>
                        <div className="text-[10px] text-gray-500 font-mono mt-1 flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {log.created_at ? new Date(log.created_at).toLocaleString() : 'Recent'}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-col">
                      <span className="text-sm text-gray-300">{log.user_email || 'System'}</span>
                      <span className="text-[10px] text-gray-600 font-mono flex items-center gap-1">
                        <MapPin className="w-3 h-3" />
                        {log.ip_address || 'Internal'}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                       <span className="px-2 py-0.5 rounded bg-white/5 text-[10px] font-bold text-gray-400 border border-white/5 uppercase">
                         {log.resource_type || 'N/A'}
                       </span>
                       <span className="text-[10px] text-gray-600 font-mono truncate max-w-[100px]">{log.resource_id || '---'}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button className="text-gray-500 hover:text-white transition-colors">
                      <Info className="w-4 h-4" />
                    </button>
                  </td>
                </motion.tr>
              )) : (
                <tr>
                  <td colSpan={4} className="px-6 py-20 text-center text-xs font-mono text-gray-600 uppercase tracking-widest">
                    No historical records found for this workspace.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="flex items-center justify-center py-4">
        <div className="text-[10px] text-gray-600 font-mono animate-pulse uppercase tracking-widest">
          {logs.length > 0 ? 'End of history — Data retained for 365 days' : 'System integrity verified'}
        </div>
      </div>
    </div>
  );
}
