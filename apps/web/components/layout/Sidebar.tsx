import Link from 'next/link';
import { LayoutDashboard, ShieldAlert, Settings, Terminal, FileText, Calendar, ShoppingBag, ShieldCheck, Cpu } from 'lucide-react';
import { cn } from '@/lib/utils';

export function Sidebar() {
  return (
    <div className="w-64 h-full bg-card-bg border-r border-card-border flex flex-col">
      <div className="p-6">
        <h1 className="text-2xl font-mono text-neon-green font-bold flex items-center gap-2">
          <Terminal className="w-6 h-6" />
          HackerScan Pro
        </h1>
      </div>
      
      <nav className="flex-1 px-4 space-y-2 overflow-y-auto">
        <Link href="/dashboard" className="flex items-center gap-3 px-3 py-2 text-foreground hover:text-neon-green hover:bg-neon-green-dim rounded-md transition-colors font-mono">
          <LayoutDashboard className="w-5 h-5" />
          Dashboard
        </Link>
        <Link href="/dashboard/scans" className="flex items-center gap-3 px-3 py-2 text-foreground hover:text-neon-green hover:bg-neon-green-dim rounded-md transition-colors font-mono">
          <ShieldAlert className="w-5 h-5" />
          Scans
        </Link>
        <Link href="/dashboard/scans/schedules" className="flex items-center gap-3 px-3 py-2 text-foreground hover:text-neon-green hover:bg-neon-green-dim rounded-md transition-colors font-mono">
          <Calendar className="w-5 h-5" />
          Automated Scans
        </Link>
        <Link href="/dashboard/reports" className="flex items-center gap-3 px-3 py-2 text-foreground hover:text-neon-green hover:bg-neon-green-dim rounded-md transition-colors font-mono">
          <FileText className="w-5 h-5" />
          Reports
        </Link>
        <Link href="/dashboard/bounty" className="flex items-center gap-3 px-3 py-2 text-foreground hover:text-neon-green hover:bg-neon-green-dim rounded-md transition-colors font-mono group">
          <ShieldCheck className="w-5 h-5 text-emerald-500 group-hover:animate-pulse" />
          Hacker Hub
        </Link>
        <Link href="/dashboard/marketplace" className="flex items-center gap-3 px-3 py-2 text-foreground hover:text-neon-green hover:bg-neon-green-dim rounded-md transition-colors font-mono">
          <ShoppingBag className="w-5 h-5" />
          Marketplace
        </Link>
        <Link href="/dashboard/billing/credits" className="flex items-center gap-3 px-3 py-2 text-foreground hover:text-neon-green hover:bg-neon-green-dim rounded-md transition-colors font-mono group">
          <Cpu className="w-5 h-5 text-primary group-hover:animate-spin" />
          AI Credits
        </Link>
        <Link href="/dashboard/developers" className="flex items-center gap-3 px-3 py-2 text-foreground hover:text-neon-green hover:bg-neon-green-dim rounded-md transition-colors font-mono">
          <Terminal className="w-5 h-5" />
          API Keys
        </Link>
        <Link href="/dashboard/settings" className="flex items-center gap-3 px-3 py-2 text-foreground hover:text-neon-green hover:bg-neon-green-dim rounded-md transition-colors font-mono">
          <Settings className="w-5 h-5" />
          Settings
        </Link>
      </nav>
      
      <div className="p-4 border-t border-card-border">
        <p className="text-xs text-center text-gray-500 font-mono">v1.0.0-beta</p>
      </div>
    </div>
  );
}
