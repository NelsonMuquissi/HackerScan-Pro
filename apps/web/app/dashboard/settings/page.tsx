'use client';

import { useState, useEffect } from 'react';
import { 
  Settings as SettingsIcon, 
  User, 
  Key, 
  Bell, 
  Loader2, 
  ShieldCheck, 
  Copy, 
  Trash2, 
  Plus, 
  CheckCircle,
  AlertCircle,
  Users,
  Activity,
  Network,
  Share2,
  Mail,
  Database
} from 'lucide-react';
import { motion } from 'framer-motion';
import { 
  getMe, 
  listApiKeys, 
  createApiKey, 
  revokeApiKey, 
  getNotificationPreferences, 
  updateNotificationPreference 
} from '@/lib/api';
import { useAuthStore } from '@/store/useAuthStore';
import { cn } from '@/lib/utils';
import { TeamContent } from '@/components/workspaces/TeamContent';
import { AuditLogContent } from '@/components/dashboard/AuditLogContent';
import { WebhookContent } from '@/components/integrations/WebhookContent';
import { BountyManagement } from '@/components/workspaces/BountyManagement';

const TABS = [
  { id: 'profile', label: 'Identity', icon: User },
  { id: 'team', label: 'Operators', icon: Users },
  { id: 'notifications', label: 'Alert Feeds', icon: Bell },
  { id: 'api', label: 'Nexus Access', icon: Key },
  { id: 'connectors', label: 'Hub Connectors', icon: Network },
  { id: 'bounty', label: 'Hacker Hub', icon: ShieldCheck },
  { id: 'activity', label: 'Governance', icon: Activity },
];

export default function SettingsPage() {
  const authUser = useAuthStore((s) => s.user);
  const [activeTab, setActiveTab] = useState('profile');
  const [profile, setProfile] = useState<any>(null);
  const [apiKeys, setApiKeys] = useState<any[]>([]);
  const [preferences, setPreferences] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  // New API Key state
  const [newKey, setNewKey] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        const [me, keysData, prefsData] = await Promise.all([
          getMe(),
          listApiKeys(),
          getNotificationPreferences()
        ]);
        setProfile(me);
        
        // Synchronize store workspaceId
        if (me?.workspace_id) {
          useAuthStore.getState().setWorkspaceId(me.workspace_id);
        }
        
        // Handle Api Keys
        const keysList = Array.isArray(keysData) ? keysData : (keysData as any)?.results ?? [];
        setApiKeys(keysList);
        
        // Handle Preferences
        const prefsList = Array.isArray(prefsData) ? prefsData : (prefsData as any)?.results ?? [];
        setPreferences(prefsList);
      } catch (error) {
        console.error('Failed to load settings:', error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const handleTogglePreference = async (prefId: string, field: string, currentValue: boolean) => {
    try {
      const updated = await updateNotificationPreference(prefId, { [field]: !currentValue });
      setPreferences(preferences.map(p => p.id === prefId ? updated : p));
    } catch (e) {
      alert('Failed to update preference');
    }
  };

  const handleGenerateKey = async () => {
    const name = prompt('Key Name (e.g. CI/CD Pipeline):');
    if (!name) return;

    setIsGenerating(true);
    try {
      const result = await createApiKey(name);
      setNewKey(result.key);
      setApiKeys([result, ...apiKeys]);
    } catch (e) {
      alert('Failed to generate key');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleRevokeKey = async (id: string) => {
    if (!confirm('Are you sure you want to revoke this key? Programmatic access using this key will stop immediately.')) return;
    try {
      await revokeApiKey(id);
      setApiKeys(apiKeys.filter(k => k.id !== id));
    } catch (e) {
      alert('Failed to revoke key');
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    alert('Copied to clipboard!');
  };

  const handleTerminateSessions = () => {
    if (confirm('Are you sure you want to terminate all active sessions? You will be logged out and all Nexus connections cleared.')) {
      useAuthStore.getState().logout();
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 text-neon-green animate-spin" />
        <span className="ml-3 font-mono text-gray-400">Loading settings archive...</span>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-5xl">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground flex items-center gap-3 tracking-tighter">
            <SettingsIcon className="w-8 h-8 text-neon-green" />
            CONTROL CENTER
          </h1>
          <p className="text-xs text-gray-500 font-mono mt-1 uppercase tracking-widest">
            Manage your workspace perimeter and intelligence parameters
          </p>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex overflow-x-auto pb-1 border-b border-white/5 no-scrollbar gap-1">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "flex items-center gap-2 px-6 py-4 text-xs font-bold font-mono tracking-widest transition-all whitespace-nowrap",
              activeTab === tab.id 
                ? "text-neon-green border-b-2 border-neon-green" 
                : "text-gray-500 hover:text-gray-300 border-b-2 border-transparent"
            )}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label.toUpperCase()}
          </button>
        ))}
      </div>

      <div className="pt-4">
        {activeTab === 'profile' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="md:col-span-2 space-y-6">
              <section className="bg-card-bg border border-card-border rounded-xl p-8 space-y-8">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-full bg-gradient-to-br from-gray-800 to-black border-2 border-neon-green/30 flex items-center justify-center text-2xl font-bold text-neon-green">
                    {profile?.full_name?.charAt(0) || authUser?.email?.[0]?.toUpperCase() || '?'}
                  </div>
                  <div>
                    <h3 className="text-xl font-bold">{profile?.full_name || 'Hacker Operator'}</h3>
                    <p className="text-xs text-gray-500 font-mono">{profile?.email || authUser?.email}</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div className="space-y-2">
                    <label className="text-gray-500 font-mono text-[10px] uppercase font-bold tracking-widest ml-1">Account Identity</label>
                    <div className="bg-black/50 border border-white/10 rounded-lg p-4 font-mono text-sm">
                      {profile?.email}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <label className="text-gray-500 font-mono text-[10px] uppercase font-bold tracking-widest ml-1">Security Clearance</label>
                    <div className="bg-black/50 border border-white/10 rounded-lg p-4 font-mono text-sm text-neon-green font-bold">
                      {profile?.role?.toUpperCase()}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <label className="text-gray-500 font-mono text-[10px] uppercase font-bold tracking-widest ml-1">Operational Plan</label>
                    <div className="bg-black/50 border border-white/10 rounded-lg p-4 font-mono text-sm text-blue-400 font-bold">
                      {profile?.plan || 'FREELANCER'}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <label className="text-gray-500 font-mono text-[10px] uppercase font-bold tracking-widest ml-1">MFA Status</label>
                    <div className="bg-black/50 border border-white/10 rounded-lg p-4 font-mono text-sm flex items-center gap-2">
                      <div className={cn("w-2 h-2 rounded-full", profile?.totp_enabled ? "bg-neon-green" : "bg-red-500")} />
                      {profile?.totp_enabled ? 'FORTIFIED' : 'VULNERABLE'}
                    </div>
                  </div>
                </div>
              </section>
            </div>
            <div className="space-y-6">
              <section className="bg-[#0a0a0a] border border-white/5 rounded-xl p-6 space-y-4">
                 <h4 className="text-[10px] font-bold font-mono text-gray-500 uppercase tracking-widest">Active Sessions</h4>
                 <div className="space-y-3">
                   <div className="flex items-center justify-between text-[11px] font-mono">
                     <span className="text-gray-400">Current IP</span>
                     <span className="text-white">192.168.1.45</span>
                   </div>
                   <div className="flex items-center justify-between text-[11px] font-mono">
                     <span className="text-gray-400">Last Login</span>
                     <span className="text-white">Just now</span>
                   </div>
                 </div>
                 <button 
                    onClick={handleTerminateSessions}
                    className="w-full mt-4 py-2 bg-red-500/10 text-red-500 text-[10px] font-bold font-mono border border-red-500/20 rounded hover:bg-red-500/20 transition-all uppercase"
                  >
                   Terminate Sessions
                 </button>
              </section>
            </div>
          </div>
        )}

        {activeTab === 'team' && <TeamContent />}

        {activeTab === 'notifications' && (
          <section className="bg-card-bg border border-card-border rounded-xl p-8 max-w-3xl">
             <div className="mb-8">
               <h2 className="text-xl font-bold text-foreground flex items-center gap-2 uppercase tracking-tighter">
                 <Bell className="w-5 h-5 text-blue-400" />
                 Signal Configuration
               </h2>
               <p className="text-xs text-gray-500 font-mono mt-1 uppercase tracking-widest italic">
                 Define triggers for tactical alert delivery
               </p>
             </div>

             <div className="space-y-6">
               {preferences.length > 0 ? preferences.map((pref) => (
                 <div key={pref.id} className="bg-black/50 border border-white/10 rounded-xl p-6">
                   <div className="flex items-center justify-between mb-6">
                     <div className="flex items-center gap-3">
                       <Mail className="w-5 h-5 text-gray-400" />
                       <h3 className="font-bold uppercase tracking-widest text-sm">{pref.channel} Feed</h3>
                     </div>
                     <label className="relative inline-flex items-center cursor-pointer">
                       <input 
                         type="checkbox" 
                         checked={pref.is_active} 
                         onChange={() => handleTogglePreference(pref.id, 'is_active', pref.is_active)}
                         className="sr-only peer" 
                       />
                       <div className="w-10 h-5 bg-gray-800 rounded-full peer peer-checked:bg-blue-500 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-5" />
                     </label>
                   </div>
                   
                   <div className="grid md:grid-cols-2 gap-4">
                     <div className="flex items-center justify-between p-4 rounded-lg bg-white/5 border border-white/5">
                        <span className="text-[10px] font-bold font-mono text-gray-400 uppercase tracking-widest">Successful Recon</span>
                        <input 
                          type="checkbox" 
                          checked={pref.notify_on_complete} 
                          onChange={() => handleTogglePreference(pref.id, 'notify_on_complete', pref.notify_on_complete)}
                          className="accent-neon-green"
                        />
                     </div>
                     <div className="flex items-center justify-between p-4 rounded-lg bg-white/5 border border-white/5">
                        <span className="text-[10px] font-bold font-mono text-gray-400 uppercase tracking-widest">System Failures</span>
                        <input 
                          type="checkbox" 
                          checked={pref.notify_on_failed} 
                          onChange={() => handleTogglePreference(pref.id, 'notify_on_failed', pref.notify_on_failed)}
                          className="accent-red-500"
                        />
                     </div>
                   </div>
                 </div>
               )) : (
                 <div className="text-center py-20 border border-dashed border-white/10 rounded-xl text-gray-600 font-mono text-xs uppercase tracking-[0.2em]">
                   NO ACTIVE FEEDS CONFIGURED
                 </div>
               )}
             </div>
          </section>
        )}

        {activeTab === 'api' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 space-y-6">
              <section className="bg-card-bg border border-card-border rounded-xl p-8 space-y-8">
                 <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-xl font-bold flex items-center gap-2 uppercase tracking-tighter">
                        <Key className="w-5 h-5 text-yellow-400" />
                        Access Credentials
                      </h2>
                      <p className="text-[10px] text-gray-500 font-mono mt-1 uppercase tracking-widest">Nexus interface for programmatic operations</p>
                    </div>
                    <button 
                      onClick={handleGenerateKey}
                      className="bg-white/5 border border-white/10 text-white px-4 py-2 rounded-lg font-bold text-xs font-mono flex items-center gap-2 hover:bg-white/10 transition-all uppercase tracking-widest"
                    >
                      <Plus className="w-3 h-3" />
                      NEW KEY
                    </button>
                 </div>

                 {newKey && (
                    <motion.div 
                      initial={{ scale: 0.9, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      className="bg-yellow-400/5 border border-yellow-400/20 rounded-xl p-6 space-y-4 shadow-[0_0_20px_rgba(250,204,21,0.05)]"
                    >
                      <div className="flex items-center gap-2 text-yellow-400">
                        <AlertCircle className="w-4 h-4" />
                        <span className="text-[10px] font-bold font-mono uppercase tracking-widest">DEEP ENCRYPTION KEY GENERATED</span>
                      </div>
                      <p className="text-[10px] font-mono text-gray-400 uppercase italic">Key shown once. Store in secured hardware/vault.</p>
                      <div className="relative group">
                        <code className="block w-full bg-black border border-white/10 rounded-lg p-4 text-[11px] font-mono text-yellow-400 break-all pr-12">
                          {newKey}
                        </code>
                        <button 
                          onClick={() => copyToClipboard(newKey)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white transition-colors"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                      </div>
                      <button 
                        onClick={() => setNewKey(null)}
                        className="w-full py-2 text-[9px] font-bold font-mono text-gray-600 hover:text-gray-400 uppercase transition-all"
                      >
                        [ CLOSE CLEARANCE PORTAL ]
                      </button>
                    </motion.div>
                  )}

                 <div className="divide-y divide-white/5 border-t border-white/5 mt-8">
                   {apiKeys.length > 0 ? apiKeys.map((key) => (
                    <div key={key.id} className="py-6 flex items-center justify-between group">
                      <div className="flex items-center gap-5">
                         <div className="w-10 h-10 rounded-lg bg-black border border-white/5 flex items-center justify-center">
                            <Database className="w-5 h-5 text-gray-600" />
                         </div>
                         <div>
                           <div className="text-sm font-bold text-foreground">{key.name}</div>
                           <div className="text-[10px] font-mono text-gray-500 mt-1 uppercase tracking-tighter">
                             ID: <span className="text-gray-300">{key.id.slice(0,8)}</span> • Prefix: <span className="text-yellow-400">{key.key_prefix}</span>
                           </div>
                         </div>
                      </div>
                      <button 
                        onClick={() => handleRevokeKey(key.id)}
                        className="p-2 text-gray-600 hover:text-red-500 hover:bg-red-500/10 rounded transition-all opacity-0 group-hover:opacity-100"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                   )) : (
                    <div className="py-20 text-center text-xs font-mono text-gray-600 uppercase tracking-[0.3em]">
                      NO ACTIVE CREDENTIALS
                    </div>
                   )}
                 </div>
              </section>
            </div>
            <div className="space-y-6">
              <section className="bg-neon-green/5 border border-neon-green/10 rounded-xl p-8 space-y-4">
                 <h4 className="text-xs font-bold font-mono text-neon-green uppercase tracking-widest flex items-center gap-2">
                   <ShieldCheck className="w-4 h-4" />
                   Crypto Protocol
                 </h4>
                 <p className="text-[10px] leading-relaxed text-gray-500 font-mono uppercase">
                   Nexus keys utilize dual-hash verification. Programs must include the X-API-Key header.
                 </p>
                 <div className="pt-4">
                    <button className="w-full py-3 bg-white/5 border border-white/10 rounded text-[10px] font-bold font-mono text-gray-400 hover:bg-white/10 uppercase tracking-widest transition-all">
                      Rotation Policy
                    </button>
                 </div>
              </section>
            </div>
          </div>
        )}

        {activeTab === 'connectors' && <WebhookContent />}
        {activeTab === 'bounty' && <BountyManagement />}
        {activeTab === 'activity' && <AuditLogContent />}
      </div>
    </div>
  );
}
