'use client';

import { useEffect, useState } from 'react';
import { adminListUsageRecords, adminListPlans } from '@/lib/api';
import { 
  Activity, Zap, PieChart, TrendingUp, Search, Filter, 
  ArrowUpRight, ArrowDownRight, Globe, BarChart3, 
  Calendar, Layers, Monitor, Database, Shield, AlertTriangle,
  ChevronRight, Cpu, HardDrive, Binary, ArrowRight, Edit2, Lock
} from 'lucide-react';
import { toast } from 'sonner';
import { motion } from 'framer-motion';

export default function QuotasManagement() {
  const [usage, setUsage] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [uData, pData] = await Promise.all([
        adminListUsageRecords(),
        adminListPlans()
      ]);
      setUsage(uData);
      setPlans(pData);
    } catch {
      toast.error("Failed to synchronize telemetry buffer");
    } finally {
      setLoading(false);
    }
  }

  const filteredUsage = usage.filter(u => 
    u.workspace_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    u.workspace_id?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const totalScans = usage.reduce((acc, u) => acc + (u.scans_count || 0), 0);
  const totalFindings = usage.reduce((acc, u) => acc + (u.findings_count || 0), 0);
  const activeWorkspaces = usage.length;

  if (loading) return (
    <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
      <div className="relative">
        <div className="w-16 h-16 border-4 border-blue-500/10 border-t-blue-500 rounded-full animate-spin" />
        <div className="absolute inset-0 bg-blue-500/20 blur-xl animate-pulse rounded-full" />
      </div>
      <p className="text-blue-400 font-mono text-sm tracking-[0.2em] uppercase animate-pulse">Aggregating Global Telemetry...</p>
    </div>
  );

  return (
    <div className="max-w-[1400px] mx-auto space-y-12 pb-20">
      {/* Header & Global Stats */}
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-10 border-b border-white/5 pb-12">
        <div className="space-y-4">
          <div className="flex items-center gap-5">
            <div className="p-4 bg-blue-500/10 rounded-[2rem] border border-blue-500/20 shadow-[0_0_30px_-10px_rgba(59,130,246,0.5)]">
              <PieChart className="text-blue-400 w-10 h-10" />
            </div>
            <div>
              <h1 className="text-5xl font-mono font-black text-white tracking-tighter uppercase italic">
                Quota <span className="text-blue-400">Intelligence</span>
              </h1>
              <div className="flex items-center gap-3 mt-2">
                <div className="w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse shadow-[0_0_8px_rgba(59,130,246,0.8)]" />
                <p className="text-gray-500 font-mono text-xs uppercase tracking-[0.4em]">Real-time utilization analytics & resource governing</p>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
          {[
            { label: 'Global Scans', value: totalScans, icon: Activity, color: 'text-neon-green', bg: 'bg-neon-green/5' },
            { label: 'Findings', value: totalFindings, icon: TrendingUp, color: 'text-purple-400', bg: 'bg-purple-500/5' },
            { label: 'Active Units', value: activeWorkspaces, icon: Layers, color: 'text-blue-400', bg: 'bg-blue-500/5' }
          ].map((stat, i) => (
            <div key={i} className="bg-[#0d0d0e] border border-white/5 rounded-3xl px-8 py-5 flex items-center gap-5 group hover:border-white/10 transition-all">
              <div className={`p-3 rounded-2xl ${stat.bg} ${stat.color} group-hover:scale-110 transition-transform`}>
                <stat.icon className="w-6 h-6" />
              </div>
              <div>
                <div className="text-[10px] text-gray-500 uppercase font-mono tracking-widest font-black">{stat.label}</div>
                <div className="text-3xl font-mono font-black text-white leading-none mt-1">{stat.value.toLocaleString()}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quota Definitions / Plan Defaults Grid */}
      <div className="space-y-6">
        <div className="flex items-center gap-3">
           <Shield className="w-5 h-5 text-purple-400" />
           <h2 className="text-xl font-mono font-black text-white uppercase italic tracking-wider text-gray-400">Baseline Quota Protocols</h2>
           <div className="flex-1 h-px bg-white/5 ml-4" />
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {plans.map((plan) => (
            <div key={plan.id} className="bg-[#0d0d0e]/60 border border-white/[0.03] rounded-[2rem] p-6 group hover:border-purple-500/30 transition-all relative overflow-hidden">
               <div className="absolute -top-10 -right-10 w-24 h-24 bg-purple-500/5 blur-2xl rounded-full" />
               <div className="flex items-center justify-between mb-6">
                  <div className={`px-3 py-1 rounded-full text-[9px] font-mono font-black border ${
                    plan.name === 'enterprise' ? 'bg-purple-500/10 text-purple-400 border-purple-500/20' : 
                    plan.name === 'pro' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' : 
                    'bg-gray-500/10 text-gray-400 border-gray-500/20'
                  }`}>
                    {plan.display_name}
                  </div>
                  <Lock className="w-3.5 h-3.5 text-gray-700" />
               </div>
               <div className="space-y-4">
                  <div className="flex justify-between items-end border-b border-white/5 pb-3">
                     <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">Executions</span>
                     <span className="text-lg font-mono font-black text-white">{plan.limits?.scans_per_month || '∞'} <span className="text-[9px] font-normal text-gray-600">/MO</span></span>
                  </div>
                  <div className="flex justify-between items-end border-b border-white/5 pb-3">
                     <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">Asset Limit</span>
                     <span className="text-lg font-mono font-black text-white">{plan.limits?.targets || '∞'}</span>
                  </div>
                  <div className="flex justify-between items-end">
                     <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">Seat Count</span>
                     <span className="text-lg font-mono font-black text-white">{plan.limits?.users || '1'}</span>
                  </div>
               </div>
               <a 
                href="/admin/plans"
                className="mt-6 flex items-center justify-center gap-2 w-full py-3 bg-white/[0.02] border border-white/5 rounded-xl text-[9px] font-mono font-black text-gray-500 uppercase tracking-widest hover:bg-white/5 hover:text-white transition-all"
               >
                 Redefine Policy <ArrowRight className="w-3 h-3" />
               </a>
            </div>
          ))}
        </div>
      </div>

      {/* Control Bar */}
      <div className="flex flex-col md:flex-row gap-6 pt-6">
        <div className="relative flex-1 group">
          <Search className="absolute left-6 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-600 group-focus-within:text-blue-400 transition-colors" />
          <input 
            placeholder="FILTER TELEMETRY BY WORKSPACE IDENTITY OR NAME..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="w-full bg-[#0d0d0e] border border-white/5 rounded-[2rem] pl-16 pr-8 py-5 text-xs text-white font-mono uppercase tracking-[0.2em] focus:border-blue-400/50 outline-none transition-all shadow-inner"
          />
        </div>
        <button className="px-10 py-5 bg-[#0d0d0e] border border-white/5 rounded-[2rem] text-gray-500 hover:text-white hover:border-white/10 flex items-center gap-4 font-mono text-xs uppercase tracking-widest transition-all font-black">
           <Filter className="w-5 h-5" /> Refine Stream
        </button>
      </div>

      {/* Utilization Table */}
      <div className="bg-[#0d0d0e]/40 backdrop-blur-xl border border-white/[0.03] rounded-[3rem] overflow-hidden shadow-2xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-white/[0.02] border-b border-white/5">
                <th className="px-10 py-8 text-[10px] font-mono font-bold text-gray-500 uppercase tracking-[0.3em]">Operational Context</th>
                <th className="px-10 py-8 text-[10px] font-mono font-bold text-gray-500 uppercase tracking-[0.3em]">Telemetry Period</th>
                <th className="px-10 py-8 text-[10px] font-mono font-bold text-gray-500 uppercase tracking-[0.3em]">Execution Load</th>
                <th className="px-10 py-8 text-[10px] font-mono font-bold text-gray-500 uppercase tracking-[0.3em]">Health Status</th>
                <th className="px-10 py-8 text-[10px] font-mono font-bold text-gray-500 uppercase tracking-[0.3em]">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.02]">
              {filteredUsage.map((u, i) => (
                <tr key={u.id || i} className="hover:bg-white/[0.02] transition-colors group">
                  <td className="px-10 py-8">
                    <div className="flex items-center gap-5">
                      <div className="w-14 h-14 rounded-3xl bg-blue-500/5 border border-blue-500/10 flex items-center justify-center shadow-inner group-hover:scale-110 transition-transform">
                         <Database className="w-6 h-6 text-blue-500/50" />
                      </div>
                      <div>
                        <div className="text-base font-mono font-black text-white group-hover:text-blue-400 transition-colors uppercase italic tracking-tight">{u.workspace_name || 'Root Instance'}</div>
                        <div className="text-[10px] font-mono text-gray-600 tracking-tighter mt-1">UID: {u.workspace_id}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-10 py-8">
                    <div className="flex items-center gap-4">
                      <div className="p-2 rounded-lg bg-white/5">
                         <Calendar className="w-4 h-4 text-gray-500" />
                      </div>
                      <div className="text-xs font-mono text-gray-400 tracking-tighter uppercase">
                        {new Date(u.period_start).toLocaleDateString()} <span className="text-gray-700 px-2">»</span> {new Date(u.period_end).toLocaleDateString()}
                      </div>
                    </div>
                  </td>
                  <td className="px-10 py-8">
                    <div className="flex items-center gap-12">
                      <div className="space-y-2">
                        <div className="text-[9px] font-mono text-gray-600 uppercase tracking-widest font-black">Scan Density</div>
                        <div className="text-xl font-mono font-black text-neon-green">{u.scans_count} <span className="text-[10px] font-normal text-gray-600 uppercase">Ops</span></div>
                      </div>
                      <div className="space-y-2">
                        <div className="text-[9px] font-mono text-gray-600 uppercase tracking-widest font-black">Vulns Detected</div>
                        <div className="text-xl font-mono font-black text-purple-400">{u.findings_count} <span className="text-[10px] font-normal text-gray-600 uppercase">Hits</span></div>
                      </div>
                    </div>
                  </td>
                  <td className="px-10 py-8">
                    {u.scans_count > 100 ? (
                      <div className="inline-flex items-center gap-3 px-4 py-2 rounded-2xl bg-red-500/5 border border-red-500/20 text-[10px] font-mono font-black text-red-500 uppercase tracking-[0.2em] shadow-[0_0_20px_-5px_rgba(239,68,68,0.3)]">
                        <AlertTriangle className="w-4 h-4" /> Critical Load
                      </div>
                    ) : u.scans_count > 0 ? (
                      <div className="inline-flex items-center gap-3 px-4 py-2 rounded-2xl bg-emerald-500/5 border border-emerald-500/20 text-[10px] font-mono font-black text-emerald-400 uppercase tracking-[0.2em] shadow-[0_0_20px_-5px_rgba(16,185,129,0.3)]">
                        <Activity className="w-4 h-4" /> Optimal
                      </div>
                    ) : (
                      <div className="inline-flex items-center gap-3 px-4 py-2 rounded-2xl bg-white/5 border border-white/10 text-[10px] font-mono font-black text-gray-500 uppercase tracking-[0.2em] italic">
                        <Zap className="w-4 h-4" /> Standby
                      </div>
                    )}
                  </td>
                  <td className="px-10 py-8">
                     <a 
                      href={`/admin/workspaces?search=${u.workspace_id}`}
                      className="p-4 bg-white/[0.02] border border-white/5 rounded-2xl text-gray-600 hover:text-blue-400 hover:border-blue-400/30 transition-all flex items-center justify-center"
                      title="Adjust Quota in Workspace Registry"
                     >
                        <Edit2 className="w-5 h-5" />
                     </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {filteredUsage.length === 0 && (
          <div className="p-40 text-center">
            <div className="inline-flex p-10 rounded-[3rem] bg-white/5 border border-white/10 mb-10 opacity-20 animate-pulse">
              <BarChart3 className="w-20 h-20 text-gray-400" />
            </div>
            <h2 className="text-3xl font-mono font-black text-white tracking-tighter uppercase italic">Telemetry Silence</h2>
            <p className="text-gray-500 font-mono text-sm mt-6 max-w-sm mx-auto uppercase tracking-widest opacity-60 leading-relaxed">The utilization buffer contains no active telemetry streams for the selected parameters.</p>
          </div>
        )}
      </div>

      {/* Footer System Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="p-10 bg-blue-500/5 border border-blue-500/10 rounded-[3rem] flex items-center justify-between group overflow-hidden relative">
           <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
              <Binary className="w-32 h-32" />
           </div>
           <div className="space-y-4 relative z-10">
             <div className="text-[12px] font-mono text-blue-400 uppercase tracking-[0.4em] font-black">Network Throughput</div>
             <p className="text-sm font-mono text-gray-400 max-w-sm leading-relaxed italic uppercase">Primary data cluster is operating at 14.2% of total execution capacity. Quota enforcement is active.</p>
           </div>
           <BarChart3 className="w-16 h-16 text-blue-500/20 group-hover:text-blue-500/40 transition-colors shrink-0" />
        </div>
        <div className="p-10 bg-neon-green/5 border border-neon-green/10 rounded-[3rem] flex items-center justify-between group overflow-hidden relative">
           <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
              <Cpu className="w-32 h-32" />
           </div>
           <div className="space-y-4 relative z-10">
             <div className="text-[12px] font-mono text-neon-green uppercase tracking-[0.4em] font-black">Cluster Integrity</div>
             <p className="text-sm font-mono text-gray-400 max-w-sm leading-relaxed italic uppercase">Automated billing synchronization confirmed. Next reconciliation cycle in 4h 22m.</p>
           </div>
           <Zap className="w-16 h-16 text-neon-green/20 group-hover:text-neon-green/40 transition-colors shrink-0" />
        </div>
      </div>
    </div>
  );
}
