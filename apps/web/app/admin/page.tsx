'use client';

import { useEffect, useState } from 'react';
import { adminGetStats } from '@/lib/api';
import { 
  Users, Shield, Terminal, AlertTriangle, Activity, 
  Globe, ShoppingBag, ShieldCheck, CreditCard, 
  Settings, Database, Zap, Cpu, Lock, 
  ChevronRight, ArrowUpRight, BarChart3, ShieldAlert
} from 'lucide-react';
import { motion } from 'framer-motion';

export default function AdminDashboard() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadStats() {
      try {
        const data = await adminGetStats();
        setStats(data);
      } catch (error) {
        console.error("Failed to load admin stats:", error);
      } finally {
        setLoading(false);
      }
    }
    loadStats();
  }, []);

  if (loading) return (
    <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
      <div className="relative">
        <div className="w-16 h-16 border-4 border-neon-green/10 border-t-neon-green rounded-full animate-spin" />
        <div className="absolute inset-0 bg-neon-green/20 blur-xl animate-pulse rounded-full" />
      </div>
      <p className="text-neon-green font-mono text-sm tracking-[0.2em] uppercase animate-pulse font-black">Decrypting Nexus Data...</p>
    </div>
  );

  const isIntegrityCompromised = stats?.audit_log_integrity === 'COMPROMISED';

  const statCards = [
    { title: 'Total Users', value: stats?.total_users, icon: Users, color: 'text-blue-500', bg: 'bg-blue-500/10' },
    { title: 'Active Workspaces', value: stats?.total_workspaces, icon: Globe, color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
    { title: 'Total Scans', value: stats?.total_scans, icon: Terminal, color: 'text-neon-green', bg: 'bg-neon-green/10' },
    { title: 'Findings Detected', value: stats?.total_findings, icon: AlertTriangle, color: 'text-red-500', bg: 'bg-red-500/10' },
    { title: 'Active (24h)', value: stats?.active_users_24h, icon: Activity, color: 'text-purple-500', bg: 'bg-purple-500/10' },
  ];

  const adminModules = [
    {
      group: "Core Infrastructure",
      icon: Database,
      color: "text-blue-400",
      description: "Manage system-wide data, users, and workspace environments.",
      links: [
        { name: "User Management", href: "/admin/users", icon: Users },
        { name: "Workspace Registry", href: "/admin/workspaces", icon: Globe },
        { name: "System Health", href: "/admin/system", icon: Activity },
        { 
          name: "Audit Trail", 
          href: "/admin/audit-logs", 
          icon: ShieldCheck,
          status: stats?.audit_log_integrity === 'COMPROMISED' ? 'TAMPERED' : 'SECURE',
          statusColor: stats?.audit_log_integrity === 'COMPROMISED' ? 'text-red-500' : 'text-neon-green'
        },
      ]
    },
    {
      group: "Security Engine",
      icon: Cpu,
      color: "text-neon-green",
      description: "Configure scanning algorithms, strategies, and discovery logs.",
      links: [
        { name: "Scan Strategies", href: "/admin/strategies", icon: Zap },
        { name: "Global Scan Queue", href: "/admin/scans", icon: Terminal },
        { name: "CT Log Monitoring", href: "/admin/ct-logs", icon: Lock },
        { name: "System Settings", href: "/admin/settings", icon: Settings },
      ]
    },
    {
      group: "Economy & Billing",
      icon: CreditCard,
      color: "text-purple-400",
      description: "Control subscription tiers, quotas, and marketplace offerings.",
      links: [
        { name: "Subscription Tiers", href: "/admin/plans", icon: Shield },
        { name: "Quota Management", href: "/admin/quotas", icon: BarChart3 },
        { name: "Active Subscriptions", href: "/admin/subscriptions", icon: CreditCard },
        { name: "Marketplace CRUD", href: "/admin/marketplace", icon: ShoppingBag },
        { name: "Bounty Programs", href: "/admin/bounty", icon: ShieldCheck },
      ]
    }
  ];

  return (
    <div className="max-w-[1400px] mx-auto space-y-12 pb-20 animate-in fade-in duration-700">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 pb-4 border-b border-white/5 relative">
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-neon-green/10 rounded-xl border border-neon-green/20 relative">
              <Shield className="text-neon-green w-8 h-8" />
              <div className="absolute inset-0 bg-neon-green/20 blur-lg rounded-full" />
            </div>
            <div>
              <h1 className="text-4xl font-mono font-black text-white tracking-tighter uppercase italic">
                Nexus <span className="text-neon-green">Control</span> Center
              </h1>
              <div className="flex items-center gap-2 mt-1">
                <div className="w-2 h-2 rounded-full bg-neon-green animate-pulse" />
                <p className="text-gray-500 font-mono text-[10px] uppercase tracking-[0.3em]">Root-level access confirmed • Multi-cluster orchestration active</p>
              </div>
            </div>
          </div>
        </div>
        <div className="flex gap-4">
           <div className="px-6 py-3 bg-card-bg border border-card-border rounded-xl font-mono text-[10px] tracking-widest text-gray-400 uppercase flex items-center gap-3">
             <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]" />
             Cluster Status: Optimal
           </div>
        </div>
      </div>

      {/* Security Alert Banner */}
      {isIntegrityCompromised && (
        <motion.div 
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-red-500/10 border border-red-500/30 rounded-3xl p-6 flex flex-col md:flex-row items-center gap-6 relative overflow-hidden group"
        >
          <div className="absolute inset-0 bg-red-500/5 animate-pulse" />
          <div className="relative p-4 bg-red-500/20 rounded-2xl border border-red-500/30">
            <ShieldAlert className="text-red-500 w-10 h-10" />
          </div>
          <div className="relative flex-grow space-y-2">
            <h2 className="text-xl font-mono font-black text-white uppercase italic">Critical: Audit Chain Tamper Detected</h2>
            <p className="text-gray-400 font-mono text-xs leading-relaxed">
              The cryptographic integrity of the platform audit logs has been compromised. One or more entries have failed the SHA-256 chain verification. 
              Immediate inspection of the <a href="/admin/audit-logs" className="text-red-500 underline underline-offset-4 font-bold">Audit Trail</a> is required.
            </p>
          </div>
          <a 
            href="/admin/audit-logs"
            className="relative px-8 py-4 bg-red-600 text-white rounded-xl font-mono font-black text-xs uppercase tracking-widest hover:bg-red-500 transition-all shadow-xl shadow-red-600/20"
          >
            Investigate Breach
          </a>
        </motion.div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        {statCards.map((card, i) => (
          <motion.div 
            key={i}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="group relative bg-[#0d0d0e]/60 backdrop-blur-xl border border-white/[0.03] rounded-3xl p-6 transition-all hover:border-white/10 hover:translate-y-[-4px]"
          >
            <div className="flex items-center justify-between mb-4">
              <div className={`p-2.5 rounded-xl ${card.bg} ${card.color} border border-white/[0.05]`}>
                <card.icon className="w-5 h-5" />
              </div>
              <ArrowUpRight className="w-4 h-4 text-gray-700 group-hover:text-neon-green transition-colors" />
            </div>
            <div className="space-y-1">
              <h3 className="text-[10px] font-mono text-gray-500 uppercase tracking-[0.2em]">{card.title}</h3>
              <div className="text-3xl font-mono font-black text-white">{card.value?.toLocaleString() || '0'}</div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Management Modules */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {adminModules.map((module, idx) => (
          <motion.div 
            key={idx}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.3 + (idx * 0.1) }}
            className="bg-[#0d0d0e]/40 border border-white/[0.05] rounded-[2.5rem] p-8 flex flex-col h-full hover:border-white/[0.08] transition-all relative overflow-hidden group"
          >
            {/* Ambient Background Glow */}
            <div className={`absolute -top-24 -right-24 w-48 h-48 blur-[100px] rounded-full opacity-10 group-hover:opacity-20 transition-opacity ${module.color.replace('text', 'bg')}`} />

            <div className="flex items-center gap-4 mb-6">
              <div className={`p-4 rounded-2xl bg-black/40 border border-white/5 ${module.color}`}>
                <module.icon className="w-8 h-8" />
              </div>
              <div>
                <h2 className="text-xl font-mono font-black text-white uppercase italic tracking-tighter">{module.group}</h2>
                <div className="h-0.5 w-12 bg-current opacity-30 mt-1" />
              </div>
            </div>

            <p className="text-gray-500 font-mono text-xs leading-relaxed mb-8 flex-grow">
              {module.description}
            </p>

            <div className="grid grid-cols-1 gap-3">
              {module.links.map((link: any, lIdx) => (
                <a 
                  key={lIdx} 
                  href={link.href}
                  className="group/link flex items-center justify-between p-4 bg-white/[0.02] border border-white/[0.03] rounded-2xl hover:bg-white/[0.05] hover:border-white/10 transition-all active:scale-[0.98]"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-xl bg-black flex items-center justify-center text-gray-500 group-hover/link:text-white transition-colors">
                      <link.icon className="w-4 h-4" />
                    </div>
                    <div className="flex flex-col">
                      <span className="text-sm font-mono font-bold text-gray-400 group-hover/link:text-white transition-colors">{link.name}</span>
                      {link.status && (
                        <span className={`text-[9px] font-mono font-black uppercase ${link.statusColor}`}>{link.status}</span>
                      )}
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-gray-700 group-hover/link:text-neon-green transition-all translate-x-[-4px] group-hover/link:translate-x-0" />
                </a>
              ))}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Quick Terminal Access */}
      <div className="relative overflow-hidden bg-black border border-white/5 rounded-[3rem] p-10 group">
        <div className="absolute inset-0 bg-gradient-to-r from-neon-green/[0.02] to-transparent" />
        <div className="relative flex flex-col md:flex-row items-center justify-between gap-8">
          <div className="space-y-4 max-w-2xl">
            <div className="flex items-center gap-3 text-neon-green font-mono text-[10px] uppercase tracking-[0.4em]">
              <div className="w-2 h-2 rounded-full bg-neon-green shadow-[0_0_8px_rgba(57,255,20,0.8)]" />
              Operational Efficiency
            </div>
            <h2 className="text-3xl font-mono font-black text-white uppercase italic tracking-tight">
              Rapid System <span className="text-neon-green">Maintenance</span>
            </h2>
            <p className="text-gray-500 font-mono text-sm leading-relaxed">
              Trigger global cache purges, repair data inconsistencies, or synchronize plugin registries across the entire distributed cluster in one action.
            </p>
          </div>
          <a 
            href="/admin/system"
            className="px-10 py-5 bg-white text-black rounded-2xl font-mono font-black text-sm uppercase tracking-widest hover:bg-neon-green transition-all shadow-2xl hover:shadow-neon-green/30 flex items-center gap-3 whitespace-nowrap"
          >
            Terminal Access <ArrowUpRight className="w-5 h-5" />
          </a>
        </div>
      </div>
    </div>
  );
}
