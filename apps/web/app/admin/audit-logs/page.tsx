"use client";

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { FileText, User, Terminal, Clock, ShieldCheck, ShieldAlert, History, RotateCcw, Database, AlertCircle, Search, Filter, Download, Activity, ExternalLink, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { adminListAuditLogs, adminRunMaintenance, adminGetSystemHealth, adminExportAuditLogs } from '@/lib/api';
import { formatDistanceToNow } from 'date-fns';
import { motion, AnimatePresence } from 'framer-motion';

export default function AdminAuditLogsPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedLog, setSelectedLog] = useState<any | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [backfilling, setBackfilling] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [health, setHealth] = useState<any>(null);
  const [liveMode, setLiveMode] = useState(false);
  const [lastSync, setLastSync] = useState<Date>(new Date());
  const [isSyncError, setIsSyncError] = useState(false);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    initLoad();
  }, []);

  // Optimized initialization
  const initLoad = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [logsData, healthData] = await Promise.all([
        adminListAuditLogs(),
        adminGetSystemHealth()
      ]);
      setLogs(logsData);
      setHealth(healthData);
      setLastSync(new Date());
      setIsSyncError(false);
    } catch (err) {
      setError('Connection to Nexus Protocol failed. Check system status.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    initLoad();
  }, [initLoad]);

  // Optimized health check with silent failure
  const loadHealth = useCallback(async () => {
    try {
      const data = await adminGetSystemHealth();
      setHealth(data);
      setIsSyncError(false);
    } catch (error) {
      setIsSyncError(true);
      console.warn('System health check failed - background task suppressed');
    }
  }, []);

  // Optimized log fetching with silent failure
  const loadLogs = useCallback(async (isSilent = false) => {
    if (!isSilent) setRefreshing(true);
    try {
      const data = await adminListAuditLogs();
      setLogs(data);
      setLastSync(new Date());
      setIsSyncError(false);
    } catch (error) {
      setIsSyncError(true);
      if (!isSilent) toast.error('Failed to sync logs');
    } finally {
      setRefreshing(false);
    }
  }, []);

  // Smarter polling mechanism
  useEffect(() => {
    let timer: NodeJS.Timeout;
    const isRepairing = health?.audit_integrity?.repair_progress?.status === 'RUNNING';
    
    if (liveMode || isRepairing) {
      timer = setInterval(() => {
        loadHealth();
        if (liveMode) loadLogs(true);
      }, 3000);
    }

    return () => {
      if (timer) clearInterval(timer);
    };
  }, [liveMode, health?.audit_integrity?.repair_progress?.status, loadHealth, loadLogs]);

  const filtered = useMemo(() => {
    const q = debouncedSearch.trim().toLowerCase();
    if (!q) return logs;
    return logs.filter(
      (l) =>
        l.action?.toLowerCase().includes(q) ||
        l.user_email?.toLowerCase().includes(q) ||
        l.resource_type?.toLowerCase().includes(q) ||
        l.description?.toLowerCase().includes(q)
    );
  }, [logs, debouncedSearch]);

  async function handleVerifyTrail() {
    if (verifying) return;
    setVerifying(true);
    try {
      const promise = adminRunMaintenance('verify_audit');
      toast.promise(promise, {
        loading: 'Verifying cryptographic chain...',
        success: 'Chain integrity verified.',
        error: 'Verification timed out. Check system logs.'
      });
      await promise;
      await loadHealth();
    } catch (err) {
      // Handled by toast
    } finally {
      setVerifying(false);
    }
  }

  async function handleBackfill() {
    if (!confirm('Proceed with cryptographic backfill for all legacy logs?')) return;
    setBackfilling(true);
    try {
      const promise = adminRunMaintenance('backfill_audit');
      toast.promise(promise, {
        loading: 'Backfilling legacy blocks...',
        success: 'Backfill sequence initiated.',
        error: 'Backfill failed to start.'
      });
      await promise;
      // Immediate feedback for backfill
      setTimeout(() => {
        loadLogs(true);
        loadHealth();
      }, 1000);
    } catch (err) {
      // Handled by toast
    } finally {
      setBackfilling(false);
    }
  }

  async function handleRepairChain() {
    if (!confirm('CRITICAL: This will re-hash the entire audit trail. Proceed?')) return;
    setVerifying(true);
    try {
      const promise = adminRunMaintenance('repair_audit');
      toast.promise(promise, {
        loading: 'Initializing emergency repair...',
        success: 'Repair sequence started in background.',
        error: 'Failed to initiate repair.'
      });
      await promise;
      // Optimistic health update to trigger progress bar
      setHealth((prev: any) => ({
        ...prev,
        audit_integrity: {
          ...prev?.audit_integrity,
          repair_progress: { status: 'RUNNING', percent: 0, processed: 0 }
        }
      }));
      await loadHealth();
    } catch (err) {
      // Handled by toast
    } finally {
      setVerifying(false);
    }
  }

  async function handleExport(format: 'csv' | 'json') {
    setExporting(true);
    try {
      const blob = await adminExportAuditLogs(format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-logs-${new Date().toISOString()}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success(`Exported as ${format.toUpperCase()}`);
    } catch (err) {
      toast.error('Export failed');
    } finally {
      setExporting(false);
    }
  }

  const repairProgress = health?.audit_integrity?.repair_progress;

  if (loading) return <AuditLogsSkeleton />;

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-4">
        <AlertCircle className="w-12 h-12 text-red-500 animate-pulse" />
        <h2 className="text-xl font-mono text-white">{error}</h2>
        <button 
          onClick={initLoad}
          className="bg-neon-green text-black px-6 py-2 rounded font-mono font-bold hover:scale-105 transition-transform"
        >
          RETRY CONNECTION
        </button>
      </div>
    );
  }

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6 pb-20 max-w-[1600px] mx-auto"
    >
      {/* Integrity Banner */}
      <AnimatePresence mode="wait">
        {health?.audit_integrity && (
          <motion.div 
            key="integrity-banner"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-2"
          >
            <div className={`border p-4 rounded-xl flex items-center justify-between font-mono backdrop-blur-md transition-colors duration-500 ${
              health.audit_integrity.status === 'SECURE' 
                ? 'bg-neon-green/5 border-neon-green/20 text-neon-green shadow-[0_0_20px_rgba(57,255,20,0.05)]' 
                : health.audit_integrity.status === 'COMPROMISED'
                  ? 'bg-red-500/5 border-red-500/20 text-red-500 shadow-[0_0_20px_rgba(239,68,68,0.05)]'
                  : 'bg-yellow-500/5 border-yellow-500/20 text-yellow-500 shadow-[0_0_20px_rgba(234,179,8,0.05)]'
            }`}>
              <div className="flex items-center gap-4">
                <div className={`p-2.5 rounded-full transition-colors ${
                  health.audit_integrity.status === 'SECURE' ? 'bg-neon-green/20' : 'bg-red-500/20'
                }`}>
                  {health.audit_integrity.status === 'SECURE' ? <ShieldCheck className="w-6 h-6" /> : <ShieldAlert className="w-6 h-6" />}
                </div>
                <div>
                  <div className="text-sm font-bold uppercase tracking-[0.2em] flex items-center gap-2">
                    Chain Status: {health.audit_integrity.status}
                    {isSyncError && <div className="w-2 h-2 rounded-full bg-red-500 shadow-[0_0_10px_#ef4444]" title="Sync Connection Issues" />}
                  </div>
                  <div className="text-[10px] opacity-70 mt-0.5">
                    {health.audit_integrity.total_chained_logs.toLocaleString()} logs secured via Nexus Protocol v1.4.2
                    {health.audit_integrity.last_check_at && ` • Last verified: ${new Date(health.audit_integrity.last_check_at).toLocaleTimeString()}`}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4">
                {refreshing && (
                  <motion.div 
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="flex items-center gap-2 text-[10px] uppercase font-bold text-neon-green bg-neon-green/10 px-3 py-1.5 rounded-lg border border-neon-green/20 shadow-[0_0_15px_rgba(57,255,20,0.1)]"
                  >
                    <RefreshCw className="w-3 h-3 animate-spin" />
                    Syncing Trail...
                  </motion.div>
                )}
                {health.audit_integrity.tampered_detected > 0 && !repairProgress && (
                  <button
                    onClick={handleRepairChain}
                    className="bg-red-500 hover:bg-red-600 text-white px-4 py-1.5 rounded-lg text-xs font-bold uppercase transition-all shadow-lg shadow-red-500/20 hover:scale-105 active:scale-95"
                  >
                    Attempt Emergency Repair
                  </button>
                )}
                <div className="h-8 w-px bg-white/10 hidden sm:block" />
                <button
                  onClick={() => setLiveMode(!liveMode)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase transition-all border group relative ${
                    liveMode 
                      ? 'bg-neon-green text-black border-neon-green shadow-[0_0_15px_rgba(57,255,20,0.3)]' 
                      : 'bg-white/5 text-gray-500 border-white/10 hover:bg-white/10'
                  }`}
                >
                  <Activity className={`w-3 h-3 ${liveMode ? 'animate-pulse' : ''}`} />
                  Live Sync {liveMode ? 'ON' : 'OFF'}
                  {liveMode && (
                    <span className="absolute -top-1 -right-1 flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
                    </span>
                  )}
                </button>
              </div>
            </div>

            {repairProgress && (
              <motion.div 
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="bg-[#0A0A0A] border border-white/5 rounded-xl p-5 font-mono overflow-hidden shadow-2xl"
              >
                <div className="flex justify-between items-center mb-3">
                  <div className="flex items-center gap-3">
                    <div className="p-1.5 rounded bg-neon-green/10">
                      <RotateCcw className={`w-4 h-4 text-neon-green ${repairProgress.status === 'RUNNING' ? 'animate-spin' : ''}`} />
                    </div>
                    <div>
                      <span className="text-xs font-bold uppercase text-white">
                        Chain Reconstruction in Progress
                      </span>
                      <div className="text-[9px] text-gray-500 uppercase mt-0.5">Status: {repairProgress.status}</div>
                    </div>
                  </div>
                  <span className="text-lg font-bold text-neon-green">{repairProgress.percent}%</span>
                </div>
                <div className="w-full bg-black rounded-full h-1.5 overflow-hidden border border-white/5">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: `${repairProgress.percent}%` }}
                    className="bg-neon-green h-full shadow-[0_0_15px_rgba(57,255,20,0.6)]"
                  />
                </div>
                <div className="mt-4 grid grid-cols-3 gap-4">
                  <div className="bg-white/5 p-2 rounded-lg border border-white/5 text-center">
                    <div className="text-[9px] text-gray-500 uppercase">Processed</div>
                    <div className="text-xs font-bold text-white">{repairProgress.processed.toLocaleString()}</div>
                  </div>
                  <div className="bg-white/5 p-2 rounded-lg border border-white/5 text-center">
                    <div className="text-[9px] text-gray-500 uppercase">Violations</div>
                    <div className="text-xs font-bold text-red-500">{repairProgress.violations || 0}</div>
                  </div>
                  <div className="bg-white/5 p-2 rounded-lg border border-white/5 text-center">
                    <div className="text-[9px] text-gray-500 uppercase">Repaired</div>
                    <div className="text-xs font-bold text-neon-green">{repairProgress.repaired || 0}</div>
                  </div>
                </div>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex flex-col xl:flex-row justify-between xl:items-end gap-6">
        <div className="space-y-1">
          <h1 className="text-4xl font-mono font-bold text-white tracking-tighter uppercase">Audit Trail</h1>
          <div className="flex items-center gap-3">
             <div className="h-1.5 w-1.5 rounded-full bg-neon-green animate-pulse" />
             <p className="text-[10px] text-gray-500 font-mono uppercase tracking-[0.3em]">nexus cryptochain v1.4.2 active</p>
          </div>
        </div>
        
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex flex-col items-end gap-1 px-3 py-1 font-mono text-[9px] uppercase text-gray-500">
            <div className="flex items-center gap-2">
              <Clock className="w-3 h-3" />
              Last Sync: {lastSync.toLocaleTimeString()}
            </div>
            {liveMode && <div className="text-neon-green animate-pulse">Connection: Active</div>}
          </div>

          <div className="relative group">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 group-focus-within:text-neon-green transition-colors" />
            <input
              type="text"
              placeholder="Filter by action, user or resource..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-[#0A0A0A] border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-sm font-mono text-white placeholder:text-gray-600 focus:outline-none focus:border-neon-green/50 w-80 transition-all shadow-inner"
            />
          </div>

          <div className="flex items-center bg-[#0A0A0A] border border-white/10 rounded-xl p-1 gap-1">
            <button
              onClick={() => handleExport('csv')}
              disabled={exporting}
              className="p-2 hover:bg-white/5 rounded-lg text-gray-400 hover:text-white transition-all disabled:opacity-30"
              title="Export CSV"
            >
              <Download className="w-4 h-4" />
            </button>
            <div className="w-px h-4 bg-white/10" />
            <button
              onClick={() => handleExport('json')}
              disabled={exporting}
              className="p-2 hover:bg-white/5 rounded-lg text-gray-400 hover:text-white transition-all disabled:opacity-30"
              title="Export JSON"
            >
              <FileText className="w-4 h-4" />
            </button>
          </div>

          <button
            onClick={handleVerifyTrail}
            disabled={verifying}
            className="flex items-center gap-2 bg-white/5 hover:bg-white/10 text-white border border-white/10 px-5 py-2.5 rounded-xl text-xs font-mono font-bold uppercase transition-all disabled:opacity-50 active:scale-95"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${verifying ? 'animate-spin text-neon-green' : ''}`} />
            Run Integrity Check
          </button>
          
          <button
            onClick={handleBackfill}
            disabled={backfilling}
            className="flex items-center gap-2 bg-neon-green/10 hover:bg-neon-green/20 text-neon-green border border-neon-green/30 px-5 py-2.5 rounded-xl text-xs font-mono font-bold uppercase transition-all disabled:opacity-50 active:scale-95 shadow-lg shadow-neon-green/5"
          >
            <Database className="w-3.5 h-3.5" />
            Backfill Chain
          </button>
        </div>
      </div>

      <div className="bg-[#0A0A0A] border border-white/10 rounded-2xl overflow-hidden shadow-2xl relative">
        {refreshing && !loading && (
          <div className="absolute top-0 left-0 right-0 h-0.5 bg-neon-green/20 overflow-hidden">
            <motion.div 
              animate={{ x: ['-100%', '100%'] }}
              transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
              className="w-1/3 h-full bg-neon-green shadow-[0_0_10px_#39FF14]"
            />
          </div>
        )}
        
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left border-collapse">
            <thead className="text-[10px] text-gray-500 uppercase bg-[#050505] border-b border-white/5 font-mono tracking-[0.2em]">
              <tr>
                <th className="px-8 py-5">Audit Identity</th>
                <th className="px-6 py-5">Actor</th>
                <th className="px-6 py-5 text-center">Protocol Integrity</th>
                <th className="px-6 py-5">Resource Cluster</th>
                <th className="px-6 py-5">Timestamp</th>
                <th className="px-8 py-5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              <AnimatePresence mode='popLayout'>
                {filtered.length > 0 ? filtered.map((log, idx) => (
                  <motion.tr
                    layout
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ delay: idx * 0.02 }}
                    key={log.id}
                    className="hover:bg-white/[0.02] transition-all group cursor-default"
                  >
                    <td className="px-8 py-5">
                      <div className="flex items-center gap-4">
                        <div className="p-2 rounded-lg bg-neon-green/5 text-neon-green border border-neon-green/10 group-hover:border-neon-green/30 transition-all">
                          <Terminal className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="font-mono font-bold text-white uppercase text-xs tracking-wider">{log.action || 'system_op'}</div>
                          <div className="text-[10px] text-gray-600 mt-1 truncate max-w-[240px] group-hover:text-gray-400 transition-colors">
                            {log.description || 'Verified System Operation'}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-5">
                      <div className="flex items-center gap-3">
                        <div className="w-7 h-7 rounded-full bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
                          <User className="w-3.5 h-3.5 text-blue-400" />
                        </div>
                        <span className="text-gray-300 font-mono text-xs">{log.user_email || 'ROOT_SYSTEM'}</span>
                      </div>
                    </td>
                    <td className="px-6 py-5">
                      <div className="flex justify-center">
                        {log.is_verified === true ? (
                          <div className="flex items-center gap-2 px-2 py-1 rounded bg-neon-green/10 border border-neon-green/20 text-neon-green text-[9px] font-bold uppercase">
                            <ShieldCheck className="w-3.5 h-3.5" />
                            Secure
                          </div>
                        ) : log.is_verified === false ? (
                          <div className="flex items-center gap-2 px-2 py-1 rounded bg-red-500/10 border border-red-500/20 text-red-500 text-[9px] font-bold uppercase animate-pulse">
                            <ShieldAlert className="w-3.5 h-3.5" />
                            Tampered
                          </div>
                        ) : (
                          <div className="flex items-center gap-2 px-2 py-1 rounded bg-white/5 border border-white/10 text-gray-500 text-[9px] font-bold uppercase">
                            <History className="w-3.5 h-3.5" />
                            Legacy
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-5">
                      <span className="text-[9px] font-mono px-2.5 py-1 bg-purple-500/5 text-purple-400 rounded-md border border-purple-500/10 uppercase tracking-wider">
                        {log.resource_type || 'GLOBAL'}
                      </span>
                    </td>
                    <td className="px-6 py-5 text-gray-500 font-mono text-xs">
                      <div className="flex items-center gap-2">
                        <Clock className="w-3 h-3 opacity-50" />
                        {log.created_at ? formatDistanceToNow(new Date(log.created_at), { addSuffix: true }) : '—'}
                      </div>
                    </td>
                    <td className="px-8 py-5 text-right">
                      <button 
                        onClick={() => setSelectedLog(log)}
                        className="opacity-0 group-hover:opacity-100 bg-white/5 hover:bg-neon-green hover:text-black text-white p-2 rounded-lg transition-all active:scale-90 border border-white/10 shadow-xl"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </motion.tr>
                )) : (
                  <tr>
                    <td colSpan={6} className="px-8 py-20 text-center">
                      <div className="flex flex-col items-center gap-4 text-gray-600 font-mono">
                        <Search className="w-12 h-12 opacity-20" />
                        <div className="uppercase tracking-[0.3em] text-xs">No records found in current sector</div>
                      </div>
                    </td>
                  </tr>
                )}
              </AnimatePresence>
            </tbody>
          </table>
        </div>
      </div>

      {/* Detail Modal */}
      <AnimatePresence>
        {selectedLog && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90 backdrop-blur-md"
          >
            <motion.div 
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              className="bg-[#050505] border border-white/10 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col shadow-[0_0_50px_rgba(0,0,0,0.5)] border-neon-green/5"
            >
              <div className="p-6 border-b border-white/5 flex items-center justify-between bg-gradient-to-r from-neon-green/5 to-transparent">
                <div className="flex items-center gap-4">
                  <div className="p-2.5 rounded-lg bg-neon-green/10 border border-neon-green/20">
                    <ShieldCheck className="w-5 h-5 text-neon-green" />
                  </div>
                  <div>
                    <h2 className="text-lg font-mono font-bold text-white uppercase tracking-tight">
                      Nexus Evidence Node
                    </h2>
                    <div className="text-[9px] text-gray-500 uppercase tracking-[0.2em]">Verification Protocol v1.4.2</div>
                  </div>
                </div>
                <button 
                  onClick={() => setSelectedLog(null)}
                  className="text-gray-500 hover:text-white font-mono text-[10px] uppercase px-4 py-2 border border-white/10 rounded-lg hover:bg-white/5 transition-all flex items-center gap-2 group"
                >
                  <RotateCcw className="w-3 h-3 group-hover:rotate-180 transition-transform duration-500" />
                  Close
                </button>
              </div>
              
              <div className="p-8 overflow-y-auto space-y-8 font-mono custom-scrollbar">
                <div className="grid grid-cols-2 gap-8">
                  <div className="space-y-1 p-4 bg-white/[0.02] rounded-xl border border-white/5">
                    <label className="text-[9px] text-gray-600 uppercase tracking-widest font-bold">Action Payload</label>
                    <div className="text-neon-green font-bold text-base truncate">{selectedLog.action}</div>
                  </div>
                  <div className="space-y-1 p-4 bg-white/[0.02] rounded-xl border border-white/5">
                    <label className="text-[9px] text-gray-600 uppercase tracking-widest font-bold">Event Epoch</label>
                    <div className="text-white text-base">{new Date(selectedLog.created_at).toLocaleString()}</div>
                  </div>
                </div>

                <div className="space-y-4">
                  <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-[0.3em] flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-neon-green" />
                    Cryptographic Signature
                  </h3>
                  <div className="space-y-3 p-6 bg-black border border-white/5 rounded-2xl relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-30 transition-opacity">
                      <Database className="w-20 h-20 text-neon-green" />
                    </div>
                    <div className="relative z-10 space-y-4">
                      <div>
                        <label className="text-[8px] text-neon-green/50 uppercase block mb-1.5 font-bold">Parent Block Hash</label>
                        <div className="text-[10px] font-mono text-gray-400 break-all bg-[#050505] p-3 rounded-xl border border-white/5">
                          {selectedLog.previous_hash || 'ROOT_GENESIS_BLOCK_0000'}
                        </div>
                      </div>
                      <div>
                        <label className="text-[8px] text-neon-green/50 uppercase block mb-1.5 font-bold">Current Node Signature</label>
                        <div className="text-[10px] font-mono text-neon-green break-all bg-neon-green/5 p-3 rounded-xl border border-neon-green/20">
                          {selectedLog.current_hash || 'UNSIGNED_LEGACY_DATA'}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <label className="text-[10px] text-gray-500 uppercase font-bold tracking-widest">Metadata context</label>
                    <button 
                      onClick={() => {
                        navigator.clipboard.writeText(JSON.stringify(selectedLog.metadata, null, 2));
                        toast.success('Metadata copied to clipboard');
                      }}
                      className="text-[9px] text-neon-green hover:underline uppercase"
                    >
                      Copy JSON
                    </button>
                  </div>
                  <pre className="bg-[#050505] border border-white/5 rounded-2xl p-6 text-[11px] text-neon-green/80 overflow-x-auto leading-relaxed shadow-inner max-h-[300px] custom-scrollbar">
                    {JSON.stringify(selectedLog.metadata, null, 2)}
                  </pre>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function AuditLogsSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-20 bg-card-bg border border-card-border rounded-lg" />
      <div className="flex justify-between items-center">
        <div className="h-10 w-48 bg-card-bg rounded-lg" />
        <div className="flex gap-2">
          <div className="h-10 w-24 bg-card-bg rounded-lg" />
          <div className="h-10 w-24 bg-card-bg rounded-lg" />
        </div>
      </div>
      <div className="space-y-2">
        {[1, 2, 3, 4, 5].map(i => (
          <div key={i} className="h-16 bg-card-bg border border-card-border rounded-lg opacity-50" style={{ opacity: 1 - (i * 0.1) }} />
        ))}
      </div>
    </div>
  );
}
