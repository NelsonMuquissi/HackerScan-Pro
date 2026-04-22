'use client';

import { AlertTriangle, ArrowUpCircle } from 'lucide-react';
import Link from 'next/link';

interface QuotaExceededBannerProps {
  type: 'scans' | 'api' | 'general';
  message?: string;
  upgradeUrl?: string;
}

export function QuotaExceededBanner({ type, message, upgradeUrl }: QuotaExceededBannerProps) {
  const defaultMessages = {
    scans: 'You have reached your monthly scan limit.',
    api: 'Your API request quota has been exceeded.',
    general: 'Your current plan limits have been reached.'
  };

  return (
    <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-center justify-between mb-6">
      <div className="flex items-center space-x-3">
        <div className="p-2 bg-red-500/20 rounded-lg text-red-400">
          <AlertTriangle className="h-5 w-5" />
        </div>
        <div>
          <p className="text-sm font-bold text-white uppercase tracking-tight">Limit Reached</p>
          <p className="text-xs text-gray-400">{message || defaultMessages[type]}</p>
        </div>
      </div>
      <Link 
        href={upgradeUrl || "/billing/plans"}
        className="flex items-center space-x-1.5 px-4 py-1.5 bg-red-500 hover:bg-red-600 text-white rounded-lg text-xs font-bold transition-all"
      >
        <ArrowUpCircle className="h-4 w-4" />
        <span>Upgrade Now</span>
      </Link>
    </div>
  );
}
