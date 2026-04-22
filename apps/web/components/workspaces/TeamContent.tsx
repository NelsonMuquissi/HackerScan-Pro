'use client';

import { useState } from 'react';
import { 
  Users, 
  Mail, 
  UserPlus, 
  Shield, 
  MoreVertical,
  Search,
  CheckCircle2,
  Clock,
  X
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';

const MOCK_MEMBERS = [
  { id: '1', name: 'John Doe', email: 'john@hackerscan.pro', role: 'OWNER', joined_at: '2026-01-10' },
  { id: '2', name: 'Sarah Smith', email: 'sarah@hackerscan.pro', role: 'ADMIN', joined_at: '2026-02-15' },
  { id: '3', name: 'Mike Johnson', email: 'mike@hackerscan.pro', role: 'MEMBER', joined_at: '2026-03-01' },
];

const MOCK_INVITES = [
  { id: 'inv_1', email: 'external-auditor@gmail.com', role: 'VIEWER', expires_at: '2026-04-25', status: 'PENDING' }
];

export function TeamContent() {
  const [members, setMembers] = useState(MOCK_MEMBERS);
  const [invites, setInvites] = useState(MOCK_INVITES);
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('member');

  return (
    <div className="space-y-8 pb-10">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2 uppercase tracking-tighter text-foreground">
            <Users className="w-5 h-5 text-neon-green" />
            Team Orchestration
          </h2>
          <p className="text-xs text-gray-500 font-mono mt-1 uppercase tracking-widest">
            Manage members, roles and access permissions
          </p>
        </div>
        <button 
          onClick={() => setIsInviteModalOpen(true)}
          className="bg-neon-green text-black px-4 py-2 rounded-lg font-bold text-xs flex items-center justify-center gap-2 transition-all hover:bg-neon-green/90"
        >
          <UserPlus className="w-4 h-4" />
          INVITE OPERATOR
        </button>
      </div>

      {/* Search & Stats */}
      <div className="grid md:grid-cols-3 gap-4">
        <div className="md:col-span-2 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input 
            type="text" 
            placeholder="SEARCH MEMBERS BY NAME OR EMAIL..."
            className="w-full bg-black/50 border border-white/10 rounded-lg py-3 pl-10 pr-4 text-xs font-mono focus:border-neon-green/50 outline-none transition-all uppercase tracking-tighter"
          />
        </div>
        <div className="bg-card-bg border border-card-border rounded-lg p-3 flex items-center justify-between px-6">
          <div className="flex items-center gap-3">
             <div className="w-8 h-8 rounded-full bg-neon-green/10 flex items-center justify-center">
               <Shield className="w-4 h-4 text-neon-green" />
             </div>
             <span className="text-[10px] font-bold text-gray-400 font-mono uppercase">Quota: 8/10 Seats</span>
          </div>
          <button className="text-[9px] font-bold text-neon-green hover:underline font-mono">UPGRADE</button>
        </div>
      </div>

      {/* Active Members Table */}
      <div className="bg-card-bg border border-card-border rounded-xl overflow-hidden relative">
        <div className="px-6 py-4 border-b border-white/5 bg-black/20 flex items-center justify-between">
           <h3 className="text-[10px] font-bold font-mono tracking-[0.2em] text-gray-500 uppercase">Active Operators</h3>
           <span className="text-[10px] font-bold font-mono text-neon-green px-2 py-0.5 rounded bg-neon-green/5 border border-neon-green/20">LIVE</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <tbody className="divide-y divide-white/5">
              {members.map((member) => (
                <tr key={member.id} className="group hover:bg-white/[0.01] transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-gray-800 to-black border border-white/5 flex items-center justify-center font-bold text-gray-400">
                        {member.name.charAt(0)}
                      </div>
                      <div>
                        <div className="text-sm font-bold text-foreground">{member.name}</div>
                        <div className="text-[10px] text-gray-500 font-mono tracking-tighter uppercase">{member.email}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={cn(
                      "text-[9px] font-bold font-mono px-2 py-0.5 rounded border tracking-widest",
                      member.role === 'OWNER' ? 'text-neon-green border-neon-green/20 bg-neon-green/5' :
                      member.role === 'ADMIN' ? 'text-blue-400 border-blue-400/20 bg-blue-400/5' :
                      'text-gray-400 border-white/10 bg-white/5'
                    )}>
                      {member.role}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                     <button className="p-2 hover:bg-white/5 rounded-md transition-colors text-gray-500">
                       <MoreVertical className="w-4 h-4" />
                     </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pending Invites */}
      {invites.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-[10px] font-bold font-mono tracking-[0.2em] text-gray-500 uppercase px-1">Pending Transmissions</h3>
          <div className="grid md:grid-cols-2 gap-4">
            {invites.map((invite) => (
              <div key={invite.id} className="bg-[#0c0c0c] border border-white/5 rounded-xl p-4 flex items-center justify-between group">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-black border border-white/5 flex items-center justify-center text-gray-600">
                    <Mail className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="text-sm font-bold text-gray-300">{invite.email}</div>
                    <div className="flex items-center gap-3 mt-1">
                       <span className="text-[9px] font-bold font-mono text-gray-500 uppercase">{invite.role}</span>
                       <span className="text-[9px] font-bold font-mono text-gray-600 flex items-center gap-1 uppercase">
                         <Clock className="w-3 h-3" />
                         Expires {invite.expires_at}
                       </span>
                    </div>
                  </div>
                </div>
                <button className="p-2 opacity-0 group-hover:opacity-100 transition-opacity text-red-500/50 hover:text-red-500">
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Invite Modal Overlay */}
      <AnimatePresence>
        {isInviteModalOpen && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 overflow-hidden">
             <motion.div 
               initial={{ opacity: 0 }}
               animate={{ opacity: 1 }}
               exit={{ opacity: 0 }}
               onClick={() => setIsInviteModalOpen(false)}
               className="absolute inset-0 bg-black/80 backdrop-blur-sm"
             />
             <motion.div 
               initial={{ scale: 0.95, opacity: 0, y: 20 }}
               animate={{ scale: 1, opacity: 1, y: 0 }}
               exit={{ scale: 0.95, opacity: 0, y: 20 }}
               className="relative w-full max-w-md bg-[#111111] border border-white/10 rounded-2xl p-8 shadow-2xl"
             >
                <div className="mb-6">
                  <h3 className="text-xl font-bold uppercase tracking-tighter">Invite Operator</h3>
                  <p className="text-xs text-gray-500 font-mono mt-1 uppercase tracking-widest">Connect a new security professional</p>
                </div>
                
                <div className="space-y-6">
                  <div className="space-y-2">
                    <label className="text-[10px] font-bold font-mono text-gray-500 uppercase tracking-widest ml-1">Email Address</label>
                    <input 
                      type="email" 
                      placeholder="operator@company.com"
                      className="w-full bg-black border border-white/10 rounded-lg py-3 px-4 text-sm font-mono focus:border-neon-green/50 outline-none transition-all"
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-[10px] font-bold font-mono text-gray-500 uppercase tracking-widest ml-1">System Role</label>
                    <div className="grid grid-cols-3 gap-2">
                      {['MEMBER', 'ADMIN', 'VIEWER'].map((role) => (
                        <button 
                          key={role}
                          onClick={() => setInviteRole(role)}
                          className={cn(
                            "py-2 rounded-md text-[10px] font-bold font-mono border transition-all",
                            inviteRole === role 
                              ? "bg-neon-green/10 border-neon-green text-neon-green" 
                              : "bg-black border-white/5 text-gray-600 hover:border-white/20"
                          )}
                        >
                          {role}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="pt-4 flex gap-3">
                    <button 
                      onClick={() => setIsInviteModalOpen(false)}
                      className="flex-1 py-3 rounded-lg font-bold text-xs bg-white/5 text-gray-400 hover:bg-white/10 transition-all uppercase tracking-widest"
                    >
                      Cancel
                    </button>
                    <button className="flex-1 py-3 rounded-lg font-bold text-xs bg-neon-green text-black hover:opacity-90 transition-all uppercase tracking-widest">
                      Send Transmission
                    </button>
                  </div>
                </div>
             </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
