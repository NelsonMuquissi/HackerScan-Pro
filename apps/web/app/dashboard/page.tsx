'use client';

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { MetricCard } from '@/components/dashboard/MetricCard';
import { RecentScans } from '@/components/dashboard/RecentScans';
import { SeverityHeatmap } from '@/components/dashboard/SeverityHeatmap';
import { TerminalOutput } from '@/components/TerminalOutput';
import { Activity, ShieldAlert, Bug, Target, Terminal, Zap, ShieldCheck, Lock, Loader2, ExternalLink } from 'lucide-react';
import { startScan, getDashboardStats, listPlugins, type DashboardStats } from '@/lib/api';
import Link from 'next/link';

export default function DashboardPage() {
  const searchParams = useSearchParams();
  const scanQueryParam = searchParams.get('scan');
  
   const [activeScanId, setActiveScanId] = useState<string | null>(scanQueryParam);
  const [targetUrl, setTargetUrl] = useState('');
  const [scanType, setScanType] = useState('quick');
  const [availablePlugins, setAvailablePlugins] = useState<any[]>([]);
  const [selectedPlugins, setSelectedPlugins] = useState<string[]>([]);
  const [isScanning, setIsScanning] = useState(false);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [statsError, setStatsError] = useState(false);

   // Initial stats and plugins load
  useEffect(() => {
    getDashboardStats()
      .then(setStats)
      .catch(() => setStatsError(true));
      
    listPlugins()
      .then(setAvailablePlugins)
      .catch(console.error);
  }, []);

  // Auto-refresh stats every 5s while a scan is active so Recent Scans and counters update live
  useEffect(() => {
    if (!activeScanId) return;
    const interval = setInterval(() => {
      getDashboardStats().then(setStats).catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, [activeScanId]);

  // Refresh stats after a scan completes
  const refreshStats = () => {
    getDashboardStats().then(setStats).catch(() => {});
  };

   const handleStartScan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetUrl) return;
    if (scanType === 'custom' && selectedPlugins.length === 0) {
      alert('Select at least one plugin for custom scan.');
      return;
    }

    try {
      setIsScanning(true);
      // For custom scans, we send 'full' as scanType if it requires deep inspection, 
      // or just 'custom'. The backend handles prioritized plugin_ids.
      const res = await startScan(targetUrl, scanType, undefined, selectedPlugins);
      setActiveScanId(res.scan_id);
      // Refresh dashboard stats after starting a scan
      setTimeout(refreshStats, 2000);
    } catch (error: any) {
      console.error('Failed to start scan', error);
      
      if (error.status === 402) {
        alert('PREMIUM MODULE REQUIRED\nThis tactical strategy is locked. Redirecting to Marketplace...');
        setTimeout(() => window.location.href = '/dashboard/marketplace', 3000);
      } else {
        alert(error?.message || 'Initialization Failed');
      }
    } finally {
      setIsScanning(false);
    }
  };

  const togglePlugin = (pluginId: string) => {
    setSelectedPlugins(prev => 
      prev.includes(pluginId) 
        ? prev.filter(p => p !== pluginId) 
        : [...prev, pluginId]
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <h1 className="text-2xl font-mono font-bold text-foreground">Dashboard</h1>
        
        <div className="flex flex-col gap-4">
          <form onSubmit={handleStartScan} className="flex flex-col md:flex-row gap-2">
            <div className="relative flex-1">
              <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none text-gray-500">
                <Target className="w-4 h-4" />
              </div>
              <input
                type="url"
                value={targetUrl}
                onChange={(e) => setTargetUrl(e.target.value)}
                placeholder="PROBE TARGET (URL/IP)..."
                required
                className="bg-[#0a0a0a] border border-white/5 rounded-lg pl-10 pr-4 py-3 font-mono text-xs focus:outline-none focus:border-neon-green/50 text-foreground w-full transition-all hover:bg-[#0d0d0d]"
              />
            </div>

            <div className="flex gap-2">
              <select
                value={scanType}
                onChange={(e) => setScanType(e.target.value)}
                className="bg-[#0a0a0a] border border-white/5 rounded-lg px-4 py-3 font-mono text-[10px] focus:outline-none focus:border-neon-green/50 text-gray-400 uppercase tracking-widest"
              >
                 <option value="quick">QUICK SCOPE</option>
                <option value="full">FULL SPECTRUM</option>
                <option value="vuln">VULN RESEARCH</option>
                <option value="recon">RECON & DISCOVERY</option>
                <option value="custom">CUSTOM PLUGINS</option>
                <option value="ad_audit">AD TACTICAL [PREMIUM]</option>
                <option value="k8s_security">K8S HARDENING [PREMIUM]</option>
                <option value="sap_audit">SAP ECOSYSTEM [PREMIUM]</option>
              </select>

              <button 
                type="submit" 
                disabled={isScanning}
                className="flex items-center gap-2 bg-neon-green text-black font-bold font-mono px-6 py-3 rounded-lg hover:bg-[#00cc00] transition-all disabled:opacity-50 text-[10px] uppercase tracking-widest"
              >
                {isScanning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                {isScanning ? 'ENQUEUING...' : 'INITIALIZE'}
              </button>
            </div>
          </form>

          {scanType === 'custom' && (
            <div className="bg-[#0a0a0a] border border-white/5 rounded-lg p-4 animate-in fade-in slide-in-from-top-2">
              <h3 className="text-[10px] font-mono font-bold text-gray-500 mb-3 uppercase tracking-widest">Select Tactical Modules</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {availablePlugins.length > 0 ? availablePlugins.map(plugin => (
                  <label key={plugin.plugin_id} className={`flex items-center gap-2 p-2 rounded border cursor-pointer transition-all ${
                    selectedPlugins.includes(plugin.plugin_id) 
                      ? 'border-neon-green/50 bg-neon-green/5' 
                      : 'border-white/5 bg-transparent hover:border-white/10'
                  }`}>
                    <input 
                      type="checkbox" 
                      className="hidden"
                      checked={selectedPlugins.includes(plugin.plugin_id)}
                      onChange={() => togglePlugin(plugin.plugin_id)}
                    />
                    <div className={`w-3 h-3 rounded-sm border ${
                      selectedPlugins.includes(plugin.plugin_id) ? 'bg-neon-green border-neon-green' : 'border-gray-600'
                    }`} />
                    <span className={`text-[9px] font-mono uppercase truncate ${
                      selectedPlugins.includes(plugin.plugin_id) ? 'text-neon-green' : 'text-gray-400'
                    }`}>
                      {plugin.name}
                    </span>
                  </label>
                )) : (
                  <p className="text-[10px] font-mono text-gray-600 col-span-full italic">Scanning local strategy directory...</p>
                )}
              </div>
            </div>
          )}
          
          <div className="flex items-center gap-4 text-[9px] font-mono text-gray-600 uppercase tracking-tighter">
            <span className="flex items-center gap-1.5"><ShieldCheck className="w-3 h-3 text-neon-green" /> End-to-end Encrypted</span>
            <span className="flex items-center gap-1.5"><Zap className="w-3 h-3 text-neon-yellow" /> Hardware Accelerated</span>
            <span className="flex items-center gap-1.5"><Lock className="w-3 h-3 text-blue-500" /> ISO 27001 Ready</span>
          </div>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <MetricCard 
          title="Active Scans" 
          value={stats?.active_scans ?? (activeScanId ? 1 : 0)} 
          icon={Activity} 
          color="green" 
        />
        <MetricCard 
          title="Total Vulnerabilities" 
          value={stats?.total_findings ?? 0} 
          icon={Bug} 
          color="red" 
        />
        <MetricCard 
          title="Critical Alerts" 
          value={stats?.critical_count ?? 0} 
          icon={ShieldAlert} 
          color="yellow" 
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SeverityHeatmap 
          critical={stats?.critical_count ?? 0}
          high={stats?.high_count ?? 0}
          medium={stats?.medium_count ?? 0}
          low={stats?.low_count ?? 0}
          info={stats?.info_count ?? 0}
        />
        <RecentScans scans={stats?.recent_scans ?? []} />
      </div>

      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-mono font-bold text-foreground">Live Terminal Output</h2>
          {scanQueryParam && (
            <Link 
              href={`/dashboard/scans/${scanQueryParam}`}
              className="flex items-center gap-2 text-[10px] font-mono font-bold text-neon-green bg-neon-green/10 px-3 py-1.5 rounded border border-neon-green/20 hover:bg-neon-green/20 transition-all uppercase tracking-widest"
            >
              <ExternalLink className="w-3 h-3" />
              View Full Audit Report
            </Link>
          )}
        </div>
        
        {activeScanId ? (
          <TerminalOutput key={activeScanId} scanId={activeScanId} />
        ) : (
          <div className="bg-card-bg border border-card-border rounded-lg p-12 text-center flex flex-col items-center justify-center min-h-[400px]">
            <Terminal className="w-12 h-12 text-gray-500 mb-4" />
            <p className="text-gray-400 font-mono">No active scan selected.</p>
            <p className="text-gray-500 text-sm font-mono mt-2">Enter a target URL and execute a scan to monitor realtime activity.</p>
          </div>
        )}
      </div>
    </div>
  );
}
