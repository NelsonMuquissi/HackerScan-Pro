'use client';

import { useState, useEffect } from 'react';
import { 
  Webhook as WebhookIcon, 
  Plus, 
  Trash2, 
  Key, 
  Activity, 
  CheckCircle, 
  XCircle, 
  ExternalLink, 
  RotateCcw, 
  RefreshCw,
  PlusCircle,
  Copy,
  Terminal,
  ShieldCheck,
  Send
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  listWebhooks, 
  createWebhook, 
  updateWebhook, 
  deleteWebhook, 
  resetWebhookSecret, 
  testWebhook 
} from '@/lib/api';
import { cn } from '@/lib/utils';

export function WebhookContent() {
  const [webhooks, setWebhooks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    url: '',
    events: ['scan.completed']
  });

  useEffect(() => {
    loadWebhooks();
  }, []);

  async function loadWebhooks() {
    setLoading(true);
    try {
      const data = await listWebhooks();
      setWebhooks(data);
    } catch (err) {
      console.error('Failed to load webhooks:', err);
    } finally {
      setLoading(false);
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const result = await createWebhook(formData);
      setWebhooks([result, ...webhooks]);
      setShowAddForm(false);
      setFormData({ name: '', url: '', events: ['scan.completed'] });
    } catch (err) {
      alert('Failed to create webhook');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTest = async (id: string) => {
    setTestingId(id);
    try {
      await testWebhook(id);
      alert('Test event dispatched successfully.');
      loadWebhooks(); // Refresh to see last_triggered
    } catch (err) {
      alert('Failed to dispatch test event.');
    } finally {
      setTestingId(null);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this webhook connector?')) return;
    try {
      await deleteWebhook(id);
      setWebhooks(webhooks.filter(w => w.id !== id));
    } catch (err) {
      alert('Failed to delete webhook.');
    }
  };

  const handleResetSecret = async (id: string) => {
    if (!confirm('Rotate the secret token? You must update your receiving endpoint immediately.')) return;
    try {
      const { secret_token } = await resetWebhookSecret(id);
      alert(`New secret token generated: ${secret_token}`);
      loadWebhooks();
    } catch (err) {
      alert('Failed to reset secret.');
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    alert('Copied to clipboard!');
  };

  if (loading) {
     return (
       <div className="flex items-center justify-center py-20">
         <RefreshCw className="w-5 h-5 text-neon-green animate-spin" />
         <span className="ml-3 font-mono text-gray-400 text-xs uppercase tracking-widest">Scanning Dispatcher Matrix...</span>
       </div>
     );
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2 uppercase tracking-tighter">
            <WebhookIcon className="w-5 h-5 text-neon-green" />
            Outbound Webhooks
          </h2>
          <p className="text-[10px] text-gray-500 font-mono mt-1 uppercase tracking-widest italic">
            Synchronize intelligence with external SOC/SIEM platforms
          </p>
        </div>
        <button 
          onClick={() => setShowAddForm(!showAddForm)}
          className={cn(
            "flex items-center gap-2 px-4 py-2 rounded-lg font-bold font-mono text-xs transition-all uppercase tracking-widest",
            showAddForm ? "bg-red-500/10 text-red-500 border border-red-500/20" : "bg-neon-green text-black hover:bg-opacity-90"
          )}
        >
          {showAddForm ? <XCircle className="w-4 h-4" /> : <PlusCircle className="w-4 h-4" />}
          {showAddForm ? "Cancel" : "New Endpoint"}
        </button>
      </div>

      <AnimatePresence>
        {showAddForm && (
          <motion.div 
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <form onSubmit={handleCreate} className="bg-card-bg border border-card-border rounded-xl p-8 space-y-6 shadow-[0_0_30px_rgba(57,255,20,0.05)]">
              <div className="grid md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="text-[10px] font-bold font-mono text-gray-500 uppercase tracking-widest ml-1">Friendly Name</label>
                  <input 
                    type="text" 
                    required
                    value={formData.name}
                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g. SOC Automation"
                    className="w-full bg-black/50 border border-white/10 rounded-lg p-3 text-sm font-mono focus:border-neon-green outline-none transition-all"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-bold font-mono text-gray-500 uppercase tracking-widest ml-1">Endpoint URL (HTTPS)</label>
                  <input 
                    type="url" 
                    required
                    value={formData.url}
                    onChange={e => setFormData({ ...formData, url: e.target.value })}
                    placeholder="https://your-api.com/webhooks"
                    className="w-full bg-black/50 border border-white/10 rounded-lg p-3 text-sm font-mono focus:border-neon-green outline-none transition-all"
                  />
                </div>
              </div>

              <div className="space-y-4">
                 <label className="text-[10px] font-bold font-mono text-gray-500 uppercase tracking-widest ml-1">Operational Triggers</label>
                 <div className="flex flex-wrap gap-3">
                    {["scan.completed", "scan.failed", "finding.new"].map(event => (
                      <label key={event} className={cn(
                        "flex items-center gap-2 px-3 py-1.5 rounded border border-white/5 cursor-pointer transition-all",
                        formData.events.includes(event) ? "bg-neon-green/10 border-neon-green/30 text-neon-green" : "bg-black/50 text-gray-500"
                      )}>
                        <input 
                          type="checkbox" 
                          className="sr-only"
                          checked={formData.events.includes(event)}
                          onChange={() => {
                            const newEvents = formData.events.includes(event)
                              ? formData.events.filter(e => e !== event)
                              : [...formData.events, event];
                            setFormData({ ...formData, events: newEvents });
                          }}
                        />
                        <span className="text-[10px] font-mono font-bold uppercase tracking-widest">{event.replace('.', ' ')}</span>
                      </label>
                    ))}
                 </div>
              </div>

              <div className="pt-4 border-t border-white/5 flex justify-end">
                 <button 
                   type="submit" 
                   disabled={isSubmitting}
                   className="flex items-center gap-2 px-6 py-3 bg-neon-green text-black font-bold font-mono text-xs rounded-lg hover:bg-opacity-90 disabled:opacity-50 uppercase tracking-[0.1em]"
                 >
                   {isSubmitting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
                   Authorize Hub Connector
                 </button>
              </div>
            </form>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="space-y-4">
        {webhooks.length > 0 ? webhooks.map((webhook) => (
          <div key={webhook.id} className="bg-card-bg border border-card-border rounded-xl p-6 group hover:border-white/20 transition-all">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex items-start gap-4">
                <div className={cn(
                  "w-10 h-10 rounded-lg flex items-center justify-center border",
                  webhook.is_active ? "bg-neon-green/5 border-neon-green/20" : "bg-gray-800/10 border-gray-700"
                )}>
                  <Activity className={cn("w-5 h-5", webhook.is_active ? "text-neon-green" : "text-gray-600")} />
                </div>
                <div>
                  <div className="flex items-center gap-3">
                    <h3 className="font-bold text-foreground">{webhook.name}</h3>
                    {!webhook.is_active && (
                      <span className="text-[8px] font-bold font-mono px-1.5 py-0.5 rounded border border-red-500/30 text-red-500 bg-red-500/5 uppercase tracking-widest">Offline</span>
                    )}
                  </div>
                  <p className="text-[11px] font-mono text-gray-500 mt-1 flex items-center gap-1.5 opacity-60 group-hover:opacity-100 transition-opacity">
                    <Terminal className="w-3 h-3" />
                    {webhook.url}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button 
                  onClick={() => handleTest(webhook.id)}
                  className="px-3 py-1.5 bg-white/5 border border-white/10 rounded flex items-center gap-2 text-[10px] font-mono font-bold hover:bg-white/10 transition-all uppercase tracking-widest text-blue-400"
                >
                  {testingId === webhook.id ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
                  Test
                </button>
                <button 
                   onClick={() => handleResetSecret(webhook.id)}
                   className="p-2 text-gray-600 hover:text-yellow-400 hover:bg-yellow-400/10 rounded transition-all"
                   title="Rotate Secret"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
                <button 
                  onClick={() => handleDelete(webhook.id)}
                  className="p-2 text-gray-600 hover:text-red-500 hover:bg-red-500/10 rounded transition-all"
                  title="Remove Connector"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-white/5 grid grid-cols-2 md:grid-cols-4 gap-4">
               <div className="space-y-1">
                  <span className="text-[9px] font-mono text-gray-600 uppercase tracking-widest">Last Triggered</span>
                  <p className="text-[10px] font-mono text-gray-400">
                    {webhook.last_triggered_at ? new Date(webhook.last_triggered_at).toLocaleString() : 'NEVER'}
                  </p>
               </div>
               <div className="space-y-1">
                  <span className="text-[9px] font-mono text-gray-600 uppercase tracking-widest">Last Status</span>
                  <div className="flex items-center gap-2">
                    <div className={cn(
                      "w-1.5 h-1.5 rounded-full",
                      webhook.last_status_code >= 200 && webhook.last_status_code < 300 ? "bg-neon-green" : 
                      webhook.last_status_code ? "bg-red-500" : "bg-gray-700"
                    )} />
                    <p className="text-[10px] font-mono text-gray-400">
                      {webhook.last_status_code || '---'}
                    </p>
                  </div>
               </div>
               <div className="space-y-1 md:col-span-2">
                  <span className="text-[9px] font-mono text-gray-600 uppercase tracking-widest">Secret Identification</span>
                  <div className="flex items-center gap-2">
                    <code className="text-[10px] font-mono text-gray-500 bg-black/30 px-2 py-0.5 rounded border border-white/5">
                      {webhook.secret_token.slice(0, 10)}********************
                    </code>
                    <button 
                      onClick={() => copyToClipboard(webhook.secret_token)}
                      className="text-gray-600 hover:text-white transition-colors"
                    >
                      <Copy className="w-3 h-3" />
                    </button>
                  </div>
               </div>
            </div>
          </div>
        )) : (
          <div className="py-20 text-center border border-dashed border-white/10 rounded-xl space-y-4">
             <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-white/5">
                <Terminal className="w-6 h-6 text-gray-600" />
             </div>
             <div className="space-y-1">
                <p className="text-sm font-bold text-gray-400 uppercase tracking-[0.2em]">Deployment Required</p>
                <p className="text-[10px] font-mono text-gray-600 uppercase italic">No active webhook connectors found in this workspace grid.</p>
             </div>
          </div>
        )}
      </div>
    </div>
  );
}
