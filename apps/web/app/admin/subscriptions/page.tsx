'use client';

import { useEffect, useState } from 'react';
import { adminListSubscriptions } from '@/lib/api';
import { 
  CreditCard, Shield, Calendar, Search, Filter, 
  ExternalLink, CheckCircle2, XCircle, Clock, 
  User, Globe, ArrowRight, RefreshCcw
} from 'lucide-react';
import { toast } from 'sonner';

export default function SubscriptionsManagement() {
  const [subscriptions, setSubscriptions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    setLoading(true);
    try {
      const data = await adminListSubscriptions();
      setSubscriptions(data);
    } catch {
      toast.error("Failed to load subscriptions");
    } finally {
      setLoading(false);
    }
  }

  const filtered = subscriptions.filter(s => 
    s.workspace_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    s.owner_email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    s.stripe_subscription_id?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) return (
    <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
      <div className="relative">
        <div className="w-16 h-16 border-4 border-purple-500/10 border-t-purple-500 rounded-full animate-spin" />
        <div className="absolute inset-0 bg-purple-500/20 blur-xl animate-pulse rounded-full" />
      </div>
      <p className="text-purple-400 font-mono text-sm tracking-[0.2em] uppercase animate-pulse">Scanning Active Contracts...</p>
    </div>
  );

  return (
    <div className="max-w-[1200px] mx-auto space-y-10 pb-20">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-8 border-b border-white/5 pb-8">
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-purple-500/10 rounded-2xl border border-purple-500/20 shadow-[0_0_20px_-5px_rgba(168,85,247,0.3)]">
              <Shield className="text-purple-400 w-8 h-8" />
            </div>
            <div>
              <h1 className="text-4xl font-mono font-black text-white tracking-tighter uppercase italic">
                Active <span className="text-purple-400">Subscriptions</span>
              </h1>
              <div className="flex items-center gap-2 mt-1">
                <div className="w-2 h-2 rounded-full bg-purple-500 animate-pulse" />
                <p className="text-gray-500 font-mono text-[10px] uppercase tracking-[0.3em]">Platform Revenue & Contract Integrity</p>
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
            <button 
                onClick={loadData}
                className="p-4 bg-[#0d0d0e] border border-white/5 rounded-2xl text-gray-500 hover:text-purple-400 hover:border-purple-500/30 transition-all group"
            >
                <RefreshCcw className="w-5 h-5 group-active:rotate-180 transition-transform duration-500" />
            </button>
            <div className="bg-[#0d0d0e] border border-white/5 rounded-2xl px-6 py-4 flex items-center gap-4">
                <div>
                    <div className="text-[10px] text-gray-500 uppercase font-mono tracking-widest text-right">Active Contracts</div>
                    <div className="text-2xl font-mono font-black text-white leading-none mt-1 text-right">{subscriptions.length}</div>
                </div>
            </div>
        </div>
      </div>

      {/* Control Bar */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="relative flex-1 group">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600 group-focus-within:text-purple-400 transition-colors" />
          <input 
            placeholder="FILTER BY WORKSPACE, EMAIL OR STRIPE ID..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="w-full bg-[#0d0d0e] border border-white/5 rounded-2xl pl-12 pr-4 py-4 text-xs text-white font-mono uppercase tracking-widest focus:border-purple-400/50 outline-none transition-all"
          />
        </div>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 gap-4">
        {filtered.map((sub) => (
          <div key={sub.id} className="group bg-[#0d0d0e]/60 border border-white/[0.03] hover:border-purple-500/30 rounded-3xl p-6 transition-all">
            <div className="flex flex-col lg:flex-row gap-8 lg:items-center">
              
              {/* Workspace Info */}
              <div className="flex items-center gap-4 min-w-[300px]">
                <div className="w-12 h-12 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                  <Globe className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-lg font-mono font-bold text-white group-hover:text-purple-400 transition-colors uppercase tracking-tight">{sub.workspace_name}</h3>
                  <div className="flex items-center gap-2 text-[10px] text-gray-500 font-mono">
                    <User className="w-3 h-3" />
                    {sub.owner_email}
                  </div>
                </div>
              </div>

              {/* Plan Info */}
              <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-6">
                <div className="space-y-1">
                  <span className="text-[10px] font-mono text-gray-600 uppercase tracking-widest">Active Tier</span>
                  <div className="flex items-center gap-2">
                    <Shield className="w-3.5 h-3.5 text-neon-green" />
                    <span className="text-sm font-mono font-bold text-white uppercase">{sub.plan?.display_name}</span>
                  </div>
                </div>
                
                <div className="space-y-1">
                  <span className="text-[10px] font-mono text-gray-600 uppercase tracking-widest">Status</span>
                  <div className="flex items-center gap-2">
                    {sub.status === 'active' ? (
                      <div className="flex items-center gap-1.5 text-emerald-400 font-mono text-xs font-bold uppercase tracking-tighter">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Healthy
                      </div>
                    ) : (
                      <div className="flex items-center gap-1.5 text-amber-400 font-mono text-xs font-bold uppercase tracking-tighter">
                        <Clock className="w-3.5 h-3.5" />
                        {sub.status}
                      </div>
                    )}
                  </div>
                </div>

                <div className="space-y-1">
                  <span className="text-[10px] font-mono text-gray-600 uppercase tracking-widest">Billing Period</span>
                  <div className="text-xs font-mono text-gray-400 flex items-center gap-1.5">
                    <Calendar className="w-3 h-3" />
                    {new Date(sub.current_period_end).toLocaleDateString()}
                  </div>
                </div>

                <div className="space-y-1">
                  <span className="text-[10px] font-mono text-gray-600 uppercase tracking-widest">Cycle</span>
                  <div className="text-xs font-mono text-gray-400 uppercase tracking-widest">
                    {sub.billing_cycle}
                  </div>
                </div>
              </div>

              {/* Stripe Details */}
              <div className="flex items-center gap-4 border-l border-white/5 pl-8">
                <div className="text-right">
                  <div className="text-[9px] font-mono text-gray-600 uppercase">Stripe Protocol ID</div>
                  <code className="text-[10px] font-mono text-gray-400 bg-white/5 px-2 py-0.5 rounded border border-white/5 truncate max-w-[150px] block">
                    {sub.stripe_subscription_id || 'LOCAL_OVERRIDE'}
                  </code>
                </div>
                <button className="p-3 bg-white/5 border border-white/10 rounded-xl text-gray-500 hover:text-white hover:bg-white/10 transition-all">
                  <ExternalLink className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        ))}

        {filtered.length === 0 && (
          <div className="p-32 text-center border border-dashed border-white/10 rounded-[3rem] bg-white/[0.01]">
            <XCircle className="w-16 h-16 text-gray-700 mx-auto mb-6" />
            <h2 className="text-2xl font-mono font-black text-white tracking-tighter uppercase italic">No Active Contracts</h2>
            <p className="text-gray-500 font-mono text-sm mt-2 uppercase tracking-widest opacity-60">The subscription registry is currently quiet.</p>
          </div>
        )}
      </div>
    </div>
  );
}
