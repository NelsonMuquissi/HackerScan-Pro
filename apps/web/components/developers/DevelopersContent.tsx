'use client';

import { useState, useEffect } from 'react';
import { 
  Terminal, 
  Key, 
  Plus, 
  Trash2, 
  Copy, 
  Check, 
  Eye, 
  EyeOff, 
  ExternalLink,
  Code2,
  ShieldCheck,
  AlertCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { 
  listApiKeys, 
  createApiKey, 
  revokeApiKey 
} from '@/lib/api';

export function DevelopersContent() {
  const [keys, setKeys] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [revealedKey, setRevealedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    loadKeys();
  }, []);

  async function loadKeys() {
    setLoading(true);
    try {
      const data = await listApiKeys();
      // Handle both plain arrays and paginated responses { results: [...] }
      let list: any[] = [];
      if (Array.isArray(data)) {
        list = data;
      } else if (data && typeof data === 'object' && 'results' in data) {
        list = (data as any).results;
      }
      setKeys(list);
    } catch (err) {
      console.error('Failed to load keys:', err);
      setKeys([]);
    } finally {
      setLoading(false);
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      const result = await createApiKey(newKeyName);
      setRevealedKey(result.key); // The raw key is only returned once
      setNewKeyName('');
      await loadKeys();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create key');
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (id: string) => {
    if (!confirm('Are you sure you want to revoke this key? This action is permanent.')) return;
    try {
      await revokeApiKey(id);
      setKeys(prev => prev.filter(k => k.id !== id));
    } catch (err) {
      console.error('Failed to revoke key:', err);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
        <div className="w-12 h-12 border-4 border-neon-green border-t-transparent rounded-full animate-spin" />
        <p className="font-mono text-neon-green text-xs">ESTABLISHING ENCRYPTED SESSION...</p>
      </div>
    );
  }

  return (
    <div className="space-y-10 pb-20">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <Terminal className="w-8 h-8 text-neon-green" />
          DEVELOPER CONSOLE
        </h1>
        <p className="text-gray-400 font-mono mt-2 uppercase tracking-widest text-xs">
          PROGRAMMATIC ACCESS & INTEGRATIONS
        </p>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* API Keys Management */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-card-bg border border-card-border rounded-2xl overflow-hidden">
            <div className="p-6 border-b border-card-border flex items-center justify-between bg-[#0a0a0a]">
              <h3 className="font-bold flex items-center gap-2">
                <Key className="w-4 h-4 text-neon-green" />
                API KEYS
              </h3>
              <button 
                onClick={() => setRevealedKey(null)}
                className="text-xs font-mono text-neon-green hover:underline"
              >
                GENERATE NEW
              </button>
            </div>

            <div className="divide-y divide-card-border">
              {keys.length === 0 ? (
                <div className="p-12 text-center text-gray-500 font-mono text-sm">
                  NO ACTIVE KEYS SECURED.
                </div>
              ) : (
                keys.map((key) => (
                  <div key={key.id} className="p-6 flex items-center justify-between hover:bg-white/[0.02] transition-colors">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-foreground">{key.name}</span>
                        <span className="text-[10px] bg-black px-2 py-0.5 rounded border border-card-border text-gray-500 font-mono">
                          {key.key_prefix}***
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-[10px] font-mono text-gray-500">
                        <span>CREATED: {new Date(key.created_at).toLocaleDateString()}</span>
                        <span>LAST USED: {key.last_used_at ? new Date(key.last_used_at).toLocaleDateString() : 'NEVER'}</span>
                      </div>
                    </div>
                    <button 
                      onClick={() => handleRevoke(key.id)}
                      className="p-2 text-gray-600 hover:text-neon-red transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Docs / Code Snippets */}
          <div className="bg-card-bg border border-card-border rounded-2xl p-6 space-y-4">
            <h3 className="font-bold flex items-center gap-2 mb-4">
              <Code2 className="w-4 h-4 text-neon-green" />
              IMPLEMENTATION GUIDE
            </h3>
            <div className="space-y-6">
              <div className="space-y-2">
                <p className="text-sm text-gray-400">Trigger a scan via cURL:</p>
                <pre className="bg-black border border-card-border p-4 rounded-lg text-xs font-mono text-neon-green overflow-x-auto">
                  {`curl -X POST "${process.env.NEXT_PUBLIC_API_URL || 'https://api.hackerscan.pro/v1'}/scans/quick/" \\
  -H "X-API-Key: YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"target_url": "https://example.com"}'`}
                </pre>
              </div>
              <div className="flex items-center gap-2 text-xs text-neon-green font-mono">
                <ExternalLink className="w-3 h-3" />
                <a href="#" className="hover:underline">VIEW FULL API REFERENCE [v1.0]</a>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar Actions */}
        <div className="space-y-6">
          <div className="bg-neon-green-dim/10 border border-neon-green/20 rounded-2xl p-6 space-y-4">
            <ShieldCheck className="w-8 h-8 text-neon-green" />
            <h4 className="font-bold">SECURITY ADVISORY</h4>
            <p className="text-xs text-gray-400 leading-relaxed font-mono">
              API Keys bypass MFA and grant direct access to your workspace. 
              Never commit them to version control. Use environment variables 
              in your CI/CD pipelines (e.g., GitHub Secrets).
            </p>
          </div>

          <div className="bg-card-bg border border-card-border rounded-2xl p-6">
            <h4 className="font-bold mb-4 flex items-center gap-2">
              <Plus className="w-4 h-4 text-neon-green" />
              NEW ACCESS KEY
            </h4>
            <form onSubmit={handleCreate} className="space-y-4">
              <input 
                required
                type="text"
                placeholder="Key Name (e.g. Jenkins CI)"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                className="w-full bg-black border border-card-border rounded-lg p-3 text-xs focus:border-neon-green outline-none"
              />
              <button 
                disabled={creating || !newKeyName}
                className="w-full py-3 bg-neon-green text-black font-bold text-xs rounded-lg hover:bg-opacity-90 transition-all disabled:opacity-50"
              >
                {creating ? 'GENERATING...' : 'GENERATE KEY'}
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* Reveal Modal */}
      <AnimatePresence>
        {revealedKey && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90 backdrop-blur-md">
            <motion.div 
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="bg-card-bg border border-neon-green/30 rounded-2xl p-8 max-w-lg w-full shadow-[0_0_50px_-12px_rgba(57,255,20,0.2)]"
            >
              <div className="flex items-center gap-3 text-neon-yellow mb-6">
                <AlertCircle className="w-6 h-6" />
                <h3 className="text-xl font-bold">SAVE THIS KEY NOW</h3>
              </div>
              <p className="text-sm text-gray-300 mb-6 font-mono leading-relaxed">
                This key will only be shown <span className="text-neon-red font-bold">ONCE</span>. 
                If you lose it, you will need to revoke and generate a new one.
              </p>
              
              <div className="relative group">
                <input 
                  readOnly
                  type="text"
                  value={revealedKey}
                  className="w-full bg-black border-2 border-neon-green/30 rounded-xl p-5 font-mono text-sm pr-12 text-neon-green"
                />
                <button 
                  onClick={() => copyToClipboard(revealedKey)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 p-2 hover:bg-neon-green/10 rounded-lg transition-colors"
                >
                  {copied ? <Check className="w-5 h-5 text-neon-green" /> : <Copy className="w-5 h-5 text-gray-400" />}
                </button>
              </div>

              <div className="mt-8">
                <button 
                  onClick={() => setRevealedKey(null)}
                  className="w-full py-4 bg-neon-green text-black font-bold rounded-xl hover:bg-opacity-90 transition-all shadow-lg"
                >
                  I HAVE SECURED MY KEY
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
