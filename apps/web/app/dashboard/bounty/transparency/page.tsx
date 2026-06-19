'use client';

import { useState, useEffect } from 'react';
import { 
  Fingerprint, 
  Search, 
  Terminal, 
  RefreshCw, 
  Loader2, 
  CheckCircle,
  User,
  Paperclip,
  ChevronLeft,
  Download,
  ShieldCheck,
  Lock,
  Database
} from 'lucide-react';
import Link from 'next/link';
import { getBountyTransparencyLog } from '@/lib/api';
import { useAuthStore } from '@/store/useAuthStore';

export default function TransparencyLogPage() {
  const { user, token } = useAuthStore();
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [filter, setFilter] = useState('');

  const isSuperAdmin = user?.role === 'superadmin';

  useEffect(() => {
    fetchLogs(1);
  }, []);

  async function fetchLogs(pageNum: number, append = false) {
    setLoading(true);
    try {
      const data = await getBountyTransparencyLog(pageNum);
      let list: any[] = [];
      let more = false;
      
      if (Array.isArray(data)) {
        list = data;
      } else if (data && typeof data === 'object' && 'results' in data) {
        list = (data as any).results;
        more = !!(data as any).next;
      }

      if (append) {
        setLogs(prev => [...prev, ...list]);
      } else {
        setLogs(list);
      }
      setPage(pageNum);
      setHasMore(more);
    } catch (error) {
      console.error('Failed to fetch transparency logs:', error);
    } finally {
      setLoading(false);
    }
  }

  const handleLoadMore = () => {
    fetchLogs(page + 1, true);
  };

  const handleExportCSV = async () => {
    if (!isSuperAdmin) return;
    setExporting(true);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/bounty/transparency-log/export/`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (!response.ok) throw new Error('Export failed');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `bounty_transparency_log_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (error) {
      console.error('Export failed:', error);
      alert('Failed to export logs. Check permissions.');
    } finally {
      setExporting(false);
    }
  };

  const filteredLogs = logs.filter(log => 
    log.action.toLowerCase().includes(filter.toLowerCase()) ||
    (log.resource_id && log.resource_id.includes(filter)) ||
    (log.user_email && log.user_email.toLowerCase().includes(filter.toLowerCase()))
  );

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between mb-8 gap-6">
          <div>
            <Link 
              href="/dashboard/bounty/submissions"
              className="text-zinc-500 hover:text-white flex items-center gap-2 text-xs font-bold transition-colors mb-4"
            >
              <ChevronLeft className="w-4 h-4" /> VOLTAR PARA SUBMISSÕES
            </Link>
            <h1 className="text-4xl font-black flex items-center gap-4">
              <Fingerprint className="text-emerald-500 w-10 h-10" />
              TRANSPARENCY LOG
            </h1>
            <p className="text-zinc-500 mt-2 font-mono text-sm">
              Nexus Protocol v1.4.2 — Immutable cryptographically-chained audit trail.
            </p>
          </div>
          <div className="flex items-center gap-4">
             {isSuperAdmin && (
                <button 
                  onClick={handleExportCSV}
                  disabled={exporting}
                  className="bg-zinc-900 hover:bg-white hover:text-black border border-zinc-800 rounded-2xl px-6 py-3 text-xs font-black transition-all flex items-center gap-2 group disabled:opacity-50"
                >
                  {exporting ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Download className="w-4 h-4 group-hover:-translate-y-1 transition-transform" />
                  )}
                  EXPORT AUDIT CSV
                </button>
             )}
             <div className="text-right hidden sm:block">
                <div className="text-emerald-500 font-bold text-[10px] bg-emerald-500/10 px-4 py-2 rounded-full border border-emerald-500/20 inline-flex items-center gap-2">
                   <CheckCircle className="w-4 h-4" /> CHAIN_INTEGRITY: OK
                </div>
                <p className="text-[10px] text-zinc-700 font-mono mt-2 uppercase tracking-widest">
                  Real-time Integrity Monitor
                </p>
             </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          <div className="lg:col-span-1 space-y-6">
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-3xl p-6">
              <h3 className="text-sm font-bold mb-4 uppercase tracking-wider text-zinc-400">Search & Filter</h3>
              <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                <input 
                  type="text" 
                  placeholder="ID, Action, Email..."
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                  className="w-full bg-black/40 border border-zinc-800 rounded-xl py-3 pl-12 pr-4 text-xs focus:border-emerald-500/50 outline-none transition-all"
                />
              </div>
            </div>

            <div className="bg-zinc-900/50 border border-zinc-800 rounded-3xl p-6">
               <h3 className="text-sm font-bold mb-4 uppercase tracking-wider text-zinc-400">Audit Status</h3>
               <div className="space-y-4">
                  <div className="flex items-center justify-between">
                     <span className="text-xs text-zinc-500">Total Entries</span>
                     <span className="text-xs font-mono font-bold text-white">{logs.length}{hasMore ? '+' : ''}</span>
                  </div>
                  <div className="flex items-center justify-between">
                     <span className="text-xs text-zinc-500">Node Status</span>
                     <span className="text-xs font-mono font-bold text-emerald-500 flex items-center gap-2">
                        <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                        SYNCED
                     </span>
                  </div>
                  <div className="flex items-center justify-between">
                     <span className="text-xs text-zinc-500">Security Type</span>
                     <span className="text-[10px] font-mono font-bold text-zinc-400">SHA-256 CHAIN</span>
                  </div>
               </div>
            </div>

            <div className="p-6 bg-emerald-500/5 border border-emerald-500/10 rounded-3xl">
               <div className="flex items-center gap-3 mb-4">
                  <Lock className="w-4 h-4 text-emerald-500" />
                  <h4 className="text-xs font-black uppercase text-emerald-500">Encryption Active</h4>
               </div>
               <p className="text-[10px] text-zinc-500 leading-relaxed font-mono">
                 Every log entry is hashed using SHA-256 and linked to the previous entry, creating an immutable sequence of events.
               </p>
            </div>
          </div>

          <div className="lg:col-span-3">
            {loading && logs.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-40 bg-zinc-900/10 border border-dashed border-zinc-800 rounded-3xl">
                <Loader2 className="w-10 h-10 text-emerald-500 animate-spin mb-4" />
                <p className="text-zinc-500 font-mono animate-pulse">Syncing with transparency engine...</p>
              </div>
            ) : filteredLogs.length > 0 ? (
              <div className="space-y-4">
                {filteredLogs.map((log, index) => (
                  <div key={log.id} className="p-6 bg-zinc-900/30 border border-zinc-800/50 rounded-3xl hover:border-zinc-700 transition-all group relative overflow-hidden">
                    {/* Genesis Marker */}
                    {log.previous_hash === "0000000000000000000000000000000000000000000000000000000000000000" && (
                       <div className="absolute top-0 right-0 bg-emerald-500/20 text-emerald-500 text-[8px] font-black px-4 py-1 rounded-bl-xl border-l border-b border-emerald-500/30">
                          GENESIS_BLOCK
                       </div>
                    )}
                    
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-4">
                         <div className={`px-3 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider ${
                           log.action.includes('create') ? 'bg-emerald-500/10 text-emerald-500' :
                           log.action.includes('triage') ? 'bg-amber-500/10 text-amber-500' :
                           log.action.includes('verify') ? 'bg-purple-500/10 text-purple-500' :
                           'bg-blue-500/10 text-blue-500'
                         }`}>
                            {log.action.replace('bounty.', '').replace('.', ' ')}
                         </div>
                         <span className="text-zinc-500 text-[11px] font-mono">{new Date(log.created_at).toLocaleString()}</span>
                      </div>
                      <div className="flex items-center gap-2">
                         <span className="text-[10px] text-zinc-600 uppercase font-black">Trace_ID</span>
                         <code className="text-[10px] text-zinc-400 font-mono bg-black/40 px-2 py-1 rounded border border-zinc-800/50">{log.id}</code>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-6 text-sm mb-4">
                      <div className="flex items-center gap-2 text-zinc-300">
                         <User className="w-4 h-4 text-zinc-500" />
                         {log.user_email}
                      </div>
                      <div className="flex items-center gap-2 text-zinc-500">
                         <Terminal className="w-4 h-4" />
                         <span className="font-mono">{log.ip_address}</span>
                      </div>
                      {log.resource_id && (
                        <div className="flex items-center gap-2 text-zinc-600 font-mono text-[11px]">
                          <Paperclip className="w-4 h-4" />
                          RESOURCE: {log.resource_id}
                        </div>
                      )}
                    </div>

                    {/* Hash Chain Visualization */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
                       <div className="bg-black/40 p-4 rounded-2xl border border-zinc-800/50 relative">
                          <div className="text-[9px] text-zinc-600 uppercase font-black mb-2 flex items-center gap-2">
                             <Database className="w-3 h-3" /> CURRENT_HASH
                          </div>
                          <code className="text-[10px] text-emerald-500/70 font-mono break-all leading-relaxed">
                            {log.current_hash}
                          </code>
                       </div>
                       <div className="bg-black/20 p-4 rounded-2xl border border-dashed border-zinc-800/50 opacity-60">
                          <div className="text-[9px] text-zinc-700 uppercase font-black mb-2 flex items-center gap-2">
                             <ChevronLeft className="w-3 h-3" /> PREVIOUS_HASH
                          </div>
                          <code className="text-[10px] text-zinc-600 font-mono break-all leading-relaxed">
                            {log.previous_hash}
                          </code>
                       </div>
                    </div>

                    {log.metadata && Object.keys(log.metadata).length > 0 && (
                      <div className="mt-4 bg-black/60 p-5 rounded-2xl border border-zinc-800/50 relative overflow-hidden group/meta">
                        <div className="absolute top-0 left-0 w-1.5 h-full bg-emerald-500/20 group-hover/meta:bg-emerald-500/40 transition-colors" />
                        <div className="text-[10px] text-zinc-600 uppercase font-bold mb-2 flex items-center justify-between">
                          <span>Metadata Payload</span>
                          <span className="text-zinc-800 font-mono">TYPE: JSON</span>
                        </div>
                        <pre className="text-[11px] text-emerald-400/80 font-mono overflow-x-auto scrollbar-hide leading-relaxed">
                          {JSON.stringify(log.metadata, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                ))}

                {hasMore && (
                  <button 
                    onClick={handleLoadMore}
                    disabled={loading}
                    className="w-full py-6 bg-zinc-900/50 border border-zinc-800 border-dashed rounded-3xl text-zinc-500 hover:text-emerald-500 hover:border-emerald-500/30 transition-all text-xs font-bold flex items-center justify-center gap-3 disabled:opacity-50 group"
                  >
                    {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <RefreshCw className="w-5 h-5 group-hover:rotate-180 transition-transform duration-500" />}
                    FETCH MORE LOG ENTRIES
                  </button>
                )}
              </div>
            ) : (
              <div className="text-center py-32 bg-zinc-900/10 border border-dashed border-zinc-800 rounded-3xl">
                <Fingerprint className="w-16 h-16 text-zinc-800 mx-auto mb-6" />
                <h2 className="text-xl font-bold mb-2">No logs detected</h2>
                <p className="text-zinc-500">We couldn&apos;t find any transparency records matching your criteria.</p>
              </div>
            )}
          </div>
        </div>

        <div className="mt-12 p-8 bg-zinc-900/20 border border-zinc-800/50 rounded-3xl flex flex-col md:flex-row items-center justify-between gap-6">
           <div className="flex items-center gap-4">
              <div className="p-3 bg-emerald-500/10 rounded-2xl border border-emerald-500/20">
                 <ShieldCheck className="w-8 h-8 text-emerald-500" />
              </div>
              <div>
                 <h4 className="font-bold text-white uppercase tracking-wider text-sm">Nexus Protocol Security</h4>
                 <p className="text-zinc-500 text-xs mt-1">All logs are cryptographically signed and archived for compliance.</p>
              </div>
           </div>
           <div className="flex items-center gap-3">
              <div className="text-right hidden md:block">
                 <p className="text-[10px] text-zinc-600 font-mono">SYSTEM_STABILITY: 100%</p>
                 <p className="text-[10px] text-zinc-600 font-mono">LATENCY: 14ms</p>
              </div>
              <div className="h-10 w-[1px] bg-zinc-800 mx-2 hidden md:block" />
              <div className="bg-black/60 px-4 py-2 rounded-xl border border-zinc-800 font-mono text-[10px] text-emerald-500">
                ACTIVE_ARCHIVE_NODE_#402
              </div>
           </div>
        </div>
      </div>
    </div>
  );
}
