'use client';

import { useEffect, useState } from 'react';
import { adminListSettings, adminUpdateSetting, adminBatchUpdateSettings } from '@/lib/api';
import { 
  Settings, Save, RefreshCw, Shield, Zap, Bell, Globe, 
  Lock, Cpu, Database, ChevronRight, Binary, Fingerprint,
  Mail, HardDrive, Terminal
} from 'lucide-react';
import { toast } from 'sonner';
import { ConfirmModal } from '@/components/ui/ConfirmModal';
import { useConfirm } from '@/hooks/useConfirm';

export default function GlobalSettingsPage() {
  const [settings, setSettings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeCategory, setActiveCategory] = useState('general');
  const { confirm, state: confirmState, handleConfirm, handleCancel } = useConfirm();

  const categories = [
    { id: 'general', label: 'Core Platform', icon: Globe, description: 'Branding, Localization & Identity' },
    { id: 'security', label: 'Security Firewall', icon: Lock, description: 'Auth, MFA & Network Policies' },
    { id: 'ai', label: 'Cortex AI', icon: Cpu, description: 'LLM, Analysis & Automations' },
    { id: 'scans', label: 'Scan Clusters', icon: Zap, description: 'Engine, Rules & Performance' },
    { id: 'notifications', label: 'Comm Hub', icon: Bell, description: 'SMTP, Webhooks & Alerts' },
  ];

  useEffect(() => {
    loadSettings();
  }, []);

  async function loadSettings() {
    setLoading(true);
    try {
      const data = await adminListSettings();
      setSettings(data);
    } catch (error) {
      toast.error("Failed to load settings");
    } finally {
      setLoading(false);
    }
  }

  const filteredSettings = settings.filter(s => s.category === activeCategory);

  async function handleUpdate(key: string, value: any) {
    try {
      await adminUpdateSetting(key, value);
      setSettings(settings.map(s => s.key === key ? { ...s, value } : s));
      toast.success(`Parameter [${key}] synchronized`);
    } catch (error) {
      toast.error(`Failed to sync [${key}]`);
    }
  }

  async function saveAll() {
    const ok = await confirm({
      title: 'Commit Global Configuration',
      description: 'You are about to propagate these changes across the entire system. All active sessions and nodes will be affected.',
      confirmLabel: 'Commit to Cluster',
      variant: 'warning',
    });
    if (!ok) return;

    setSaving(true);
    try {
      await adminBatchUpdateSettings(filteredSettings);
      toast.success("Global registry synchronized");
      loadSettings();
    } catch (error) {
      toast.error("Cluster synchronization failed");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return (
    <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
      <div className="relative">
        <div className="w-16 h-16 border-4 border-neon-green/10 border-t-neon-green rounded-full animate-spin" />
        <div className="absolute inset-0 bg-neon-green/20 blur-xl animate-pulse rounded-full" />
      </div>
      <p className="text-neon-green font-mono text-sm tracking-[0.2em] uppercase animate-pulse">Decrypting Cluster Config...</p>
    </div>
  );

  return (
    <div className="max-w-[1400px] mx-auto space-y-12 pb-20">
      <ConfirmModal
        open={confirmState.open}
        title={confirmState.title}
        description={confirmState.description}
        confirmLabel={confirmState.confirmLabel}
        variant={confirmState.variant}
        onConfirm={handleConfirm}
        onCancel={handleCancel}
      />

      {/* Hero Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-8 border-b border-white/5 pb-10">
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-neon-green/10 rounded-2xl border border-neon-green/20 shadow-[0_0_25px_-5px_rgba(57,255,20,0.4)]">
              <Settings className="text-neon-green w-8 h-8" />
            </div>
            <div>
              <h1 className="text-4xl font-mono font-black text-white tracking-tighter uppercase italic">
                System <span className="text-neon-green">Control</span> Center
              </h1>
              <div className="flex items-center gap-2 mt-1">
                <div className="w-2 h-2 rounded-full bg-neon-green animate-pulse" />
                <p className="text-gray-500 font-mono text-[10px] uppercase tracking-[0.3em]">Universal Registry Configuration & Security Policies</p>
              </div>
            </div>
          </div>
        </div>
        <button 
          onClick={saveAll}
          disabled={saving}
          className="group relative flex items-center gap-3 bg-white text-black px-10 py-4 rounded-2xl font-mono font-black text-sm uppercase tracking-[0.2em] hover:bg-neon-green transition-all shadow-[0_0_50px_-15px_rgba(255,255,255,0.4)] hover:shadow-neon-green/50 active:scale-95 disabled:opacity-50"
        >
          {saving ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
          Synchronize Cluster
        </button>
      </div>

      <div className="flex flex-col lg:flex-row gap-10">
        {/* Navigation Sidebar */}
        <div className="w-full lg:w-80 space-y-3">
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setActiveCategory(cat.id)}
              className={`w-full group text-left p-4 rounded-2xl transition-all border flex items-center gap-4 ${
                activeCategory === cat.id 
                  ? 'bg-neon-green/5 border-neon-green/30 shadow-[0_0_20px_-5px_rgba(57,255,20,0.1)]' 
                  : 'bg-[#0d0d0e]/40 border-white/[0.03] hover:border-white/10'
              }`}
            >
              <div className={`p-3 rounded-xl transition-all ${
                activeCategory === cat.id ? 'bg-neon-green text-black scale-110 shadow-lg' : 'bg-white/5 text-gray-500 group-hover:text-white'
              }`}>
                <cat.icon className="w-5 h-5" />
              </div>
              <div className="flex-1 overflow-hidden">
                <div className={`text-sm font-mono font-black uppercase tracking-wider transition-colors ${
                  activeCategory === cat.id ? 'text-white' : 'text-gray-500 group-hover:text-gray-300'
                }`}>{cat.label}</div>
                <div className="text-[9px] font-mono text-gray-600 uppercase tracking-tighter truncate">{cat.description}</div>
              </div>
              {activeCategory === cat.id && <ChevronRight className="w-4 h-4 text-neon-green animate-pulse" />}
            </button>
          ))}
          
          <div className="mt-8 p-6 bg-white/[0.02] border border-white/5 rounded-[2rem] space-y-4">
             <div className="flex items-center gap-2">
                <HardDrive className="w-3.5 h-3.5 text-gray-600" />
                <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest font-black">Storage Integrity</span>
             </div>
             <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                <div className="h-full w-[42%] bg-neon-green/50" />
             </div>
             <p className="text-[9px] font-mono text-gray-600 uppercase">Buffer usage: 42.8 GB / 100 GB</p>
          </div>
        </div>

        {/* Content Engine */}
        <div className="flex-1 space-y-6">
          <div className="bg-[#0d0d0e]/60 backdrop-blur-xl border border-white/[0.03] rounded-[2.5rem] overflow-hidden shadow-2xl">
            <div className="p-10 border-b border-white/[0.03] flex items-center justify-between bg-white/[0.01]">
              <div>
                <h2 className="text-2xl font-mono font-black text-white flex items-center gap-3 uppercase italic">
                  {categories.find(c => c.id === activeCategory)?.label} <span className="text-neon-green">Nodes</span>
                </h2>
                <p className="text-[10px] font-mono text-gray-500 uppercase tracking-[0.3em] mt-1">Modifying primary configuration registry</p>
              </div>
              <div className="hidden sm:flex items-center gap-2 bg-black/40 border border-white/5 px-4 py-2 rounded-xl">
                 <Binary className="w-4 h-4 text-gray-600" />
                 <span className="text-[10px] font-mono text-gray-500 uppercase tracking-tighter">Cluster Status: <span className="text-emerald-500 font-bold">STABLE</span></span>
              </div>
            </div>
            
            <div className="p-10 space-y-12">
              {filteredSettings.length === 0 ? (
                <div className="text-center py-20">
                  <Database className="w-16 h-16 text-gray-800 mx-auto mb-6 animate-pulse" />
                  <p className="text-gray-500 font-mono text-sm uppercase tracking-widest">No active parameters detected in this cluster segment.</p>
                  <button 
                    onClick={() => handleUpdate(`init_${activeCategory}`, { enabled: true })}
                    className="mt-10 px-8 py-3 bg-white/5 border border-white/10 rounded-xl text-xs text-neon-green hover:bg-neon-green hover:text-black font-mono font-black transition-all"
                  >
                    Generate Default Parameters
                  </button>
                </div>
              ) : (
                filteredSettings.map((setting) => (
                  <div key={setting.key} className="grid grid-cols-1 xl:grid-cols-3 gap-8 group">
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                         <div className="w-1.5 h-1.5 rounded-full bg-neon-green/30 group-hover:bg-neon-green transition-colors" />
                         <label className="text-sm font-mono font-black text-gray-400 group-hover:text-white transition-colors uppercase tracking-wider">
                           {setting.key.replace(/_/g, ' ')}
                         </label>
                      </div>
                      <p className="text-[10px] text-gray-600 font-mono uppercase leading-relaxed pl-3.5 italic">{setting.description || 'System mandated parameter for infrastructure stability.'}</p>
                    </div>
                    <div className="xl:col-span-2">
                      {typeof setting.value === 'boolean' ? (
                        <div className="flex items-center gap-6 p-4 bg-black/40 border border-white/[0.02] rounded-2xl">
                          <button
                            onClick={() => handleUpdate(setting.key, !setting.value)}
                            className={`relative inline-flex h-7 w-14 items-center rounded-full transition-all focus:outline-none shadow-inner ${
                              setting.value ? 'bg-neon-green shadow-neon-green/20' : 'bg-gray-800'
                            }`}
                          >
                            <span
                              className={`inline-block h-5 w-5 transform rounded-full bg-white transition-all shadow-md ${
                                setting.value ? 'translate-x-8' : 'translate-x-1'
                              }`}
                            />
                          </button>
                          <div className="flex flex-col">
                            <span className={`text-[10px] font-mono font-black uppercase tracking-widest ${setting.value ? 'text-neon-green' : 'text-gray-600'}`}>
                              {setting.value ? 'Active Operation' : 'Bypassed'}
                            </span>
                            <span className="text-[9px] font-mono text-gray-700 uppercase tracking-tighter">Logical State</span>
                          </div>
                        </div>
                      ) : typeof setting.value === 'object' ? (
                        <div className="relative group/text">
                          <div className="absolute right-4 top-4 z-10 p-2 bg-black/60 rounded-lg text-gray-600 opacity-0 group-hover/text:opacity-100 transition-opacity">
                             <Fingerprint className="w-4 h-4" />
                          </div>
                          <textarea
                            value={JSON.stringify(setting.value, null, 2)}
                            onChange={(e) => {
                              try {
                                const val = JSON.parse(e.target.value);
                                setSettings(settings.map(s => s.key === setting.key ? { ...s, value: val } : s));
                              } catch (err) {}
                            }}
                            className="w-full bg-black/60 border border-white/5 rounded-2xl px-6 py-5 text-xs font-mono text-gray-400 focus:text-blue-400 focus:border-blue-500/50 outline-none h-48 transition-all resize-none shadow-inner scrollbar-hide"
                          />
                          <div className="absolute left-6 -bottom-3 px-3 py-1 bg-black border border-white/5 rounded-lg text-[8px] font-mono text-gray-600 uppercase tracking-[0.2em]">JSON Protocol Buffer</div>
                        </div>
                      ) : (
                        <div className="relative">
                          <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-700">
                             <Terminal className="w-4 h-4" />
                          </div>
                          <input
                            type="text"
                            value={setting.value}
                            onChange={(e) => {
                              setSettings(settings.map(s => s.key === setting.key ? { ...s, value: e.target.value } : s));
                            }}
                            className="w-full bg-black/60 border border-white/5 rounded-2xl pl-12 pr-6 py-4 text-sm font-mono text-white focus:border-neon-green/50 outline-none transition-all shadow-inner"
                          />
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {activeCategory === 'security' && (
            <div className="bg-red-500/5 border border-red-500/10 rounded-[2rem] p-8 flex gap-6 items-start animate-pulse">
              <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20 shadow-[0_0_20px_rgba(239,68,68,0.2)]">
                <Shield className="w-8 h-8 text-red-500" />
              </div>
              <div className="space-y-2">
                <h3 className="font-mono font-black text-red-500 uppercase tracking-[0.2em] italic text-lg">Infrastructure Security Breach Risk</h3>
                <p className="text-xs text-gray-500 font-mono uppercase leading-relaxed max-w-2xl">
                  Modification of security firewall parameters requires high-level clearance. Any misconfiguration will immediately cascade across all regional data centers and may result in partial or total service disruption.
                </p>
              </div>
            </div>
          )}
          
          <div className="p-8 bg-[#0d0d0e]/40 border border-white/[0.03] rounded-[2rem] flex items-center justify-between">
             <div className="flex items-center gap-6">
                <div className="flex -space-x-3">
                   {[1,2,3].map(i => (
                     <div key={i} className="w-10 h-10 rounded-full border-2 border-[#0d0d0e] bg-white/5 flex items-center justify-center text-[10px] font-mono text-gray-500">
                        OP{i}
                     </div>
                   ))}
                </div>
                <div className="text-[10px] font-mono text-gray-600 uppercase tracking-widest">Authorized Admins with Write Access</div>
             </div>
             <div className="flex items-center gap-3">
                <Mail className="w-4 h-4 text-gray-700" />
                <span className="text-[10px] font-mono text-gray-700 uppercase tracking-widest underline cursor-pointer hover:text-gray-400">Export Registry Snapshot</span>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
}
