'use client';

import { useEffect, useState } from 'react';
import { adminListPlans, adminCreatePlan, adminUpdatePlan, adminDeletePlan } from '@/lib/api';
import { 
  CreditCard, Plus, Trash2, Edit2, Shield, Zap, Users, 
  Globe, Save, DollarSign, Activity, Lock, ShieldAlert,
  ChevronRight, Sparkles, Server, Cpu, Fingerprint, 
  Terminal, History, ZapOff, HardDrive, Binary
} from 'lucide-react';
import { toast } from 'sonner';
import { AdminCommandCenter } from '@/components/ui/AdminCommandCenter';
import { HackerModal } from '@/components/ui/HackerModal';
import { useConfirm } from '@/hooks/useConfirm';
import { motion, AnimatePresence } from 'framer-motion';

export default function PlansManagement() {
  const [plans, setPlans] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingPlan, setEditingPlan] = useState<any>(null);
  const [activeSection, setActiveSection] = useState('identity');
  const [isSaving, setIsSaving] = useState(false);
  const [form, setForm] = useState<any>({});
  const { confirm, state: confirmState, handleConfirm, handleCancel } = useConfirm();

  const sections = [
    { id: 'identity', label: 'Identity', icon: Fingerprint },
    { id: 'financials', label: 'Financials', icon: DollarSign },
    { id: 'quotas', label: 'Quotas', icon: Activity },
    { id: 'advanced', label: 'Advanced', icon: Cpu },
  ];

  useEffect(() => { loadPlans(); }, []);

  async function loadPlans() {
    try {
      const data = await adminListPlans();
      setPlans(data);
    } catch {
      toast.error("Failed to load plans");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: string, name: string) {
    const ok = await confirm({
      title: `Delete Plan "${name}"`,
      description: `Are you sure you want to delete this plan? This will NOT affect active subscriptions but will prevent new users from choosing this plan.`,
      confirmLabel: 'Delete Plan',
      variant: 'danger',
    });
    if (!ok) return;

    try {
      await adminDeletePlan(id);
      toast.success("Plan deleted");
      loadPlans();
    } catch (error: any) {
      toast.error(error.message || "Failed to delete plan");
    }
  }

  function openEdit(plan: any = null) {
    setActiveSection('identity');
    if (plan) {
      setEditingPlan(plan);
      setForm({
        ...plan,
        scans_per_month: plan.limits?.scans_per_month || 0,
        targets: plan.limits?.targets || 0,
        users: plan.limits?.users || 0,
        api_access: plan.limits?.api_access || false,
        parallel_scans: plan.limits?.parallel_scans || 1,
        ai_credits: plan.limits?.ai_credits || 0,
        data_retention_days: plan.limits?.data_retention_days || 30,
        burst_mode: plan.limits?.burst_mode || false,
        api_rate_limit: plan.limits?.api_rate_limit || 60,
      });
    } else {
      setEditingPlan(null);
      setForm({
        name: '',
        display_name: '',
        price_monthly: '0',
        price_yearly: '0',
        currency: 'USD',
        stripe_price_monthly_id: '',
        stripe_price_yearly_id: '',
        is_active: true,
        scans_per_month: 10,
        targets: 5,
        users: 1,
        api_access: false,
        parallel_scans: 1,
        ai_credits: 100,
        data_retention_days: 30,
        burst_mode: false,
        api_rate_limit: 60,
      });
    }
    setShowModal(true);
  }

  async function savePlan() {
    setIsSaving(true);
    try {
      const payload = {
        ...form,
        limits: {
          scans_per_month: parseInt(form.scans_per_month),
          targets: parseInt(form.targets),
          users: parseInt(form.users),
          api_access: form.api_access,
          parallel_scans: parseInt(form.parallel_scans),
          ai_credits: parseInt(form.ai_credits),
          data_retention_days: parseInt(form.data_retention_days),
          burst_mode: form.burst_mode,
          api_rate_limit: parseInt(form.api_rate_limit),
        }
      };

      if (editingPlan) {
        await adminUpdatePlan(editingPlan.id, payload);
        toast.success("Plan updated successfully");
      } else {
        await adminCreatePlan(payload);
        toast.success("Plan created successfully");
      }
      setShowModal(false);
      loadPlans();
    } catch (error: any) {
      toast.error(error.message || "Failed to save plan");
    } finally {
      setIsSaving(false);
    }
  }

  if (loading) return (
    <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
      <div className="relative">
        <div className="w-16 h-16 border-4 border-neon-green/10 border-t-neon-green rounded-full animate-spin" />
        <div className="absolute inset-0 bg-neon-green/20 blur-xl animate-pulse rounded-full" />
      </div>
      <p className="text-neon-green font-mono text-sm tracking-[0.2em] uppercase animate-pulse">Syncing Tiers...</p>
    </div>
  );

  return (
    <div className="max-w-[1200px] mx-auto space-y-12 pb-20">
      <HackerModal
        open={confirmState.open}
        title={confirmState.title || ''}
        description={confirmState.description || ''}
        variant={(confirmState.variant as any) || 'danger'}
        onClose={handleCancel}
        footer={
          <div className="flex gap-4 pt-2">
            <button
              onClick={handleCancel}
              className="flex-1 px-8 py-4 bg-white/5 border border-white/10 rounded-2xl text-xs font-mono font-black text-gray-500 uppercase tracking-widest hover:text-white hover:bg-white/10 transition-all"
            >
              Abort Mission
            </button>
            <button
              onClick={handleConfirm}
              className={`flex-[2] px-10 py-4 ${confirmState.variant === 'danger' ? 'bg-red-500 hover:bg-red-600 text-white' : 'bg-neon-green hover:bg-emerald-400 text-black'} rounded-2xl text-xs font-mono font-black uppercase tracking-[0.2em] transition-all shadow-xl active:scale-95 flex items-center justify-center gap-3`}
            >
              <Terminal className="w-4 h-4" />
              {confirmState.confirmLabel || 'Confirm Action'}
            </button>
          </div>
        }
      />

      <AdminCommandCenter
        open={showModal}
        onClose={() => setShowModal(false)}
        title={editingPlan ? `Configure Tier: ${editingPlan.display_name}` : 'Initialize New Tier'}
        subtitle="System Tier & Policy Configuration"
        sections={sections}
        activeSection={activeSection}
        onSectionChange={setActiveSection}
        isLoading={isSaving}
        onSave={savePlan}
        variant="cyan"
        size="4xl"
      >
        <div className="space-y-8 min-h-[400px]">
          <AnimatePresence mode="wait">
            {activeSection === 'identity' && (
              <motion.div
                key="identity"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-8"
              >
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-3">
                    <label className="text-[10px] font-mono text-gray-400 uppercase tracking-[0.2em] block">Internal Registry Slug</label>
                    <div className="relative group">
                      <Server className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600 group-focus-within:text-neon-green transition-colors" />
                      <input 
                        value={form.name} 
                        disabled={!!editingPlan}
                        onChange={e => setForm({...form, name: e.target.value})}
                        placeholder="enterprise-v3"
                        className="w-full bg-black/40 border border-white/5 rounded-xl pl-12 pr-4 py-3 text-white font-mono text-sm focus:border-neon-green/50 focus:ring-1 focus:ring-neon-green/20 outline-none transition-all disabled:opacity-40"
                      />
                    </div>
                  </div>
                  <div className="space-y-3">
                    <label className="text-[10px] font-mono text-gray-400 uppercase tracking-[0.2em] block">Marketing Title</label>
                    <div className="relative group">
                      <Sparkles className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600 group-focus-within:text-blue-400 transition-colors" />
                      <input 
                        value={form.display_name} 
                        onChange={e => setForm({...form, display_name: e.target.value})}
                        placeholder="Titanium Enterprise"
                        className="w-full bg-black/40 border border-white/5 rounded-xl pl-12 pr-4 py-3 text-white font-mono text-sm focus:border-blue-400/50 focus:ring-1 focus:ring-blue-400/20 outline-none transition-all"
                      />
                    </div>
                  </div>
                </div>

                <label className="flex items-center gap-4 p-6 bg-white/[0.02] border border-white/5 rounded-2xl cursor-pointer hover:bg-white/[0.04] transition-all group">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all ${form.is_active ? 'bg-emerald-500/10 text-emerald-400 shadow-[0_0_20px_-5px_rgba(52,211,153,0.4)]' : 'bg-white/5 text-gray-500'}`}>
                    <Activity className="w-6 h-6" />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-mono font-bold text-white group-hover:text-emerald-400 transition-colors">Deployment Status</div>
                    <div className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">Enable or disable this tier in the public registry</div>
                  </div>
                  <div className="relative inline-flex items-center cursor-pointer">
                    <input 
                      type="checkbox" 
                      className="sr-only peer"
                      checked={form.is_active}
                      onChange={e => setForm({...form, is_active: e.target.checked})}
                    />
                    <div className="w-11 h-6 bg-white/5 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-500/50 border border-white/10"></div>
                  </div>
                </label>
              </motion.div>
            )}

            {activeSection === 'financials' && (
              <motion.div
                key="financials"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-8"
              >
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="space-y-3">
                    <label className="text-[10px] font-mono text-gray-400 uppercase tracking-[0.2em] block">Monthly Rate</label>
                    <div className="relative group">
                      <DollarSign className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-emerald-500" />
                      <input 
                        type="number"
                        value={form.price_monthly} 
                        onChange={e => setForm({...form, price_monthly: e.target.value})}
                        className="w-full bg-black/40 border border-white/5 rounded-xl pl-12 pr-4 py-3 text-white font-mono text-lg focus:border-emerald-500/50 outline-none transition-all"
                      />
                    </div>
                  </div>
                  <div className="space-y-3">
                    <label className="text-[10px] font-mono text-gray-400 uppercase tracking-[0.2em] block">Yearly Rate</label>
                    <div className="relative group">
                      <DollarSign className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-blue-500" />
                      <input 
                        type="number"
                        value={form.price_yearly} 
                        onChange={e => setForm({...form, price_yearly: e.target.value})}
                        className="w-full bg-black/40 border border-white/5 rounded-xl pl-12 pr-4 py-3 text-white font-mono text-lg focus:border-blue-500/50 outline-none transition-all"
                      />
                    </div>
                  </div>
                  <div className="space-y-3">
                    <label className="text-[10px] font-mono text-gray-400 uppercase tracking-[0.2em] block">ISO Currency</label>
                    <input 
                      value={form.currency} 
                      onChange={e => setForm({...form, currency: e.target.value})}
                      className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-white font-mono text-center uppercase focus:border-neon-green/50 outline-none transition-all"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-6 bg-white/[0.02] border border-white/5 rounded-2xl">
                  <div className="space-y-3">
                    <label className="text-[10px] font-mono text-gray-400 uppercase tracking-[0.2em] block">Stripe Monthly Price ID</label>
                    <input 
                      value={form.stripe_price_monthly_id} 
                      onChange={e => setForm({...form, stripe_price_monthly_id: e.target.value})}
                      placeholder="price_H1..."
                      className="w-full bg-black/20 border border-white/5 rounded-xl px-4 py-3 text-white font-mono text-xs focus:border-neon-green/50 outline-none transition-all"
                    />
                  </div>
                  <div className="space-y-3">
                    <label className="text-[10px] font-mono text-gray-400 uppercase tracking-[0.2em] block">Stripe Yearly Price ID</label>
                    <input 
                      value={form.stripe_price_yearly_id} 
                      onChange={e => setForm({...form, stripe_price_yearly_id: e.target.value})}
                      placeholder="price_H2..."
                      className="w-full bg-black/20 border border-white/5 rounded-xl px-4 py-3 text-white font-mono text-xs focus:border-neon-green/50 outline-none transition-all"
                    />
                  </div>
                </div>
              </motion.div>
            )}

            {activeSection === 'quotas' && (
              <motion.div
                key="quotas"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-8"
              >
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 mb-1">
                      <Activity className="w-3 h-3 text-neon-green" />
                      <label className="text-[10px] font-mono text-gray-400 uppercase tracking-widest">Monthly Scans</label>
                    </div>
                    <input 
                      type="number"
                      value={form.scans_per_month} 
                      onChange={e => setForm({...form, scans_per_month: e.target.value})}
                      className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-white font-mono text-sm focus:border-neon-green/50 outline-none transition-all"
                    />
                  </div>
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 mb-1">
                      <Globe className="w-3 h-3 text-blue-400" />
                      <label className="text-[10px] font-mono text-gray-400 uppercase tracking-widest">Asset Limit</label>
                    </div>
                    <input 
                      type="number"
                      value={form.targets} 
                      onChange={e => setForm({...form, targets: e.target.value})}
                      className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-white font-mono text-sm focus:border-blue-400/50 outline-none transition-all"
                    />
                  </div>
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 mb-1">
                      <Users className="w-3 h-3 text-purple-400" />
                      <label className="text-[10px] font-mono text-gray-400 uppercase tracking-widest">Seat Limit</label>
                    </div>
                    <input 
                      type="number"
                      value={form.users} 
                      onChange={e => setForm({...form, users: e.target.value})}
                      className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-white font-mono text-sm focus:border-purple-400/50 outline-none transition-all"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <label className="flex items-center gap-4 p-4 bg-white/[0.02] border border-white/5 rounded-xl cursor-pointer hover:bg-white/[0.04] transition-all group">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all ${form.api_access ? 'bg-neon-green/10 text-neon-green shadow-[0_0_15px_-5px_rgba(57,255,20,0.4)]' : 'bg-white/5 text-gray-500'}`}>
                      <Cpu className="w-5 h-5" />
                    </div>
                    <div className="flex-1">
                      <div className="text-sm font-mono font-bold text-white group-hover:text-neon-green transition-colors">Programmatic Interface</div>
                      <div className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">Enable API/CLI access</div>
                    </div>
                    <input 
                      type="checkbox" 
                      checked={form.api_access}
                      onChange={e => setForm({...form, api_access: e.target.checked})}
                      className="w-5 h-5 rounded-md border-white/10 bg-black/40 text-neon-green focus:ring-neon-green/20 transition-all cursor-pointer"
                    />
                  </label>

                  <div className="space-y-3">
                    <div className="flex items-center gap-2 mb-1">
                      <Zap className="w-3 h-3 text-amber-500" />
                      <label className="text-[10px] font-mono text-gray-400 uppercase tracking-widest">API Rate Limit (req/min)</label>
                    </div>
                    <input 
                      type="number"
                      value={form.api_rate_limit} 
                      onChange={e => setForm({...form, api_rate_limit: e.target.value})}
                      className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-white font-mono text-sm focus:border-amber-500/50 outline-none transition-all"
                    />
                  </div>
                </div>
              </motion.div>
            )}

            {activeSection === 'advanced' && (
              <motion.div
                key="advanced"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-8"
              >
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  <div className="space-y-3 p-6 bg-white/[0.02] border border-white/5 rounded-2xl">
                    <div className="flex items-center gap-2 mb-2">
                      <Binary className="w-4 h-4 text-cyan-400" />
                      <label className="text-[10px] font-mono text-gray-400 uppercase tracking-widest font-black">Parallel Scan Threads</label>
                    </div>
                    <div className="flex items-center gap-4">
                      <input 
                        type="range"
                        min="1"
                        max="20"
                        step="1"
                        value={form.parallel_scans} 
                        onChange={e => setForm({...form, parallel_scans: e.target.value})}
                        className="flex-1 accent-cyan-400"
                      />
                      <span className="text-xl font-mono font-black text-cyan-400 min-w-[2rem] text-center">{form.parallel_scans}</span>
                    </div>
                    <p className="text-[9px] font-mono text-gray-600 uppercase">Maximum concurrent scan jobs per workspace</p>
                  </div>

                  <div className="space-y-3 p-6 bg-white/[0.02] border border-white/5 rounded-2xl">
                    <div className="flex items-center gap-2 mb-2">
                      <Shield className="w-4 h-4 text-purple-400" />
                      <label className="text-[10px] font-mono text-gray-400 uppercase tracking-widest font-black">AI Intelligence Credits</label>
                    </div>
                    <input 
                      type="number"
                      value={form.ai_credits} 
                      onChange={e => setForm({...form, ai_credits: e.target.value})}
                      className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-white font-mono text-sm focus:border-purple-500/50 outline-none transition-all"
                    />
                    <p className="text-[9px] font-mono text-gray-600 uppercase">Monthly tokens for AI-powered vulnerability analysis</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  <div className="space-y-3 p-6 bg-white/[0.02] border border-white/5 rounded-2xl">
                    <div className="flex items-center gap-2 mb-2">
                      <History className="w-4 h-4 text-amber-500" />
                      <label className="text-[10px] font-mono text-gray-400 uppercase tracking-widest font-black">Data Retention Policy</label>
                    </div>
                    <div className="flex items-center gap-3">
                      <HardDrive className="w-4 h-4 text-gray-700" />
                      <select 
                        value={form.data_retention_days}
                        onChange={e => setForm({...form, data_retention_days: e.target.value})}
                        className="flex-1 bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-white font-mono text-sm focus:border-amber-500/50 outline-none appearance-none cursor-pointer"
                      >
                        <option value="7">7 Days (Ephemeral)</option>
                        <option value="30">30 Days (Standard)</option>
                        <option value="90">90 Days (Extended)</option>
                        <option value="365">1 Year (Compliance)</option>
                        <option value="0">Unlimited (Persistent)</option>
                      </select>
                    </div>
                  </div>

                  <label className="flex items-center gap-4 p-6 bg-white/[0.02] border border-white/5 rounded-2xl cursor-pointer hover:bg-white/[0.04] transition-all group">
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all ${form.burst_mode ? 'bg-orange-500/10 text-orange-400 shadow-[0_0_20px_-5px_rgba(251,146,60,0.4)]' : 'bg-white/5 text-gray-500'}`}>
                      <Zap className="w-6 h-6" />
                    </div>
                    <div className="flex-1">
                      <div className="text-sm font-mono font-bold text-white group-hover:text-orange-400 transition-colors">Burst Execution Mode</div>
                      <div className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">Allow temporary overflow of execution limits</div>
                    </div>
                    <div className="relative inline-flex items-center cursor-pointer">
                      <input 
                        type="checkbox" 
                        className="sr-only peer"
                        checked={form.burst_mode}
                        onChange={e => setForm({...form, burst_mode: e.target.checked})}
                      />
                      <div className="w-11 h-6 bg-white/5 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-orange-500/50 border border-white/10"></div>
                    </div>
                  </label>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </AdminCommandCenter>

      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 pb-4 border-b border-white/5">
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-neon-green/10 rounded-xl border border-neon-green/20">
              <CreditCard className="text-neon-green w-8 h-8" />
            </div>
            <div>
              <h1 className="text-4xl font-mono font-black text-white tracking-tighter uppercase italic">
                Subscription <span className="text-neon-green">Architecture</span>
              </h1>
              <div className="flex items-center gap-2 mt-1">
                <div className="w-2 h-2 rounded-full bg-neon-green animate-pulse" />
                <p className="text-gray-500 font-mono text-[10px] uppercase tracking-[0.3em]">Tier Registry & Policy Enforcement Engine</p>
              </div>
            </div>
          </div>
        </div>
        <button 
          onClick={() => openEdit()}
          className="group relative flex items-center gap-3 bg-white text-black px-8 py-4 rounded-2xl font-mono font-black text-sm uppercase tracking-widest hover:bg-neon-green transition-all shadow-[0_0_50px_-12px_rgba(255,255,255,0.3)] hover:shadow-neon-green/40 active:scale-95"
        >
          <Plus className="w-5 h-5 group-hover:rotate-90 transition-transform duration-500" /> 
          Deploy New Tier
        </button>
      </div>

      {/* Plans Grid */}
      <div className="grid grid-cols-1 gap-6">
        {plans.map(plan => (
          <div 
            key={plan.id} 
            className="group relative overflow-hidden bg-[#0d0d0e]/60 backdrop-blur-xl border border-white/[0.03] rounded-[2rem] p-1 transition-all hover:border-neon-green/30"
          >
            {/* Glossy Overlay */}
            <div className="absolute inset-0 bg-gradient-to-br from-white/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
            
            <div className="bg-[#0d0d0e] rounded-[1.9rem] p-8 lg:p-10">
              <div className="flex flex-col xl:flex-row xl:items-center gap-10">
                
                {/* Visual Identity */}
                <div className="flex items-center gap-8 min-w-[320px]">
                  <div className={`relative p-6 rounded-[1.5rem] bg-black/40 border border-white/5 flex items-center justify-center shadow-2xl transition-all group-hover:scale-110 duration-500 ${
                    plan.name === 'enterprise' ? 'text-purple-500 shadow-purple-500/10' : plan.name === 'pro' ? 'text-neon-green shadow-neon-green/10' : 'text-blue-500 shadow-blue-500/10'
                  }`}>
                     <Shield className="w-12 h-12" />
                     {plan.name === 'enterprise' && <div className="absolute -top-2 -right-2 bg-purple-600 text-white text-[8px] font-black px-2 py-1 rounded-md tracking-tighter">ELITE</div>}
                  </div>
                  
                  <div className="space-y-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-3">
                        <h3 className="text-3xl font-mono font-black text-white group-hover:text-neon-green transition-colors">{plan.display_name}</h3>
                        <div className={`px-3 py-1 rounded-full text-[9px] font-mono font-bold tracking-widest flex items-center gap-1.5 ${
                          plan.is_active 
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                            : 'bg-red-500/10 text-red-400 border border-red-500/20'
                        }`}>
                          <div className={`w-1.5 h-1.5 rounded-full ${plan.is_active ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`} />
                          {plan.is_active ? 'LIVE' : 'OFFLINE'}
                        </div>
                      </div>
                      <p className="text-xs font-mono text-gray-500 uppercase tracking-widest opacity-60">System Protocol: {plan.name}</p>
                    </div>

                    <div className="flex items-center gap-6">
                      <div className="flex flex-col">
                        <span className="text-[10px] font-mono text-gray-600 uppercase tracking-wider">Monthly</span>
                        <div className="flex items-baseline gap-1">
                          <span className="text-2xl font-mono font-black text-white">${plan.price_monthly}</span>
                          <span className="text-[10px] text-gray-500 font-mono uppercase tracking-tighter">USD</span>
                        </div>
                      </div>
                      <div className="w-px h-8 bg-white/5" />
                      <div className="flex flex-col">
                        <span className="text-[10px] font-mono text-gray-600 uppercase tracking-wider">Annualized</span>
                        <div className="flex items-baseline gap-1">
                          <span className="text-2xl font-mono font-black text-gray-400">${plan.price_yearly}</span>
                          <span className="text-[10px] text-gray-600 font-mono uppercase tracking-tighter">USD</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Quota Matrix */}
                <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-6 p-8 bg-white/[0.02] border border-white/5 rounded-3xl group-hover:bg-white/[0.04] transition-all">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Activity className="w-3.5 h-3.5 text-neon-green" />
                      <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest font-bold">Execution</span>
                    </div>
                    <div className="text-xl font-mono font-black text-white">{plan.limits?.scans_per_month || '∞'} <span className="text-[10px] font-normal text-gray-600 tracking-normal">SCANS</span></div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Globe className="w-3.5 h-3.5 text-blue-400" />
                      <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest font-bold">Coverage</span>
                    </div>
                    <div className="text-xl font-mono font-black text-white">{plan.limits?.targets || '∞'} <span className="text-[10px] font-normal text-gray-600 tracking-normal">ASSETS</span></div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Users className="w-3.5 h-3.5 text-purple-400" />
                      <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest font-bold">Team</span>
                    </div>
                    <div className="text-xl font-mono font-black text-white">{plan.limits?.users || '1'} <span className="text-[10px] font-normal text-gray-600 tracking-normal">SEATS</span></div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Zap className="w-3.5 h-3.5 text-amber-400" />
                      <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest font-bold">API/CLI</span>
                    </div>
                    <div className={`text-xl font-mono font-black ${plan.limits?.api_access ? 'text-emerald-400' : 'text-gray-600'}`}>{plan.limits?.api_access ? 'ACTIVE' : 'LOCKED'}</div>
                  </div>
                </div>

                {/* Interaction Terminal */}
                <div className="flex items-center gap-3 self-center xl:self-auto">
                  <button 
                    onClick={() => openEdit(plan)}
                    className="p-4 bg-white/[0.02] border border-white/5 rounded-2xl text-gray-500 hover:text-neon-green hover:border-neon-green/30 hover:bg-neon-green/5 transition-all group-hover:translate-x-[-4px]"
                    title="Reconfigure Tier"
                  >
                    <Edit2 className="w-6 h-6" />
                  </button>
                  <button 
                    onClick={() => handleDelete(plan.id, plan.display_name)}
                    className="p-4 bg-white/[0.02] border border-white/5 rounded-2xl text-gray-500 hover:text-red-500 hover:border-red-500/30 hover:bg-red-500/5 transition-all group-hover:translate-x-[-2px]"
                    title="Terminate Tier"
                  >
                    <Trash2 className="w-6 h-6" />
                  </button>
                  <div className="w-10 h-10 flex items-center justify-center text-gray-800 opacity-0 group-hover:opacity-100 transition-opacity">
                    <ChevronRight className="w-6 h-6 animate-pulse" />
                  </div>
                </div>
              </div>

              {/* Security & Stripe Integrity */}
              <div className="mt-8 pt-6 border-t border-white/[0.02] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 opacity-40 group-hover:opacity-100 transition-opacity">
                <div className="flex flex-wrap gap-x-8 gap-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] font-mono text-gray-600 uppercase">Monthly Price Link</span>
                    <code className="text-[9px] font-mono text-white/50 bg-white/5 px-2 py-0.5 rounded border border-white/5">{plan.stripe_price_monthly_id || 'NULL'}</code>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] font-mono text-gray-600 uppercase">Annual Price Link</span>
                    <code className="text-[9px] font-mono text-white/50 bg-white/5 px-2 py-0.5 rounded border border-white/5">{plan.stripe_price_yearly_id || 'NULL'}</code>
                  </div>
                </div>
                {(!plan.stripe_price_monthly_id || !plan.stripe_price_yearly_id) && plan.name !== 'free' && (
                  <div className="flex items-center gap-2 text-[9px] font-mono font-black text-amber-500/80 bg-amber-500/5 border border-amber-500/20 px-3 py-1 rounded-full italic">
                    <ShieldAlert className="w-3 h-3" /> STRIPE_SYNC_FAILURE_DETECTION
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {plans.length === 0 && !loading && (
        <div className="relative overflow-hidden bg-[#0d0d0e]/60 backdrop-blur-xl border border-dashed border-white/10 rounded-[3rem] p-24 text-center">
          <div className="absolute inset-0 bg-gradient-to-b from-neon-green/5 to-transparent pointer-events-none" />
          <div className="relative z-10 flex flex-col items-center">
            <div className="p-8 rounded-[2rem] bg-white/5 border border-white/10 mb-8 animate-bounce">
              <Lock className="w-16 h-16 text-gray-600" />
            </div>
            <h2 className="text-3xl font-mono font-black text-white tracking-tighter uppercase italic">Registry is <span className="text-red-500">Empty</span></h2>
            <p className="text-gray-500 font-mono text-sm mt-4 max-w-sm">No subscription tiers have been initialized in the primary data cluster. Deploy a new tier to restore order.</p>
            <button 
              onClick={() => openEdit()}
              className="mt-10 bg-white text-black px-12 py-4 rounded-2xl font-mono font-black text-sm uppercase tracking-[0.2em] hover:bg-neon-green transition-all shadow-[0_0_50px_-10px_rgba(255,255,255,0.2)]"
            >
              Initialize Cluster
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
