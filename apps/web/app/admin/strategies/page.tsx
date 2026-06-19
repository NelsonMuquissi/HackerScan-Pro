'use client';

import { useEffect, useState } from 'react';
import { adminListStrategies, adminUpdateStrategy } from '@/lib/api';
import { 
  Shield, CheckCircle, XCircle, Lock, Tag, 
  Settings2, Activity, Globe, Zap, Info,
  AlertCircle, Save, X, RefreshCw, ChevronRight, ShieldCheck
} from 'lucide-react';
import { toast } from 'sonner';
import { HackerModal } from '@/components/ui/HackerModal';
import { adminRunMaintenance } from '@/lib/api';

export default function StrategiesManagement() {
  const [strategies, setStrategies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingStrategy, setEditingStrategy] = useState<any>(null);
  const [isUpdating, setIsUpdating] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

  useEffect(() => { 
    loadStrategies(); 
  }, []);

  async function loadStrategies() {
    try {
      const data = await adminListStrategies();
      setStrategies(data);
    } catch {
      toast.error("Failed to load scan strategies");
    } finally {
      setLoading(false);
    }
  }

  async function handleToggleStatus(strategy: any) {
    try {
      await adminUpdateStrategy(strategy.id, { is_active: !strategy.is_active });
      toast.success(`Strategy "${strategy.name}" ${strategy.is_active ? 'disabled' : 'enabled'}.`);
      loadStrategies();
    } catch {
      toast.error("Failed to update status");
    }
  }

  async function handleUpdateStrategy(e: React.FormEvent) {
    e.preventDefault();
    if (!editingStrategy) return;

    setIsUpdating(true);
    try {
      await adminUpdateStrategy(editingStrategy.id, {
        name: editingStrategy.name,
        description: editingStrategy.description,
        slug: editingStrategy.slug,
        requires_auth: editingStrategy.requires_auth,
        plans: editingStrategy.plans,
      });
      toast.success("Strategy updated successfully");
      setEditingStrategy(null);
      loadStrategies();
    } catch {
      toast.error("Failed to update strategy details");
    } finally {
      setIsUpdating(false);
    }
  }

  async function handleSyncPlugins() {
    setIsSyncing(true);
    try {
      const result = await adminRunMaintenance('sync_plugins');
      toast.success(result?.message || "Plugin registry synced successfully.");
      loadStrategies();
    } catch {
      toast.error("Failed to sync plugin registry");
    } finally {
      setIsSyncing(false);
    }
  }

  const active = strategies.filter(s => s.is_active).length;

  if (loading) return (
    <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
      <div className="w-12 h-12 border-4 border-neon-green/20 border-t-neon-green rounded-full animate-spin"></div>
      <p className="text-neon-green font-mono animate-pulse">Loading scan strategies...</p>
    </div>
  );

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl font-mono font-bold text-white tracking-tight flex items-center gap-3">
            <Activity className="w-10 h-10 text-neon-green" />
            Scan Strategies
          </h1>
          <p className="text-gray-500 font-mono text-sm mt-1">
            CORE ENGINE / PLUGIN CONFIGURATION
          </p>
        </div>
        
        <div className="flex items-center gap-4 bg-card-bg/50 backdrop-blur-xl border border-card-border p-1.5 rounded-xl">
          <button
            onClick={handleSyncPlugins}
            disabled={isSyncing}
            className="px-4 py-2 bg-purple-500/10 text-purple-400 hover:bg-purple-500/20 rounded-lg transition-all border border-purple-500/20 font-mono text-xs flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
            SYNC REGISTRY
          </button>
          <div className="w-px h-10 bg-card-border" />
          <div className="flex flex-col px-4 py-1 text-center">
            <span className="text-[10px] text-gray-500 font-mono uppercase tracking-wider">Active</span>
            <span className="text-xl font-bold text-emerald-500 font-mono">{active}</span>
          </div>
          <div className="w-px h-10 bg-card-border" />
          <div className="flex flex-col px-4 py-1 text-center">
            <span className="text-[10px] text-gray-500 font-mono uppercase tracking-wider">Total</span>
            <span className="text-xl font-bold text-white font-mono">{strategies.length}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {strategies.map(strategy => (
          <div
            key={strategy.id}
            className={`group bg-card-bg/40 backdrop-blur-md border rounded-2xl p-6 transition-all relative overflow-hidden flex flex-col h-full ${
              strategy.is_active
                ? 'border-card-border hover:border-neon-green/30 hover:shadow-[0_0_30px_rgba(57,255,20,0.05)]'
                : 'border-card-border/50 opacity-60 grayscale hover:grayscale-0 transition-all'
            }`}
          >
            {/* Active Glow */}
            {strategy.is_active && (
              <div className="absolute -top-12 -right-12 w-24 h-24 bg-neon-green/5 blur-3xl rounded-full transition-all group-hover:bg-neon-green/10" />
            )}

            <div className="flex items-start justify-between gap-4 mb-4">
              <div className={`p-3 rounded-xl bg-background border ${strategy.is_active ? 'border-neon-green/20 text-neon-green' : 'border-card-border text-gray-500'}`}>
                <Shield className="w-6 h-6" />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setEditingStrategy(strategy)}
                  className="p-2 bg-background border border-card-border rounded-lg text-gray-500 hover:text-white transition-all"
                  title="Configure"
                >
                  <Settings2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleToggleStatus(strategy)}
                  className={`p-2 rounded-lg border transition-all ${
                    strategy.is_active
                      ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-500 hover:bg-red-500/10 hover:border-red-500/20 hover:text-red-500'
                      : 'bg-gray-500/10 border-gray-500/20 text-gray-500 hover:bg-neon-green/10 hover:border-neon-green/20 hover:text-neon-green'
                  }`}
                  title={strategy.is_active ? 'Deactivate' : 'Activate'}
                >
                  {strategy.is_active ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div className="mb-4 flex-grow">
              <h3 className="text-lg font-mono font-bold text-white mb-2 group-hover:text-neon-green transition-colors">
                {strategy.name}
              </h3>
              <p className="text-xs text-gray-500 font-mono leading-relaxed line-clamp-3">
                {strategy.description || 'Global scan engine strategy with optimized discovery patterns.'}
              </p>
            </div>

            <div className="pt-4 border-t border-card-border/50 flex flex-wrap gap-2">
              <div className="flex items-center gap-1 px-2 py-1 bg-background border border-card-border rounded-lg text-[10px] font-mono text-gray-400">
                <Tag className="w-3 h-3" /> {strategy.slug}
              </div>
              {strategy.version && (
                <div className="px-2 py-1 bg-background border border-card-border rounded-lg text-[10px] font-mono text-gray-400">
                  v{strategy.version}
                </div>
              )}
              {strategy.requires_auth && (
                <div className="flex items-center gap-1 px-2 py-1 bg-amber-500/10 border border-amber-500/20 rounded-lg text-[10px] font-mono text-amber-500">
                  <Lock className="w-3 h-3" /> SECURE
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <HackerModal
        open={!!editingStrategy}
        onClose={() => setEditingStrategy(null)}
        title="Strategy Configuration"
        description={`Adjusting engine parameters: ${editingStrategy?.name}`}
        variant="primary"
        footer={
          <div className="flex gap-4 w-full">
            <button
              type="button"
              onClick={() => setEditingStrategy(null)}
              className="flex-1 px-6 py-4 bg-white/5 border border-white/10 rounded-xl text-gray-400 hover:text-white transition-all font-mono text-xs uppercase tracking-widest"
            >
              Abort
            </button>
            <button
              onClick={handleUpdateStrategy}
              disabled={isUpdating}
              className="flex-[2] px-8 py-4 bg-neon-green text-black rounded-xl font-mono font-black text-xs uppercase tracking-widest hover:bg-neon-green/90 transition-all shadow-[0_0_20px_rgba(57,255,20,0.3)] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <Save className="w-4 h-4" />
              {isUpdating ? 'Executing...' : 'Deploy Strategy'}
            </button>
          </div>
        }
      >
        {editingStrategy && (
          <div className="space-y-8">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="md:col-span-2 space-y-4">
                <label className="text-[10px] font-mono text-gray-500 uppercase tracking-[0.2em] block">Strategy Identity</label>
                <div className="relative group">
                  <Shield className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600 group-focus-within:text-neon-green transition-colors" />
                  <input
                    type="text"
                    value={editingStrategy.name}
                    onChange={(e) => setEditingStrategy({ ...editingStrategy, name: e.target.value })}
                    className="w-full bg-[#0d0d0e] border border-white/5 rounded-xl pl-12 pr-4 py-4 text-white font-mono text-sm focus:border-neon-green/50 outline-none transition-all shadow-inner"
                  />
                </div>
              </div>

              <div className="space-y-4">
                <label className="text-[10px] font-mono text-gray-500 uppercase tracking-[0.2em] block">System Identifier (Slug)</label>
                <div className="relative group">
                  <Tag className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600 group-focus-within:text-purple-400 transition-colors" />
                  <input
                    type="text"
                    value={editingStrategy.slug}
                    onChange={(e) => setEditingStrategy({ ...editingStrategy, slug: e.target.value })}
                    className="w-full bg-[#0d0d0e] border border-white/5 rounded-xl pl-12 pr-4 py-4 text-white font-mono text-sm focus:border-purple-500/50 outline-none transition-all shadow-inner"
                  />
                </div>
              </div>

              <div className="space-y-4">
                <label className="text-[10px] font-mono text-gray-500 uppercase tracking-[0.2em] block">Baseline Authorization</label>
                <div className="relative group">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600 pointer-events-none" />
                  <select
                    value={editingStrategy.plans || 'all'}
                    onChange={(e) => setEditingStrategy({ ...editingStrategy, plans: e.target.value })}
                    className="w-full bg-[#0d0d0e] border border-white/5 rounded-xl pl-12 pr-10 py-4 text-white font-mono text-sm focus:border-blue-400/50 outline-none transition-all appearance-none shadow-inner"
                  >
                    <option value="all">ALL ACCESS PROTOCOL</option>
                    <option value="pro">PRO & ENTERPRISE ONLY</option>
                    <option value="enterprise">ENTERPRISE RESTRICTED</option>
                  </select>
                  <ChevronRight className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600 rotate-90 pointer-events-none" />
                </div>
              </div>

              <div className="md:col-span-2 space-y-4">
                <label className="text-[10px] font-mono text-gray-500 uppercase tracking-[0.2em] block">Operational Objectives</label>
                <textarea
                  value={editingStrategy.description}
                  onChange={(e) => setEditingStrategy({ ...editingStrategy, description: e.target.value })}
                  rows={4}
                  className="w-full bg-[#0d0d0e] border border-white/5 rounded-xl p-6 text-white font-mono text-sm focus:border-neon-green/50 outline-none transition-all shadow-inner resize-none leading-relaxed"
                  placeholder="Define strategy objectives and engine behavior..."
                />
              </div>

              <div className="md:col-span-2 flex items-center justify-between p-6 bg-white/[0.02] border border-white/5 rounded-2xl group overflow-hidden relative">
                <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none group-hover:opacity-10 transition-opacity">
                   <ShieldCheck className="w-24 h-24" />
                </div>
                <div className="space-y-1 relative z-10">
                  <h4 className="text-[11px] font-mono font-black text-white uppercase tracking-widest">Authentication Perimeter</h4>
                  <p className="text-[10px] text-gray-500 font-mono uppercase tracking-tighter">Enable forced credential validation for this engine strategy.</p>
                </div>
                <button
                  type="button"
                  onClick={() => setEditingStrategy({ ...editingStrategy, requires_auth: !editingStrategy.requires_auth })}
                  className={`w-14 h-7 rounded-full transition-all relative z-10 shadow-lg ${editingStrategy.requires_auth ? 'bg-neon-green' : 'bg-gray-800/50 border border-white/5'}`}
                >
                  <div className={`absolute top-1 w-5 h-5 rounded-full bg-white transition-all shadow-md ${editingStrategy.requires_auth ? 'left-8' : 'left-1'}`} />
                </button>
              </div>
            </div>
          </div>
        )}
      </HackerModal>
    </div>
  );
}
