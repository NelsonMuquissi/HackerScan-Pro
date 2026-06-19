'use client';

import { useEffect, useState } from 'react';
import { adminGetSystemHealth, adminRunMaintenance } from '@/lib/api';
import { Activity, Database, Server, Cpu, RefreshCw, Trash2, ShieldAlert, Wrench } from 'lucide-react';
import { toast } from 'sonner';
import { HackerModal } from '@/components/ui/HackerModal';
import { useConfirm } from '@/hooks/useConfirm';

export default function AdminSystemManagement() {
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [runningAction, setRunningAction] = useState<string | null>(null);
  const { confirm, state: confirmState, handleConfirm, handleCancel } = useConfirm();

  useEffect(() => {
    loadHealth();
    const interval = setInterval(loadHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  async function loadHealth() {
    try {
      const data = await adminGetSystemHealth();
      setHealth(data);
    } catch {
      toast.error("Failed to load system health");
    } finally {
      setLoading(false);
    }
  }

  async function handleMaintenance(action: string, label: string, description: string, variant: any = 'warning') {
    const ok = await confirm({
      title: label,
      description,
      confirmLabel: 'Execute',
      variant,
    });
    if (!ok) return;

    setRunningAction(action);
    try {
      const result = await adminRunMaintenance(action);
      toast.success(result?.data?.message || result?.message || `${label} completed.`);
      loadHealth();
    } catch (error: any) {
      toast.error(error?.message || `Action "${label}" failed`);
    } finally {
      setRunningAction(null);
    }
  }

  const statusColor = (s?: string) => {
    switch (s?.toUpperCase()) {
      case 'UP': return 'text-emerald-500';
      case 'DOWN': return 'text-red-500';
      default: return 'text-amber-400';
    }
  };

  const overallOk = health?.status === 'HEALTHY';

  if (loading) return <div className="text-neon-green animate-pulse font-mono">Loading system telemetry...</div>;

  return (
    <>
      <HackerModal
        open={confirmState.open}
        onClose={handleCancel}
        title={confirmState.title}
        variant={confirmState.variant === 'danger' ? 'danger' : confirmState.variant === 'warning' ? 'warning' : 'primary'}
        footer={
          <div className="flex gap-4 w-full">
            <button 
              onClick={handleCancel}
              className="flex-1 px-6 py-4 bg-white/5 border border-white/10 rounded-xl text-gray-400 hover:text-white transition-all font-mono text-xs uppercase tracking-widest"
            >
              Abort
            </button>
            <button 
              onClick={handleConfirm}
              className={`flex-[2] px-8 py-4 rounded-xl font-mono font-black text-xs uppercase tracking-widest transition-all flex items-center justify-center gap-2 ${
                confirmState.variant === 'danger' 
                  ? 'bg-red-500 text-black hover:bg-red-400 shadow-[0_0_20px_rgba(239,68,68,0.3)]' 
                  : confirmState.variant === 'warning'
                  ? 'bg-amber-500 text-black hover:bg-amber-400 shadow-[0_0_20px_rgba(245,158,11,0.3)]'
                  : 'bg-blue-500 text-black hover:bg-blue-400 shadow-[0_0_20px_rgba(59,130,246,0.3)]'
              }`}
            >
              Confirm Execution
            </button>
          </div>
        }
      >
        <div className="space-y-6">
          <div className={`p-6 rounded-2xl border ${
            confirmState.variant === 'danger' ? 'bg-red-500/5 border-red-500/10' : 
            confirmState.variant === 'warning' ? 'bg-amber-500/5 border-amber-500/10' :
            'bg-blue-500/5 border-blue-500/10'
          }`}>
            <p className="text-gray-400 font-mono text-sm leading-relaxed uppercase italic">
              {confirmState.description}
            </p>
          </div>
          <div className="flex items-center gap-4 p-4 bg-black/40 border border-white/5 rounded-xl">
            <ShieldAlert className={`w-5 h-5 ${
              confirmState.variant === 'danger' ? 'text-red-500' : 
              confirmState.variant === 'warning' ? 'text-amber-500' : 'text-blue-500'
            }`} />
            <p className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">
              Core system operation. Impact on cluster performance expected.
            </p>
          </div>
        </div>
      </HackerModal>

      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-mono font-bold text-foreground">System Health &amp; Maintenance</h1>
          <div className={`text-xs font-mono px-3 py-1 rounded border flex items-center gap-2 ${
            overallOk
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-500'
              : 'bg-red-500/10 border-red-500/30 text-red-500'
          }`}>
            <span className={`w-2 h-2 rounded-full ${overallOk ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`}></span>
            {health?.status || 'UNKNOWN'}
          </div>
        </div>

        {/* Status Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[
            { label: 'Database Context', val: health?.database, sub: 'PostgreSQL PRIMARY', icon: Database, color: 'text-blue-400', bg: 'bg-blue-500/5' },
            { label: 'Telemtry Stream', val: health?.redis, sub: 'Task queue & cache', icon: Server, color: 'text-purple-400', bg: 'bg-purple-500/5' },
            { label: 'Computation Load', val: health?.celery, sub: `${health?.workers ?? 0} active workers`, icon: Cpu, color: 'text-neon-green', bg: 'bg-neon-green/5' },
            { label: 'System Uptime', val: health?.environment?.toUpperCase(), sub: health?.server_time ? new Date(health.server_time).toLocaleTimeString() : 'N/A', icon: Activity, color: 'text-amber-400', bg: 'bg-amber-500/5', skipStatus: true },
          ].map(({ label, val, sub, icon: Icon, color, bg, skipStatus }) => (
            <div key={label} className="bg-[#0d0d0e] border border-white/5 rounded-[2rem] p-8 group hover:border-white/10 transition-all relative overflow-hidden">
               <div className={`absolute -top-10 -right-10 w-24 h-24 blur-3xl rounded-full opacity-10 ${bg}`} />
               <div className="flex items-center justify-between mb-4 relative z-10">
                 <h3 className="text-[10px] font-mono text-gray-500 uppercase tracking-[0.2em] font-black">{label}</h3>
                 <div className={`p-2 rounded-lg ${bg} ${color}`}>
                   <Icon className="w-4 h-4" />
                 </div>
               </div>
               <div className={`text-3xl font-mono font-black relative z-10 ${skipStatus ? 'text-white' : statusColor(val)}`}>
                 {val || 'OFFLINE'}
               </div>
               <p className="text-[10px] text-gray-600 font-mono mt-2 uppercase tracking-tighter relative z-10">{sub}</p>
            </div>
          ))}
        </div>

        {/* Maintenance Actions */}
        <div className="bg-[#0d0d0e]/40 border border-white/[0.03] rounded-[3rem] p-10 space-y-10 relative overflow-hidden">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 border-b border-white/5 pb-8">
            <div className="space-y-2">
              <h2 className="text-2xl font-mono font-black flex items-center gap-4 text-white uppercase italic tracking-tighter">
                <Wrench className="w-8 h-8 text-red-500" /> Maintenance <span className="text-red-500">Protocols</span>
              </h2>
              <p className="text-gray-500 text-xs font-mono uppercase tracking-widest opacity-60">High-level administrative overrides for core system infrastructure.</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {[
              {
                action: 'clear_cache', label: 'Clear Cache Buffer',
                desc: 'Flushes primary Redis allocation keys.',
                btnLabel: 'Execute Flush', icon: Trash2, color: 'text-emerald-400',
                modalDesc: 'This will initiate a complete flush of the Redis cache buffer. Primary data remains intact, but transient performance degradation is expected during the rebuild phase.',
                variant: 'warning' as const,
              },
              {
                action: 'cleanup_scans', label: 'Purge Stale Context',
                desc: 'Terminates scans exceeding 2h threshold.',
                btnLabel: 'Purge Buffer', icon: Activity, color: 'text-amber-400',
                modalDesc: 'Scans with a runtime exceeding 120 minutes will be forcibly terminated. Associated worker contexts will be reallocated. This is used to clear hung scan threads.',
                variant: 'warning' as const,
              },
              {
                action: 'repair_findings', label: 'Index Integrity Repair',
                desc: 'Recalculates global finding fingerprints.',
                btnLabel: 'Start Repair', icon: Wrench, color: 'text-blue-400',
                modalDesc: 'Initiates a global re-indexing of all security findings. Fingerprint collision detection will be reset. High database load expected.',
                variant: 'info' as const,
              },
              {
                action: 'sync_plugins', label: 'Registry Synchronization',
                desc: 'Harmonizes codebase strategies with DB.',
                btnLabel: 'Sync Registry', icon: Server, color: 'text-purple-400',
                modalDesc: 'Synchronizes the local engine configuration with the persistent plugin registry. New detection vectors will be added to the available pool.',
                variant: 'info' as const,
              },
              {
                action: 'reset_quotas', label: 'Global Quota Reset',
                desc: 'Wipes usage counters across ALL units.',
                btnLabel: 'Execute Reset', icon: ShieldAlert, color: 'text-red-500',
                modalDesc: '⚠️ CRITICAL: This will zero out the scan usage counters for every workspace on the platform. This bypasses standard billing cycles and is IRREVERSIBLE.',
                variant: 'danger' as const,
              },
            ].map(({ action, label, desc, btnLabel, icon: Icon, color, modalDesc, variant }) => (
              <div
                key={action}
                className={`group border rounded-[2rem] p-8 transition-all hover:bg-white/[0.02] ${
                  variant === 'danger' ? 'bg-red-500/5 border-red-500/10 hover:border-red-500/30' : 'bg-[#0d0d0e] border-white/5 hover:border-white/20'
                }`}
              >
                <div className="mb-6">
                  <h3 className={`font-mono font-black text-sm uppercase tracking-widest ${variant === 'danger' ? 'text-red-400' : 'text-white'}`}>{label}</h3>
                  <p className="text-[10px] text-gray-500 font-mono mt-2 uppercase tracking-tighter leading-relaxed">{desc}</p>
                </div>
                <button
                  onClick={() => handleMaintenance(action, label, modalDesc, variant)}
                  disabled={runningAction !== null}
                  className={`w-full py-4 border rounded-xl font-mono font-black text-[10px] uppercase tracking-widest flex items-center justify-center gap-3 disabled:opacity-50 transition-all shadow-lg
                    ${variant === 'danger'
                      ? 'bg-red-500/10 border-red-500/20 text-red-500 hover:bg-red-500 hover:text-black'
                      : 'bg-white/[0.02] border-white/5 hover:border-white/20 text-gray-400 hover:text-white'
                    }`}
                >
                  {runningAction === action ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Icon className="w-4 h-4" />}
                  {btnLabel}
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
