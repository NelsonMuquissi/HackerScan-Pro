'use client';

import { useEffect, useState } from 'react';
import { adminListUsers, adminUpdateUser } from '@/lib/api';
import { 
  Users, Shield, CheckCircle, XCircle, MoreVertical, 
  Search, Filter, Mail, Calendar, User as UserIcon,
  ShieldAlert, ShieldCheck, Zap, Fingerprint, Activity,
  Lock, Globe, Cpu, Clock, Ban, RotateCcw, Key
} from 'lucide-react';
import { toast } from 'sonner';
import { AdminCommandCenter } from '@/components/ui/AdminCommandCenter';
import { HackerModal } from '@/components/ui/HackerModal';
import { useConfirm } from '@/hooks/useConfirm';
import { motion, AnimatePresence } from 'framer-motion';

export default function UserManagement() {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [editingUser, setEditingUser] = useState<any>(null);
  const [showModal, setShowModal] = useState(false);
  const [activeSection, setActiveSection] = useState('profile');
  const [isUpdateLoading, setIsUpdateLoading] = useState(false);
  const [form, setForm] = useState<any>({});
  const [roleFilter, setRoleFilter] = useState('all');
  const { confirm, state: confirmState, handleConfirm, handleCancel } = useConfirm();

  const sections = [
    { id: 'profile', label: 'Profile', icon: Fingerprint },
    { id: 'access', label: 'Access Control', icon: Shield },
    { id: 'quotas', label: 'Quota Override', icon: Activity },
  ];

  useEffect(() => { loadUsers(); }, []);

  async function loadUsers() {
    try {
      const data = await adminListUsers();
      setUsers(data);
    } catch (error) {
      toast.error("Failed to load users");
    } finally {
      setLoading(false);
    }
  }

  function openEdit(user: any) {
    setActiveSection('profile');
    setEditingUser(user);
    setForm({
      name: user.name || '',
      email: user.email || '',
      role: user.role || 'user',
      is_active: user.is_active ?? true,
    });
    setShowModal(true);
  }

  async function handleSave() {
    if (!editingUser) return;
    setIsUpdateLoading(true);
    try {
      await adminUpdateUser(editingUser.id, {
        role: form.role,
        is_active: form.is_active,
        name: form.name,
      });
      toast.success("User profile updated successfully");
      setShowModal(false);
      setEditingUser(null);
      loadUsers();
    } catch (error) {
      toast.error("Failed to update user");
    } finally {
      setIsUpdateLoading(false);
    }
  }

  async function handleToggleStatus(user: any) {
    const action = user.is_active ? 'suspend' : 'reactivate';
    const ok = await confirm({
      title: `${action === 'suspend' ? 'Suspend' : 'Reactivate'} "${user.name}"`,
      description: action === 'suspend' 
        ? 'This will immediately revoke access for this user across all workspaces.'
        : 'This will restore full access for this user.',
      confirmLabel: action === 'suspend' ? 'Suspend Access' : 'Reactivate User',
      variant: action === 'suspend' ? 'danger' : 'success' as any,
    });
    if (!ok) return;
    try {
      await adminUpdateUser(user.id, { is_active: !user.is_active });
      toast.success(`User ${action === 'suspend' ? 'suspended' : 'reactivated'}`);
      loadUsers();
    } catch {
      toast.error(`Failed to ${action} user`);
    }
  }

  const filteredUsers = users.filter(user => {
    const matchesSearch = user.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.email?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesRole = roleFilter === 'all' || user.role === roleFilter;
    return matchesSearch && matchesRole;
  });

  const stats = {
    total: users.length,
    active: users.filter(u => u.is_active).length,
    admins: users.filter(u => u.role === 'admin' || u.role === 'superadmin').length,
    suspended: users.filter(u => !u.is_active).length,
  };

  if (loading) return (
    <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
      <div className="relative">
        <div className="w-16 h-16 border-4 border-neon-green/10 border-t-neon-green rounded-full animate-spin" />
        <div className="absolute inset-0 bg-neon-green/20 blur-xl animate-pulse rounded-full" />
      </div>
      <p className="text-neon-green font-mono text-sm tracking-[0.2em] uppercase animate-pulse">Accessing user directory...</p>
    </div>
  );

  return (
    <div className="max-w-[1400px] mx-auto space-y-10 pb-20 animate-in fade-in duration-700">
      {/* Confirm Dialog */}
      <HackerModal
        open={confirmState.open}
        title={confirmState.title || ''}
        description={confirmState.description || ''}
        variant={(confirmState.variant as any) || 'danger'}
        onClose={handleCancel}
        footer={
          <div className="flex gap-4 pt-2">
            <button onClick={handleCancel} className="flex-1 px-8 py-4 bg-white/5 border border-white/10 rounded-2xl text-xs font-mono font-black text-gray-500 uppercase tracking-widest hover:text-white hover:bg-white/10 transition-all">
              Cancel
            </button>
            <button onClick={handleConfirm} className={`flex-[2] px-10 py-4 ${confirmState.variant === 'danger' ? 'bg-red-500 hover:bg-red-600 text-white' : 'bg-neon-green hover:bg-emerald-400 text-black'} rounded-2xl text-xs font-mono font-black uppercase tracking-[0.2em] transition-all shadow-xl active:scale-95 flex items-center justify-center gap-3`}>
              <Shield className="w-4 h-4" />
              {confirmState.confirmLabel || 'Confirm'}
            </button>
          </div>
        }
      />

      {/* AdminCommandCenter for User Edit */}
      <AdminCommandCenter
        open={showModal}
        onClose={() => { setShowModal(false); setEditingUser(null); }}
        title={editingUser ? `Agent: ${editingUser.name}` : 'User Profile'}
        subtitle="Identity & Access Configuration"
        sections={sections}
        activeSection={activeSection}
        onSectionChange={setActiveSection}
        isLoading={isUpdateLoading}
        onSave={handleSave}
        variant="primary"
        size="4xl"
      >
        <div className="space-y-8 min-h-[350px]">
          <AnimatePresence mode="wait">
            {activeSection === 'profile' && editingUser && (
              <motion.div key="profile" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="space-y-8">
                {/* User Identity Card */}
                <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-6 flex items-center gap-6">
                  <div className="relative">
                    <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-neon-green/20 to-blue-500/20 flex items-center justify-center border border-white/10 text-3xl font-black text-neon-green shadow-inner">
                      {editingUser.name?.charAt(0).toUpperCase()}
                    </div>
                    <div className="absolute -bottom-2 -right-2 w-8 h-8 rounded-xl bg-black border border-white/10 flex items-center justify-center">
                      <Shield className="w-4 h-4 text-neon-green" />
                    </div>
                  </div>
                  <div>
                    <h3 className="text-2xl font-mono font-black text-white tracking-tighter uppercase italic">{editingUser.name}</h3>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="w-1.5 h-1.5 rounded-full bg-neon-green animate-pulse" />
                      <p className="text-gray-500 text-xs font-mono uppercase tracking-widest">{editingUser.email}</p>
                    </div>
                    <p className="text-[10px] font-mono text-gray-700 mt-2">UID: {editingUser.id}</p>
                  </div>
                </div>

                {/* Name Field */}
                <div className="space-y-3">
                  <label className="text-[10px] font-mono text-gray-400 uppercase tracking-[0.2em] block">Display Name</label>
                  <div className="relative group">
                    <UserIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-700 group-focus-within:text-neon-green transition-colors" />
                    <input
                      type="text" value={form.name}
                      onChange={(e) => setForm({ ...form, name: e.target.value })}
                      className="w-full bg-black/40 border border-white/5 rounded-xl py-4 pl-12 pr-4 font-mono text-sm text-white outline-none focus:border-neon-green/40 focus:ring-1 focus:ring-neon-green/10 transition-all"
                    />
                  </div>
                </div>

                {/* Registration Info */}
                <div className="grid grid-cols-2 gap-6">
                  <div className="p-5 bg-white/[0.02] border border-white/5 rounded-xl">
                    <div className="text-[10px] font-mono text-gray-500 uppercase tracking-widest mb-2">Registered</div>
                    <div className="text-sm font-mono text-white font-bold">{new Date(editingUser.created_at).toLocaleDateString()}</div>
                  </div>
                  <div className="p-5 bg-white/[0.02] border border-white/5 rounded-xl">
                    <div className="text-[10px] font-mono text-gray-500 uppercase tracking-widest mb-2">Last Login</div>
                    <div className="text-sm font-mono text-white font-bold">{editingUser.last_login ? new Date(editingUser.last_login).toLocaleDateString() : 'Never'}</div>
                  </div>
                </div>
              </motion.div>
            )}

            {activeSection === 'access' && editingUser && (
              <motion.div key="access" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="space-y-8">
                {/* Role Selection */}
                <div className="space-y-3">
                  <label className="text-[10px] font-mono text-gray-400 uppercase tracking-[0.2em] block">Clearance Level</label>
                  <div className="grid grid-cols-3 gap-4">
                    {[
                      { value: 'user', label: 'Standard', icon: UserIcon, color: 'text-gray-400', bg: 'bg-gray-500/10', border: 'border-gray-500/20' },
                      { value: 'admin', label: 'Administrator', icon: ShieldCheck, color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/20' },
                      { value: 'superadmin', label: 'SuperAdmin', icon: ShieldAlert, color: 'text-purple-400', bg: 'bg-purple-500/10', border: 'border-purple-500/20' },
                    ].map(role => (
                      <button
                        key={role.value}
                        onClick={() => setForm({ ...form, role: role.value })}
                        className={`p-5 rounded-2xl border transition-all text-left group ${
                          form.role === role.value 
                            ? `${role.bg} ${role.border} shadow-lg` 
                            : 'bg-white/[0.02] border-white/5 hover:border-white/10'
                        }`}
                      >
                        <role.icon className={`w-6 h-6 mb-3 ${form.role === role.value ? role.color : 'text-gray-600'}`} />
                        <div className={`text-sm font-mono font-black uppercase ${form.role === role.value ? 'text-white' : 'text-gray-500'}`}>{role.label}</div>
                        <div className="text-[9px] font-mono text-gray-600 mt-1 uppercase tracking-wider">
                          {role.value === 'user' ? 'Basic scan access' : role.value === 'admin' ? 'Workspace management' : 'Full system control'}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Status Toggle */}
                <label className="flex items-center gap-4 p-6 bg-white/[0.02] border border-white/5 rounded-2xl cursor-pointer hover:bg-white/[0.04] transition-all group">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all ${form.is_active ? 'bg-emerald-500/10 text-emerald-400 shadow-[0_0_20px_-5px_rgba(52,211,153,0.4)]' : 'bg-red-500/10 text-red-400'}`}>
                    {form.is_active ? <CheckCircle className="w-6 h-6" /> : <Ban className="w-6 h-6" />}
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-mono font-bold text-white">{form.is_active ? 'Account Active' : 'Account Suspended'}</div>
                    <div className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">
                      {form.is_active ? 'User has full access to their workspaces' : 'All access is revoked'}
                    </div>
                  </div>
                  <div className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" className="sr-only peer" checked={form.is_active} onChange={e => setForm({ ...form, is_active: e.target.checked })} />
                    <div className="w-11 h-6 bg-white/5 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-500/50 border border-white/10"></div>
                  </div>
                </label>
              </motion.div>
            )}

            {activeSection === 'quotas' && editingUser && (
              <motion.div key="quotas" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="space-y-6">
                <div className="p-6 bg-amber-500/5 border border-amber-500/20 rounded-2xl">
                  <div className="flex items-center gap-3 mb-3">
                    <Activity className="w-5 h-5 text-amber-500" />
                    <span className="text-sm font-mono font-black text-amber-400 uppercase">Quota Overrides</span>
                  </div>
                  <p className="text-xs font-mono text-gray-400 leading-relaxed">
                    Per-user quota overrides allow you to grant additional resources beyond the plan baseline.
                    These settings take priority over the subscription tier limits.
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-6">
                  <div className="p-5 bg-white/[0.02] border border-white/5 rounded-xl space-y-3">
                    <div className="flex items-center gap-2">
                      <Globe className="w-3 h-3 text-blue-400" />
                      <span className="text-[10px] font-mono text-gray-400 uppercase tracking-widest">Extra Monthly Scans</span>
                    </div>
                    <input type="number" defaultValue={0} className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-white font-mono text-sm focus:border-blue-400/50 outline-none transition-all" />
                  </div>
                  <div className="p-5 bg-white/[0.02] border border-white/5 rounded-xl space-y-3">
                    <div className="flex items-center gap-2">
                      <Cpu className="w-3 h-3 text-purple-400" />
                      <span className="text-[10px] font-mono text-gray-400 uppercase tracking-widest">Extra AI Credits</span>
                    </div>
                    <input type="number" defaultValue={0} className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-white font-mono text-sm focus:border-purple-400/50 outline-none transition-all" />
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </AdminCommandCenter>

      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 pb-4 border-b border-white/5">
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-neon-green/10 rounded-xl border border-neon-green/20 shadow-[0_0_30px_-10px_rgba(57,255,20,0.4)]">
              <Users className="text-neon-green w-8 h-8" />
            </div>
            <div>
              <h1 className="text-4xl font-mono font-black text-white tracking-tighter uppercase italic">
                User <span className="text-neon-green">Directory</span>
              </h1>
              <div className="flex items-center gap-2 mt-1">
                <div className="w-2 h-2 rounded-full bg-neon-green animate-pulse" />
                <p className="text-gray-500 font-mono text-[10px] uppercase tracking-[0.3em]">Identity & Access Control Engine</p>
              </div>
            </div>
          </div>
        </div>

        {/* Stat Pills */}
        <div className="flex items-center gap-3">
          {[
            { label: 'Active', value: stats.active, color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20' },
            { label: 'Admins', value: stats.admins, color: 'text-purple-400', bg: 'bg-purple-500/10', border: 'border-purple-500/20' },
            { label: 'Suspended', value: stats.suspended, color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20' },
          ].map((s, i) => (
            <div key={i} className={`flex items-center gap-3 px-5 py-3 ${s.bg} border ${s.border} rounded-2xl`}>
              <span className={`text-lg font-mono font-black ${s.color}`}>{s.value}</span>
              <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">{s.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Search & Filters */}
      <div className="flex flex-col md:flex-row gap-4 items-center">
        <div className="relative w-full md:flex-1 group">
          <Search className="absolute left-5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 group-focus-within:text-neon-green transition-colors" />
          <input 
            type="text"
            placeholder="Search by name or email..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#0d0d0e] border border-white/5 rounded-2xl py-4 pl-14 pr-4 font-mono text-sm outline-none focus:border-neon-green/50 focus:ring-1 focus:ring-neon-green/20 transition-all text-white uppercase tracking-wider"
          />
        </div>
        <div className="flex items-center gap-2">
          {['all', 'user', 'admin', 'superadmin'].map(r => (
            <button
              key={r}
              onClick={() => setRoleFilter(r)}
              className={`px-5 py-3 rounded-xl text-[10px] font-mono font-black uppercase tracking-widest transition-all border ${
                roleFilter === r
                  ? 'bg-neon-green/10 border-neon-green/30 text-neon-green'
                  : 'bg-white/[0.02] border-white/5 text-gray-500 hover:text-white hover:border-white/10'
              }`}
            >
              {r === 'all' ? 'All Roles' : r}
            </button>
          ))}
        </div>
      </div>

      {/* Users Table */}
      {filteredUsers.length === 0 ? (
        <div className="text-center py-20 bg-[#0d0d0e]/40 border border-dashed border-white/10 rounded-[3rem]">
          <Users className="w-12 h-12 text-gray-700 mx-auto mb-4" />
          <p className="text-gray-500 font-mono uppercase tracking-widest text-sm">No users found.</p>
        </div>
      ) : (
        <div className="bg-[#0d0d0e]/40 backdrop-blur-md border border-white/[0.03] rounded-[2rem] overflow-hidden shadow-2xl">
          <table className="w-full text-left font-mono text-sm border-collapse">
            <thead className="bg-white/[0.02] border-b border-white/5 text-gray-500">
              <tr>
                <th className="px-8 py-6 font-semibold uppercase text-[10px] tracking-[0.2em]">User</th>
                <th className="px-6 py-6 font-semibold uppercase text-[10px] tracking-[0.2em] text-center">Status</th>
                <th className="px-6 py-6 font-semibold uppercase text-[10px] tracking-[0.2em]">Role</th>
                <th className="px-6 py-6 font-semibold uppercase text-[10px] tracking-[0.2em]">Joined</th>
                <th className="px-6 py-6 font-semibold uppercase text-[10px] tracking-[0.2em] text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.03]">
              {filteredUsers.map((user) => (
                <tr key={user.id} className="hover:bg-neon-green/[0.02] transition-colors group">
                  <td className="px-8 py-5">
                    <div className="flex items-center gap-4">
                      <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-neon-green/20 to-blue-500/20 flex items-center justify-center border border-white/5 text-neon-green font-bold text-sm shadow-inner group-hover:scale-110 transition-transform">
                        {user.name?.charAt(0).toUpperCase() || 'U'}
                      </div>
                      <div className="flex flex-col min-w-0">
                        <span className="text-white font-bold tracking-tight truncate">{user.name}</span>
                        <span className="text-xs text-gray-500 flex items-center gap-1.5 truncate">
                          <Mail className="w-3 h-3" /> {user.email}
                        </span>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-5">
                    <div className="flex justify-center">
                      {user.is_active ? (
                        <div className="flex items-center gap-2 px-3 py-1 bg-emerald-500/10 text-emerald-400 rounded-full border border-emerald-500/20 text-[10px] font-bold uppercase">
                          <CheckCircle className="w-3 h-3" /> Active
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 px-3 py-1 bg-red-500/10 text-red-400 rounded-full border border-red-500/20 text-[10px] font-bold uppercase">
                          <XCircle className="w-3 h-3" /> Suspended
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-5">
                    <div className="flex items-center gap-2">
                      {user.role === 'superadmin' ? (
                        <div className="flex items-center gap-2 text-purple-400">
                          <ShieldAlert className="w-4 h-4" />
                          <span className="uppercase text-[11px] font-bold tracking-wider">SuperAdmin</span>
                        </div>
                      ) : user.role === 'admin' ? (
                        <div className="flex items-center gap-2 text-blue-400">
                          <ShieldCheck className="w-4 h-4" />
                          <span className="uppercase text-[11px] font-bold tracking-wider">Admin</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 text-gray-400">
                          <UserIcon className="w-4 h-4" />
                          <span className="uppercase text-[11px] font-bold tracking-wider">User</span>
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-5 text-gray-500 text-xs">
                    <div className="flex flex-col">
                      <span className="text-gray-300 font-bold">{new Date(user.created_at).toLocaleDateString()}</span>
                      <span className="text-[10px] flex items-center gap-1"><Calendar className="w-3 h-3" /> JOINED</span>
                    </div>
                  </td>
                  <td className="px-6 py-5 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button 
                        onClick={() => handleToggleStatus(user)}
                        className={`p-2.5 rounded-xl border transition-all ${
                          user.is_active 
                            ? 'bg-red-500/5 border-red-500/10 text-red-500/50 hover:text-red-500 hover:border-red-500/30' 
                            : 'bg-emerald-500/5 border-emerald-500/10 text-emerald-500/50 hover:text-emerald-500 hover:border-emerald-500/30'
                        }`}
                        title={user.is_active ? 'Suspend User' : 'Reactivate User'}
                      >
                        {user.is_active ? <Ban className="w-4 h-4" /> : <RotateCcw className="w-4 h-4" />}
                      </button>
                      <button 
                        onClick={() => openEdit(user)}
                        className="p-2.5 bg-background border border-card-border rounded-xl text-gray-400 hover:text-neon-green hover:border-neon-green/50 hover:shadow-[0_0_15px_rgba(57,255,20,0.1)] transition-all"
                        title="Configure User"
                      >
                        <Zap className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
