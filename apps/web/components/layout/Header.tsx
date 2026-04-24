'use client';

import { User, ShieldCheck, CreditCard, LogOut, Bell, Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getSubscription } from '@/lib/api';
import { useAuthStore } from '@/store/useAuthStore';
import { NotificationCenter } from './NotificationCenter';
import { AICreditBadge } from '../ai/AICreditBadge';
import Link from 'next/link';

export function Header() {
  const { user, updateUser, logout } = useAuthStore();
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const handleLogout = () => {
    // Clear state and redirect immediately for maximum responsiveness
    logout();
    window.location.href = '/login';
  };

  useEffect(() => {
    async function checkSubscription() {
      if (!user?.plan) {
        try {
          const sub = await getSubscription();
          if (sub?.plan?.name) {
            updateUser({ plan: sub.plan.name });
          }
        } catch (e) {
          console.error("Failed to fetch sub for header badge");
        }
      }
    }
    checkSubscription();
  }, [user?.plan, updateUser]);

  const planColor = {
    'Free': 'bg-gray-500/10 text-gray-400 border-gray-500/20',
    'Pro': 'bg-primary/10 text-primary border-primary/20',
    'Team': 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    'Enterprise': 'bg-purple-500/10 text-purple-400 border-purple-500/20'
  }[user?.plan || 'Free'];

  return (
    <header className="h-16 bg-card-bg border-b border-card-border flex items-center justify-between px-6">
      <div className="flex items-center gap-4">
        <span className="text-sm font-mono text-gray-400">Workspace / <span className="text-neon-green">Default</span></span>
        {user?.plan && (
          <span className={`px-2 py-0.5 rounded border text-[10px] font-bold uppercase tracking-wider ${planColor}`}>
            {user.plan}
          </span>
        )}
      </div>
      <div className="flex items-center gap-4">
        <AICreditBadge className="mr-2" />
        <Link href="/dashboard/billing/usage" className="text-gray-400 hover:text-white transition-colors flex items-center gap-2 mr-2">
          <ShieldCheck className="w-4 h-4" />
          <span className="text-xs font-medium hidden sm:block">Usage</span>
        </Link>
        <Link href="/dashboard/billing/plans" className="text-gray-400 hover:text-white transition-colors flex items-center gap-2 mr-4">
          <CreditCard className="w-4 h-4" />
          <span className="text-xs font-medium hidden sm:block">Upgrade</span>
        </Link>
        <button className="text-gray-400 hover:text-neon-green transition-colors">
          <Bell className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-2 border-l border-card-border pl-4">
          <div className="w-8 h-8 rounded-full bg-card-border flex items-center justify-center text-neon-green overflow-hidden">
            <User className="w-5 h-5" />
          </div>
          <span className="text-sm font-mono text-foreground hidden md:block">{user?.name || 'Admin'}</span>
          <button 
            onClick={handleLogout} 
            disabled={loading}
            className="ml-2 text-gray-400 hover:text-red-500 transition-colors disabled:opacity-50" 
            title="Logout"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <LogOut className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>
    </header>
  );
}
