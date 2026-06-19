'use client';

import { useEffect, useState } from 'react';
import { adminListWorkspaces, adminUpdateWorkspace, adminDeleteWorkspace, adminListPlans } from '@/lib/api';
import { 
  Globe, Users, CreditCard, Calendar, Shield, Search, 
  Filter, MoreVertical, Edit2, Trash2, ExternalLink,
  ChevronRight, Activity, Zap, Database, Lock, Save,
  ShieldCheck, ArrowUpRight, Mail, AlertTriangle, Cpu
} from 'lucide-react';
import { toast } from 'sonner';
import { formatDistanceToNow } from 'date-fns';
import { motion, AnimatePresence } from 'framer-motion';
import { HackerModal } from '@/components/ui/HackerModal';
import { useConfirm } from '@/hooks/useConfirm';

export default function AdminWorkspacesManagement() {
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [editingWorkspace, setEditingWorkspace] = useState<any>(null);
  const [form, setForm] = useState<any>({});
  const { confirm, state: confirmState, handleConfirm, handleCancel } = useConfirm();

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [wData, pData] = await Promise.all([
        adminListWorkspaces(),
        adminListPlans()
      ]);
      setWorkspaces(wData);
      setPlans(pData);
    } catch (error) {
      toast.error("Failed to synchronize workspace registry");
    } finally {
      setLoading(false);
    }
  }

  const filteredWorkspaces = workspaces.filter(w => 
    w.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    w.owner_email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    w.id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  function openEdit(workspace: any) {
    setEditingWorkspace(workspace);
    setForm({
      name: workspace.name,
      plan: workspace.plan || 'free',
      is_active: workspace.is_active,
      custom_scans_limit: workspace.custom_limits?.scans_per_month || 0,
      custom_targets_limit: workspace.custom_limits?.targets || 0,
    });
  }

  async function handleSave() {
    try {
      const payload = {
        name: form.name,
        plan: form.plan,
        is_active: form.is_active,
        custom_limits: {
          scans_per_month: parseInt(form.custom_scans_limit),
          targets: parseInt(form.custom_targets_limit),
        }
      };
      await adminUpdateWorkspace(editingWorkspace.id, payload);
      toast.success(`Workspace [${form.name}] updated`);
      setEditingWorkspace(null);
      loadData();
    } catch (error: any) {
      toast.error(error.message || "Failed to update workspace");
    }
  }

  async function handleDelete(id: string, name: string) {
    const ok = await confirm({
      title: `Terminate Workspace "${name}"`,
      description: "This will immediately revoke all access, terminate active scans, and purge the workspace context. This action is IRREVERSIBLE.",
      confirmLabel: 'Terminate Context',
      variant: 'danger',
    });
    if (!ok) return;

    try {
      await adminDeleteWorkspace(id);
      toast.success("Workspace context terminated");
      loadData();
    } catch (error: any) {
      toast.error(error.message || "Termination sequence failed");
    }
  }

  if (loading) return (
    <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
      <div className="relative">
        <div className="w-16 h-16 border-4 border-emerald-500/10 border-t-emerald-500 rounded-full animate-spin" />
        <div className="absolute inset-0 bg-emerald-500/20 blur-xl animate-pulse rounded-full" />
      </div>
      <p className="text-emerald-400 font-mono text-sm tracking-[0.2em] uppercase animate-pulse">Scanning Global Clusters...</p>
    </div>
  );

  return (
    <div className="max-w-[1400px] mx-auto space-y-10 pb-20">
      <HackerModal
        open={confirmState.open}
        onClose={handleCancel}
        title={confirmState.title}
        variant="danger"
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
              className="flex-[2] px-8 py-4 bg-red-500 text-black rounded-xl font-mono font-black text-xs uppercase tracking-widest hover:bg-red-400 transition-all shadow-[0_0_20px_rgba(239,68,68,0.3)]"
            >
              Terminate Context
            </button>
          </div>
        }
      >
        <div className="space-y-6">
          <div className="p-6 bg-red-500/5 border border-red-500/10 rounded-2xl">
            <p className="text-gray-400 font-mono text-sm leading-relaxed uppercase italic">
              {confirmState.description}
            </p>
          </div>
          <div className="flex items-center gap-4 p-4 bg-black/40 border border-white/5 rounded-xl">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            <p className="text-[10px] font-mono text-red-400 uppercase tracking-widest">
              Action requires high-level administrative authorization.
            </p>
          </div>
        </div>
      </HackerModal>

      <HackerModal
        open={!!editingWorkspace}
        onClose={() => setEditingWorkspace(null)}
        title="Workspace Configuration"
        description={`Reconfiguring context: ${editingWorkspace?.name}`}
        variant="primary"
        footer={
          <div className="flex gap-4 w-full">
             <button 
              onClick={() => setEditingWorkspace(null)}
              className="flex-1 px-6 py-4 bg-white/5 border border-white/10 rounded-xl text-gray-400 hover:text-white transition-all font-mono text-xs uppercase tracking-widest"
             >
               Discard
             </button>
             <button 
              onClick={handleSave}
              className="flex-[2] px-8 py-4 bg-emerald-500 text-black rounded-xl font-mono font-black text-xs uppercase tracking-widest hover:bg-emerald-400 transition-all shadow-[0_0_20px_rgba(16,185,129,0.3)] flex items-center justify-center gap-2"
             >
               <Save className="w-4 h-4" /> Deploy Changes
             </button>
          </div>
        }
      >
        <div className="space-y-8">
          <div className="space-y-4">
             <label className="text-[10px] font-mono text-gray-500 uppercase tracking-[0.2em] block">Workspace Identity</label>
             <div className="relative group">
                <Globe className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600 group-focus-within:text-emerald-500 transition-colors" />
                <input 
                  value={form.name}
                  onChange={e => setForm({...form, name: e.target.value})}
                  className="w-full bg-[#0d0d0e] border border-white/5 rounded-xl pl-12 pr-4 py-4 text-white font-mono text-sm focus:border-emerald-500/50 outline-none transition-all shadow-inner"
                />
             </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-3">
              <label className="text-[10px] font-mono text-gray-500 uppercase tracking-[0.2em] block">Subscription Tier</label>
              <div className="relative group">
                <Shield className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600 pointer-events-none" />
                <select 
                  value={form.plan}
                  onChange={e => setForm({...form, plan: e.target.value})}
                  className="w-full bg-[#0d0d0e] border border-white/5 rounded-xl pl-12 pr-10 py-4 text-white font-mono text-sm focus:border-purple-500/50 outline-none transition-all appearance-none shadow-inner"
                >
                  {plans.map(p => (
                    <option key={p.name} value={p.name}>{p.display_name.toUpperCase()}</option>
                  ))}
                </select>
                <ChevronRight className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600 rotate-90 pointer-events-none" />
              </div>
            </div>
            <div className="space-y-3">
              <label className="text-[10px] font-mono text-gray-500 uppercase tracking-[0.2em] block">Operational Access</label>
              <div className="flex items-center justify-between h-[58px] bg-[#0d0d0e] border border-white/5 rounded-xl px-6 shadow-inner">
                 <span className={`text-[10px] font-mono font-black uppercase tracking-widest ${form.is_active ? 'text-emerald-400' : 'text-red-400'}`}>
                   {form.is_active ? 'PROTOCOL: ACTIVE' : 'PROTOCOL: SUSPENDED'}
                 </span>
                 <button 
                  onClick={() => setForm({...form, is_active: !form.is_active})}
                  className={`w-12 h-6 rounded-full relative transition-all shadow-lg ${form.is_active ? 'bg-emerald-500' : 'bg-red-500/20 border border-red-500/30'}`}
                 >
                    <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-all shadow-md ${form.is_active ? 'left-7' : 'left-1'}`} />
                 </button>
              </div>
            </div>
          </div>

          <div className="space-y-6 bg-white/[0.02] border border-white/5 rounded-2xl p-8 relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none group-hover:opacity-10 transition-opacity">
               <Cpu className="w-24 h-24" />
            </div>
            <div className="flex items-center gap-3 mb-2 relative z-10">
              <div className="p-2 bg-blue-500/10 rounded-lg">
                <ShieldCheck className="w-4 h-4 text-blue-400" />
              </div>
              <span className="text-[10px] font-mono text-gray-400 uppercase tracking-[0.2em] font-black">Quota Overrides / Resource Allocation</span>
            </div>
            <div className="grid grid-cols-2 gap-6 relative z-10">
              <div className="space-y-3">
                <label className="text-[10px] font-mono text-gray-600 uppercase tracking-widest flex items-center gap-2">
                   <Activity className="w-3 h-3" /> Monthly Scans
                </label>
                <div className="relative">
                  <input 
                    type="number"
                    value={form.custom_scans_limit}
                    onChange={e => setForm({...form, custom_scans_limit: e.target.value})}
                    className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-4 text-white font-mono text-lg font-black focus:border-blue-400/50 outline-none transition-all shadow-inner"
                  />
                  <div className="absolute right-4 top-1/2 -translate-y-1/2 text-[9px] font-mono text-gray-700 uppercase tracking-tighter">Units</div>
                </div>
              </div>
              <div className="space-y-3">
                <label className="text-[10px] font-mono text-gray-600 uppercase tracking-widest flex items-center gap-2">
                   <Database className="w-3 h-3" /> Target Limit
                </label>
                <div className="relative">
                  <input 
                    type="number"
                    value={form.custom_targets_limit}
                    onChange={e => setForm({...form, custom_targets_limit: e.target.value})}
                    className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-4 text-white font-mono text-lg font-black focus:border-blue-400/50 outline-none transition-all shadow-inner"
                  />
                  <div className="absolute right-4 top-1/2 -translate-y-1/2 text-[9px] font-mono text-gray-700 uppercase tracking-tighter">Nodes</div>
                </div>
              </div>
            </div>
            <p className="text-[9px] font-mono text-gray-600 uppercase italic mt-4">Note: values set to 0 will inherit baseline protocols from the assigned subscription tier.</p>
          </div>
        </div>
      </HackerModal>

      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-8 border-b border-white/5 pb-10">
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-emerald-500/10 rounded-2xl border border-emerald-500/20 shadow-[0_0_25px_-5px_rgba(16,185,129,0.4)]">
              <Globe className="text-emerald-500 w-8 h-8" />
            </div>
            <div>
              <h1 className="text-4xl font-mono font-black text-white tracking-tighter uppercase italic">
                Workspace <span className="text-emerald-500">Registry</span>
              </h1>
              <div className="flex items-center gap-2 mt-1">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <p className="text-gray-500 font-mono text-[10px] uppercase tracking-[0.3em]">Operational Unit Management & Governance</p>
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative group">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600 group-focus-within:text-emerald-500 transition-colors" />
            <input 
              placeholder="FILTER BY NAME, OWNER OR ID..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="bg-[#0d0d0e] border border-white/5 rounded-2xl pl-12 pr-6 py-4 text-[10px] text-white font-mono uppercase tracking-[0.2em] focus:border-emerald-500/50 outline-none w-full sm:w-[320px] transition-all shadow-inner"
            />
          </div>
          <button className="px-6 py-4 bg-[#0d0d0e] border border-white/5 rounded-2xl text-gray-500 hover:text-white hover:border-white/10 flex items-center gap-3 font-mono text-[10px] uppercase tracking-widest transition-all">
             <Filter className="w-4 h-4" /> Refine Registry
          </button>
        </div>
      </div>

      {/* Registry Table */}
      <div className="bg-[#0d0d0e]/40 backdrop-blur-xl border border-white/[0.03] rounded-[2.5rem] overflow-hidden shadow-2xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-white/[0.02] border-b border-white/5">
                <th className="px-8 py-6 text-[10px] font-mono font-bold text-gray-500 uppercase tracking-[0.2em]">Workspace Context</th>
                <th className="px-8 py-6 text-[10px] font-mono font-bold text-gray-500 uppercase tracking-[0.2em]">Owner Identity</th>
                <th className="px-8 py-6 text-[10px] font-mono font-bold text-gray-500 uppercase tracking-[0.2em]">Service Tier</th>
                <th className="px-8 py-6 text-[10px] font-mono font-bold text-gray-500 uppercase tracking-[0.2em]">Lifecycle</th>
                <th className="px-8 py-6 text-[10px] font-mono font-bold text-gray-500 uppercase tracking-[0.2em]">Operations</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.02]">
              {filteredWorkspaces.map((w) => (
                <tr key={w.id} className="hover:bg-white/[0.02] transition-colors group">
                  <td className="px-8 py-6">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-2xl bg-emerald-500/5 border border-emerald-500/10 flex items-center justify-center group-hover:scale-110 transition-transform">
                         <Database className="w-5 h-5 text-emerald-500/60" />
                      </div>
                      <div>
                        <div className="text-sm font-mono font-black text-white group-hover:text-emerald-400 transition-colors uppercase italic">{w.name}</div>
                        <div className="text-[9px] font-mono text-gray-600 tracking-tighter mt-0.5">UID: {w.id}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-8 py-6">
                    <div className="flex items-center gap-3">
                      <Mail className="w-3.5 h-3.5 text-gray-600" />
                      <span className="text-xs font-mono text-gray-400">{w.owner_email || 'System Root'}</span>
                    </div>
                  </td>
                  <td className="px-8 py-6">
                    <div className="flex items-center gap-3">
                      <Shield className={`w-3.5 h-3.5 ${
                        w.plan === 'enterprise' ? 'text-purple-400' : w.plan === 'pro' ? 'text-blue-400' : 'text-gray-500'
                      }`} />
                      <span className={`text-[10px] font-mono font-black uppercase tracking-widest ${
                        w.plan === 'enterprise' ? 'text-purple-400' : w.plan === 'pro' ? 'text-blue-400' : 'text-gray-500'
                      }`}>
                        {w.plan || 'Free Tier'}
                      </span>
                    </div>
                  </td>
                  <td className="px-8 py-6">
                    <div className="space-y-1.5">
                      <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[9px] font-mono font-bold tracking-widest border ${
                        w.is_active 
                          ? 'bg-emerald-500/5 text-emerald-400 border-emerald-500/20' 
                          : 'bg-red-500/5 text-red-400 border-red-500/20'
                      }`}>
                        <div className={`w-1.5 h-1.5 rounded-full ${w.is_active ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`} />
                        {w.is_active ? 'OPERATIONAL' : 'SUSPENDED'}
                      </div>
                      <div className="text-[9px] font-mono text-gray-600 uppercase flex items-center gap-1">
                        <Calendar className="w-2.5 h-2.5" />
                        Init: {w.created_at ? formatDistanceToNow(new Date(w.created_at), { addSuffix: true }) : 'N/A'}
                      </div>
                    </div>
                  </td>
                  <td className="px-8 py-6">
                    <div className="flex items-center gap-3">
                      <button 
                        onClick={() => openEdit(w)}
                        className="p-3 bg-white/[0.02] border border-white/5 rounded-xl text-gray-500 hover:text-emerald-400 hover:border-emerald-500/30 hover:bg-emerald-500/5 transition-all"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button 
                        onClick={() => handleDelete(w.id, w.name)}
                        className="p-3 bg-white/[0.02] border border-white/5 rounded-xl text-gray-500 hover:text-red-500 hover:border-red-500/30 hover:bg-red-500/5 transition-all"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {filteredWorkspaces.length === 0 && (
          <div className="p-32 text-center">
            <div className="inline-flex p-8 rounded-[2.5rem] bg-white/5 border border-white/10 mb-8 opacity-20">
              <Database className="w-16 h-16 text-gray-400" />
            </div>
            <h2 className="text-2xl font-mono font-black text-white tracking-tighter uppercase italic">No Registry <span className="text-emerald-500">Hits</span></h2>
            <p className="text-gray-500 font-mono text-sm mt-4 max-w-xs mx-auto uppercase tracking-widest opacity-60">The workspace registry contains no records matching your current filter criteria.</p>
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
         <div className="p-8 bg-white/[0.02] border border-white/5 rounded-[2rem] space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">Global Density</span>
              <Activity className="w-4 h-4 text-emerald-500" />
            </div>
            <div className="text-3xl font-mono font-black text-white">{workspaces.length}</div>
            <p className="text-[9px] font-mono text-gray-600 uppercase leading-relaxed">Active organizational contexts currently provisioned in the primary cluster.</p>
         </div>
         <div className="p-8 bg-white/[0.02] border border-white/5 rounded-[2rem] space-y-4 md:col-span-2 flex flex-col justify-center">
            <div className="flex items-center gap-4">
               <ShieldCheck className="w-8 h-8 text-blue-500/40" />
               <div className="space-y-1">
                  <div className="text-[10px] font-mono text-blue-400 uppercase tracking-[0.2em] font-black">Governance Note</div>
                  <p className="text-xs font-mono text-gray-500 leading-relaxed uppercase">Modifying workspace parameters affects all users within that context immediately. Custom quota overrides take precedence over the selected service tier limits.</p>
               </div>
            </div>
         </div>
      </div>
    </div>
  );
}
