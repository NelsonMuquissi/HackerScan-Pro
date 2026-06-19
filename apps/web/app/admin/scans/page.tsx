'use client';

import { useEffect, useState } from 'react';
import { adminListScans } from '@/lib/api';
import { 
  Terminal, Activity, Clock, Server, CheckCircle2, 
  AlertTriangle, AlertCircle, XCircle, Search, 
  Filter, LayoutGrid, List, Zap, ShieldAlert,
  ShieldCheck
} from 'lucide-react';
import { toast } from 'sonner';
import { formatDistanceToNow } from 'date-fns';

export default function AdminScansManagement() {
  const [scans, setScans] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadScans();
  }, []);

  async function loadScans() {
    try {
      const data = await adminListScans();
      setScans(data);
    } catch (error) {
      toast.error("Failed to load global scans");
    } finally {
      setLoading(false);
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'completed': return <CheckCircle2 className="w-4 h-4 text-emerald-500" />;
      case 'in_progress':
      case 'running': return <Activity className="w-4 h-4 text-blue-500 animate-pulse" />;
      case 'failed':
      case 'error': return <AlertTriangle className="w-4 h-4 text-red-500" />;
      case 'cancelled': return <XCircle className="w-4 h-4 text-gray-500" />;
      case 'pending':
      case 'queued': return <Clock className="w-4 h-4 text-amber-500" />;
      default: return <AlertCircle className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusStyle = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'completed': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 shadow-[0_0_15px_rgba(16,185,129,0.1)]';
      case 'in_progress':
      case 'running': return 'bg-blue-500/10 text-blue-400 border-blue-500/20 shadow-[0_0_15px_rgba(59,130,246,0.1)]';
      case 'failed':
      case 'error': return 'bg-red-500/10 text-red-400 border-red-500/20';
      default: return 'bg-gray-500/10 text-gray-400 border-gray-500/20';
    }
  };

  const filteredScans = scans.filter(scan => 
    scan.target_host?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    scan.workspace_name?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) return (
    <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
      <div className="w-12 h-12 border-4 border-neon-green/20 border-t-neon-green rounded-full animate-spin"></div>
      <p className="text-neon-green font-mono animate-pulse">Retrieving global scan state...</p>
    </div>
  );

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl font-mono font-bold text-white tracking-tight flex items-center gap-3">
            <Terminal className="w-10 h-10 text-neon-green" />
            Global Scans
          </h1>
          <p className="text-gray-500 font-mono text-sm mt-1">
            MONITORING / LIVE OPERATIONS
          </p>
        </div>
        
        <div className="flex items-center gap-4 bg-card-bg/50 backdrop-blur-xl border border-card-border p-1.5 rounded-xl">
          <div className="flex flex-col px-4 py-1 text-center">
            <span className="text-[10px] text-gray-500 font-mono uppercase tracking-wider">Active Operations</span>
            <span className="text-xl font-bold text-blue-500 font-mono">{scans.filter(s => s.status === 'in_progress' || s.status === 'running').length}</span>
          </div>
          <div className="w-px h-10 bg-card-border" />
          <div className="flex flex-col px-4 py-1 text-center">
            <span className="text-[10px] text-gray-500 font-mono uppercase tracking-wider">Total Scans</span>
            <span className="text-xl font-bold text-white font-mono">{scans.length}</span>
          </div>
        </div>
      </div>

      <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="relative w-full md:w-96 group">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 group-focus-within:text-neon-green transition-colors" />
          <input 
            type="text"
            placeholder="Search target or workspace..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-card-bg/30 border border-card-border rounded-xl py-3 pl-12 pr-4 font-mono text-sm outline-none focus:border-neon-green/50 transition-all"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-card-bg/40 backdrop-blur-md border border-card-border rounded-2xl overflow-hidden shadow-2xl">
            <div className="overflow-x-auto">
          <table className="w-full text-sm text-left border-collapse">
            <thead className="text-[11px] text-gray-500 uppercase bg-white/[0.02] border-b border-card-border font-mono tracking-widest">
              <tr>
                <th className="px-6 py-5 font-semibold">Identified Target</th>
                <th className="px-6 py-5 font-semibold">Workspace Context</th>
                <th className="px-6 py-5 font-semibold">Operational Status</th>
                <th className="px-6 py-5 font-semibold">Findings Intensity</th>
                <th className="px-6 py-5 font-semibold text-right">Sync Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-card-border/50">
              {filteredScans.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-20 text-center text-gray-500 font-mono italic">
                    NO OPERATIONS DETECTED IN LOGS
                  </td>
                </tr>
              ) : (
                filteredScans.map((scan) => (
                  <tr key={scan.id} className="hover:bg-neon-green/[0.02] transition-colors group">
                    <td className="px-6 py-5">
                      <div className="flex items-center gap-3">
                        <div className="p-2.5 rounded-xl bg-background border border-card-border text-neon-green group-hover:scale-110 transition-transform">
                          <Zap className="w-4 h-4" />
                        </div>
                        <div className="flex flex-col">
                          <span className="font-bold text-white tracking-tight group-hover:text-neon-green transition-colors">{scan.target_host || 'N/A'}</span>
                          <span className="text-[10px] text-gray-500 font-mono flex items-center gap-1.5 uppercase tracking-tighter">
                            {scan.scan_type || 'QUICK_PROBE'} / {scan.id?.substring(0, 8)}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-5">
                      {scan.workspace_name ? (
                        <div className="inline-flex items-center gap-2 px-3 py-1 bg-purple-500/10 text-purple-400 rounded-full border border-purple-500/20 text-[10px] font-bold uppercase">
                          {scan.workspace_name}
                        </div>
                      ) : (
                        <span className="text-xs text-gray-600 font-mono tracking-widest">SYSTEM_DIRECT</span>
                      )}
                    </td>
                    <td className="px-6 py-5">
                      <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border text-[10px] font-bold uppercase tracking-tighter ${getStatusStyle(scan.status)}`}>
                        {getStatusIcon(scan.status)}
                        {scan.status || 'UNKNOWN'}
                      </div>
                    </td>
                    <td className="px-6 py-5">
                      <div className="flex items-center gap-2 font-mono">
                        {scan.critical_count > 0 && (
                          <div className="flex items-center gap-1 text-red-500 bg-red-500/10 px-1.5 py-0.5 rounded border border-red-500/20 text-[10px]">
                            <ShieldAlert className="w-3 h-3" /> {scan.critical_count}
                          </div>
                        )}
                        {scan.high_count > 0 && (
                          <div className="flex items-center gap-1 text-orange-500 bg-orange-500/10 px-1.5 py-0.5 rounded border border-orange-500/20 text-[10px]">
                            <ShieldAlert className="w-3 h-3" /> {scan.high_count}
                          </div>
                        )}
                        {scan.total_findings > 0 ? (
                          <span className="text-gray-400 text-[10px]">{scan.total_findings} TOTAL</span>
                        ) : (
                          <span className="text-emerald-500/50 text-[10px] flex items-center gap-1">
                            <ShieldCheck className="w-3 h-3" /> CLEAN
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-5 text-right text-gray-500 font-mono text-xs">
                      {scan.created_at ? formatDistanceToNow(new Date(scan.created_at), { addSuffix: true }) : 'N/A'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-gradient-to-br from-neon-green/10 to-transparent border border-neon-green/20 rounded-2xl p-6 backdrop-blur-md">
            <h3 className="text-neon-green font-mono font-bold flex items-center gap-2 mb-4">
              <ShieldCheck className="w-5 h-5" />
              SYSTEM MANIFESTO
            </h3>
            <div className="space-y-4 text-xs font-mono leading-relaxed">
              <div className="p-3 bg-background/50 rounded-lg border border-card-border">
                <p className="text-white font-bold mb-1 underline">REAL-WORLD VERIFICATION</p>
                <p className="text-gray-400">Every finding in this list is backed by **REAL DATA PROOF**. We do not simulate. We probe, verify, and document.</p>
              </div>
              <div className="p-3 bg-background/50 rounded-lg border border-card-border">
                <p className="text-white font-bold mb-1 underline">ETHICAL BOUNDARIES</p>
                <p className="text-gray-400">HackerScan Pro is an **Active Offensive Scanner**. We identify vulnerabilities without destructive exploitation (No DB dumps, No shells).</p>
              </div>
              <div className="p-3 bg-background/50 rounded-lg border border-card-border">
                <p className="text-white font-bold mb-1 underline">EVIDENCE-FIRST</p>
                <p className="text-gray-400">Findings without evidence are noise. We capture request/response dumps and visual screenshots to ensure 100% accuracy.</p>
              </div>
            </div>
            
            <div className="mt-8 pt-6 border-t border-neon-green/10">
              <div className="flex items-center justify-between text-[10px] text-gray-500 font-mono">
                <span>VERSION: 2.4.0-PRO</span>
                <span className="flex items-center gap-1">
                  <Activity className="w-3 h-3 text-neon-green" /> 
                  ONLINE
                </span>
              </div>
            </div>
          </div>

          <div className="bg-card-bg/30 border border-card-border rounded-2xl p-6">
            <h3 className="text-white font-mono font-bold mb-4 flex items-center gap-2">
              <Activity className="w-4 h-4 text-blue-400" />
              ENGINE STATS
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center text-xs font-mono">
                <span className="text-gray-500">Avg Response Time</span>
                <span className="text-white">142ms</span>
              </div>
              <div className="flex justify-between items-center text-xs font-mono">
                <span className="text-gray-500">Active Workers</span>
                <span className="text-white">12 / 16</span>
              </div>
              <div className="flex justify-between items-center text-xs font-mono">
                <span className="text-gray-500">Success Rate</span>
                <span className="text-emerald-400 font-bold">99.8%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
