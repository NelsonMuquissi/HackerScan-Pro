'use client';

import { useEffect, useState } from 'react';
import { adminListModules, adminCreateModule, adminUpdateModule, adminDeleteModule } from '@/lib/api';
import { ShoppingBag, Plus, Edit, Trash2, Check, X, Shield, DollarSign } from 'lucide-react';
import { toast } from 'sonner';

export default function MarketplaceManagement() {
  const [modules, setModules] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isAdding, setIsAdding] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  
  const [formData, setFormData] = useState({
    name: '',
    slug: '',
    description: '',
    short_description: '',
    price: '0.00',
    icon: 'Shield',
    is_active: true
  });

  useEffect(() => {
    loadModules();
  }, []);

  async function loadModules() {
    try {
      const data = await adminListModules();
      setModules(data);
    } catch (error) {
      toast.error("Failed to load modules");
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit() {
    try {
      if (editingId) {
        await adminUpdateModule(editingId, formData);
        toast.success("Module updated");
      } else {
        await adminCreateModule(formData);
        toast.success("Module created");
      }
      setIsAdding(false);
      setEditingId(null);
      loadModules();
    } catch (error) {
      toast.error("Operation failed");
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Are you sure you want to delete this module?")) return;
    try {
      await adminDeleteModule(id);
      toast.success("Module deleted");
      loadModules();
    } catch (error) {
      toast.error("Deletion failed");
    }
  }

  const startEdit = (mod: any) => {
    setEditingId(mod.id);
    setFormData({
      name: mod.name,
      slug: mod.slug,
      description: mod.description,
      short_description: mod.short_description || '',
      price: mod.price,
      icon: mod.icon,
      is_active: mod.is_active
    });
    setIsAdding(true);
  };

  if (loading) return <div className="text-neon-green animate-pulse font-mono">Loading marketplace inventory...</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-mono font-bold text-foreground">Marketplace Admin</h1>
        <button 
          onClick={() => {
            setIsAdding(true);
            setEditingId(null);
            setFormData({ name: '', slug: '', description: '', short_description: '', price: '0.00', icon: 'Shield', is_active: true });
          }}
          className="flex items-center gap-2 bg-neon-green text-black px-4 py-2 rounded font-mono text-sm font-bold hover:bg-neon-green/80 transition-colors"
        >
          <Plus className="w-4 h-4" /> Add Module
        </button>
      </div>

      {isAdding && (
        <div className="bg-card-bg border border-neon-green p-6 rounded-lg space-y-4 animate-in fade-in slide-in-from-top-4">
          <h2 className="text-xl font-mono font-bold">{editingId ? 'Edit Module' : 'New Security Module'}</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-mono text-gray-400 uppercase">Name</label>
              <input 
                value={formData.name}
                onChange={e => setFormData({...formData, name: e.target.value})}
                className="w-full bg-background border border-card-border rounded px-3 py-2 font-mono text-sm focus:border-neon-green outline-none"
                placeholder="Active Directory Audit"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-mono text-gray-400 uppercase">Slug</label>
              <input 
                value={formData.slug}
                onChange={e => setFormData({...formData, slug: e.target.value})}
                className="w-full bg-background border border-card-border rounded px-3 py-2 font-mono text-sm focus:border-neon-green outline-none"
                placeholder="ad-audit"
              />
            </div>
            <div className="space-y-2 col-span-2">
              <label className="text-xs font-mono text-gray-400 uppercase">Short Description</label>
              <input 
                value={formData.short_description}
                onChange={e => setFormData({...formData, short_description: e.target.value})}
                className="w-full bg-background border border-card-border rounded px-3 py-2 font-mono text-sm focus:border-neon-green outline-none"
                placeholder="Brief summary for cards"
              />
            </div>
            <div className="space-y-2 col-span-2">
              <label className="text-xs font-mono text-gray-400 uppercase">Full Description (Markdown)</label>
              <textarea 
                value={formData.description}
                onChange={e => setFormData({...formData, description: e.target.value})}
                className="w-full h-32 bg-background border border-card-border rounded px-3 py-2 font-mono text-sm focus:border-neon-green outline-none resize-none"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-mono text-gray-400 uppercase">Price (USD)</label>
              <div className="relative">
                <DollarSign className="absolute left-3 top-2.5 w-4 h-4 text-gray-500" />
                <input 
                  type="number"
                  value={formData.price}
                  onChange={e => setFormData({...formData, price: e.target.value})}
                  className="w-full bg-background border border-card-border rounded pl-9 pr-3 py-2 font-mono text-sm focus:border-neon-green outline-none"
                />
              </div>
            </div>
            <div className="flex items-end gap-4">
              <button 
                onClick={handleSubmit}
                className="flex-1 bg-neon-green text-black py-2 rounded font-mono font-bold hover:bg-neon-green/80"
              >
                Save Module
              </button>
              <button 
                onClick={() => setIsAdding(false)}
                className="flex-1 bg-background border border-card-border py-2 rounded font-mono font-bold hover:bg-white/5"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {modules.map(mod => (
          <div key={mod.id} className="bg-card-bg border border-card-border rounded-lg p-6 space-y-4 hover:border-neon-green transition-all group">
            <div className="flex justify-between items-start">
              <div className="p-3 bg-background rounded-lg border border-card-border group-hover:border-neon-green transition-colors">
                 <Shield className="w-6 h-6 text-neon-green" />
              </div>
              <div className="flex gap-2">
                <button onClick={() => startEdit(mod)} className="text-gray-500 hover:text-white"><Edit className="w-4 h-4" /></button>
                <button onClick={() => handleDelete(mod.id)} className="text-gray-500 hover:text-red-500"><Trash2 className="w-4 h-4" /></button>
              </div>
            </div>
            <div>
              <h3 className="text-lg font-mono font-bold">{mod.name}</h3>
              <p className="text-xs text-gray-500 font-mono">slug: {mod.slug}</p>
            </div>
            <p className="text-sm text-gray-400 font-mono line-clamp-2">{mod.short_description || mod.description}</p>
            <div className="flex justify-between items-center pt-2">
              <span className="text-xl font-bold font-mono text-neon-green">${mod.price}</span>
              <span className={`text-[10px] uppercase px-2 py-1 rounded font-bold font-mono ${mod.is_active ? 'bg-emerald-500/20 text-emerald-500' : 'bg-red-500/20 text-red-500'}`}>
                {mod.is_active ? 'Active' : 'Inactive'}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
