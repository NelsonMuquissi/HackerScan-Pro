'use client';

import { useEffect, useState } from 'react';
import { adminListCTLogs } from '@/lib/api';
import { 
  Server, Activity, Database, Clock, 
  Globe, Shield, Search, RefreshCcw, 
  ExternalLink, Layers, AlertCircle
} from 'lucide-react';
import { toast } from 'sonner';

export default function CTLogsManagement() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadCTLogs();
  }, []);

  async function loadCTLogs() {
    setLoading(true);
    try {
      const result = await adminListCTLogs();
      setData(result);
    } catch (error) {
      toast.error("Failed to load CT Logs");
    } finally {
      setLoading(false);
    }
  }

  const logs = data?.recent_targets || [];
  const total = data?.total_discovered || 0;

  const filteredLogs = logs.filter((log: any) => 
    log.host?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    log.workspace?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) return (
    <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
      <div className="w-12 h-12 border-4 border-neon-green/20 border-t-neon-green rounded-full animate-spin"></div>
      <p className="text-neon-green font-mono animate-pulse">Monitoring Certificate Transparency streams...</p>
    </div>
  );

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl font-mono font-bold text-white tracking-tight flex items-center gap-3">
            <Globe className="w-10 h-10 text-neon-green" />
            CT Log Monitoring
          </h1>
          <p className="text-gray-500 font-mono text-sm mt-1">
            NETWORK DISCOVERY / CERTIFICATE TRANSPARENCY
          </p>
        </div>
        
        <div className="flex items-center gap-4 bg-card-bg/50 backdrop-blur-xl border border-card-border p-1.5 rounded-xl">
          <div className="flex flex-col px-4 py-1 text-center">
            <span className="text-[10px] text-gray-500 font-mono uppercase tracking-wider">Discovered Assets</span>
            <span className="text-xl font-bold text-white font-mono">{total}</span>
          </div>
          <div className="w-px h-10 bg-card-border" />
          <button 
            onClick={loadCTLogs}
            className="p-3 bg-neon-green/10 text-neon-green hover:bg-neon-green/20 rounded-lg transition-all border border-neon-green/20 group"
          >
            <RefreshCcw className="w-5 h-5 group-active:rotate-180 transition-transform duration-500" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-card-bg/40 border border-card-border p-5 rounded-2xl flex items-center gap-4">
          <div className="p-3 rounded-xl bg-blue-500/10 text-blue-400">
            <Database className="w-6 h-6" />
          </div>
          <div>
            <p className="text-[10px] text-gray-500 font-mono uppercase">Log Streams</p>
            <h3 className="text-lg font-bold text-white font-mono">ACTIVE</h3>
          </div>
        </div>
        <div className="bg-card-bg/40 border border-card-border p-5 rounded-2xl flex items-center gap-4">
          <div className="p-3 rounded-xl bg-emerald-500/10 text-emerald-400">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <p className="text-[10px] text-gray-500 font-mono uppercase">Polling Rate</p>
            <h3 className="text-lg font-bold text-white font-mono">REAL-TIME</h3>
          </div>
        </div>
        <div className="bg-card-bg/40 border border-card-border p-5 rounded-2xl flex items-center gap-4">
          <div className="p-3 rounded-xl bg-purple-500/10 text-purple-400">
            <Layers className="w-6 h-6" />
          </div>
          <div>
            <p className="text-[10px] text-gray-500 font-mono uppercase">Coverage</p>
            <h3 className="text-lg font-bold text-white font-mono">GLOBAL</h3>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative flex-grow group">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 group-focus-within:text-neon-green transition-colors" />
          <input 
            type="text"
            placeholder="Search host or workspace..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-card-bg/30 border border-card-border rounded-xl py-3 pl-12 pr-4 font-mono text-sm outline-none focus:border-neon-green/50 transition-all"
          />
        </div>
      </div>

      <div className="bg-card-bg/40 backdrop-blur-md border border-card-border rounded-2xl overflow-hidden shadow-2xl">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left border-collapse">
            <thead className="text-[11px] text-gray-500 uppercase bg-white/[0.02] border-b border-card-border font-mono tracking-widest">
              <tr>
                <th className="px-6 py-5 font-semibold">Identified Host</th>
                <th className="px-6 py-5 font-semibold">Workspace Context</th>
                <th className="px-6 py-5 font-semibold">Operational Status</th>
                <th className="px-6 py-5 font-semibold">Detection Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-card-border/50">
              {filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-20 text-center text-gray-500 font-mono italic">
                    <div className="flex flex-col items-center gap-3">
                      <AlertCircle className="w-8 h-8 opacity-20" />
                      NO CT RECORDS DETECTED IN CURRENT VIEWPORT
                    </div>
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log: any) => (
                  <tr key={log.id} className="hover:bg-neon-green/[0.02] transition-colors group">
                    <td className="px-6 py-5 font-mono">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-background border border-card-border text-neon-green">
                          <Shield className="w-4 h-4" />
                        </div>
                        <div className="flex flex-col">
                          <span className="font-bold text-white tracking-tight group-hover:text-neon-green transition-colors">{log.host}</span>
                          <span className="text-[10px] text-gray-500">HTTPS MONITORING ENABLED</span>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-5">
                      {log.workspace ? (
                        <div className="inline-flex items-center gap-2 px-3 py-1 bg-purple-500/10 text-purple-400 rounded-full border border-purple-500/20 text-[10px] font-bold uppercase tracking-tight">
                          {log.workspace}
                        </div>
                      ) : (
                        <span className="text-xs text-gray-600 font-mono">GLOBAL_REGISTRY</span>
                      )}
                    </td>
                    <td className="px-6 py-5">
                      <div className="flex items-center gap-2.5">
                        <div className="relative flex h-2 w-2">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                        </div>
                        <span className="text-emerald-500 text-xs font-bold font-mono tracking-tighter uppercase">
                          ACTIVE_MONITOR
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-5 text-gray-400 font-mono text-xs">
                      <div className="flex items-center gap-2">
                        <Clock className="w-3.5 h-3.5 opacity-50" />
                        {log.created_at ? new Date(log.created_at).toLocaleString() : 'PENDING...'}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
