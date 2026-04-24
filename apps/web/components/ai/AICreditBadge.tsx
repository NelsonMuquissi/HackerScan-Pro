'use client';

import React from 'react';
import { Cpu, Zap, Info, CreditCard, Sparkles, Trophy } from 'lucide-react';
import { useAICredits } from '@/hooks/useAICredits';
import { cn } from '@/lib/utils';
import Link from 'next/link';

interface AICreditBadgeProps {
  workspaceId?: string;
  showText?: boolean;
  className?: string;
}

export const AICreditBadge: React.FC<AICreditBadgeProps> = ({ 
  workspaceId, 
  showText = true,
  className 
}) => {
  const { wallet, loading } = useAICredits(workspaceId);

  if (loading || !wallet) {
    return (
      <div className="h-8 w-24 bg-muted animate-pulse rounded-full" />
    );
  }

  const isLow = wallet.is_low_balance;

  return (
    <div className="relative group/badge">
      <Link 
        href="/dashboard/billing/credits"
        className={cn(
          "flex items-center gap-2 px-3 py-1.5 rounded-full transition-all border",
          isLow 
            ? "bg-red-500/10 border-red-500/50 text-red-500 hover:bg-red-500/20" 
            : "bg-primary/10 border-primary/20 text-primary hover:bg-primary/20",
          className
        )}
      >
        <div className="relative">
          <Cpu className={cn("w-4 h-4", isLow && "animate-pulse")} />
          {wallet.balance_subscription > 0 && (
            <Zap className="w-2.5 h-2.5 absolute -top-1 -right-1 text-yellow-400 fill-yellow-400" />
          )}
        </div>
        
        {showText && (
          <span className="text-xs font-bold whitespace-nowrap">
            {wallet.balance_total.toLocaleString()} <span className="opacity-70 font-medium">créditos</span>
          </span>
        )}

        {isLow && (
          <Info className="w-3.5 h-3.5 animate-pulse" />
        )}
      </Link>

      {/* Breakdown Tooltip */}
      <div className="absolute top-full right-0 mt-2 w-48 p-3 rounded-2xl bg-card border border-border shadow-2xl opacity-0 translate-y-2 pointer-events-none group-hover/badge:opacity-100 group-hover/badge:translate-y-0 transition-all z-50">
        <div className="space-y-2">
          <div className="flex justify-between items-center text-[10px] uppercase font-black text-muted-foreground tracking-widest pb-1 border-b border-border/50">
            <span>Distribuição</span>
            <Sparkles className="w-3 h-3 text-primary" />
          </div>
          
          <div className="flex justify-between items-center py-1">
            <div className="flex items-center gap-2 text-xs">
              <Zap className="w-3 h-3 text-yellow-400" />
              <span>Assinatura</span>
            </div>
            <span className="text-xs font-bold">{wallet.balance_subscription.toLocaleString()}</span>
          </div>

          <div className="flex justify-between items-center py-1">
            <div className="flex items-center gap-2 text-xs">
              <CreditCard className="w-3 h-3 text-blue-400" />
              <span>Comprados</span>
            </div>
            <span className="text-xs font-bold">{wallet.balance_purchased.toLocaleString()}</span>
          </div>

          <div className="flex justify-between items-center py-1">
            <div className="flex items-center gap-2 text-xs">
              <Trophy className="w-3 h-3 text-green-400" />
              <span>Bônus</span>
            </div>
            <span className="text-xs font-bold">{wallet.balance_bonus.toLocaleString()}</span>
          </div>

          {isLow && (
            <div className="mt-2 pt-2 border-t border-red-500/20 text-[9px] text-red-500 font-bold text-center leading-tight">
              SALDO BAIXO! RECARREGUE PARA EVITAR INTERRUPÇÕES
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
