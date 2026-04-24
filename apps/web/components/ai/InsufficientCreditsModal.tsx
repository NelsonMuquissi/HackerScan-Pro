'use client';

import React from 'react';
import { 
  X, 
  Cpu, 
  ShoppingCart, 
  ExternalLink,
  ShieldAlert,
  Zap
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';

interface InsufficientCreditsModalProps {
  isOpen: boolean;
  onClose: () => void;
  needed?: number;
  available?: number;
  shortfall?: number;
}

export const InsufficientCreditsModal: React.FC<InsufficientCreditsModalProps> = ({
  isOpen,
  onClose,
  needed = 0,
  available = 0,
  shortfall = 0
}) => {
  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
        <motion.div 
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="bg-card border border-border w-full max-w-md rounded-2xl overflow-hidden shadow-2xl"
        >
          {/* Header */}
          <div className="relative p-6 pb-0 flex flex-col items-center text-center">
            <button 
              onClick={onClose}
              className="absolute top-4 right-4 p-1 rounded-full hover:bg-muted transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
            
            <div className="w-16 h-16 bg-red-500/10 rounded-2xl flex items-center justify-center mb-4 border border-red-500/20">
              <ShieldAlert className="w-8 h-8 text-red-500" />
            </div>
            
            <h2 className="text-2xl font-bold tracking-tight">Créditos Insuficientes</h2>
            <p className="text-muted-foreground mt-2">
              Você não tem créditos de IA suficientes para realizar esta ação.
            </p>
          </div>

          {/* Stats */}
          <div className="p-6">
            <div className="bg-muted/50 rounded-xl p-4 grid grid-cols-3 gap-2 border border-border/50">
              <div className="text-center">
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">Saldo</span>
                <div className="flex items-center justify-center gap-1 mt-1">
                  <Cpu className="w-3 h-3 text-primary" />
                  <span className="text-base font-bold">{available}</span>
                </div>
              </div>
              <div className="text-center border-l border-border/50">
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">Custo</span>
                <div className="flex items-center justify-center gap-1 mt-1">
                  <Cpu className="w-3 h-3 text-foreground/50" />
                  <span className="text-base font-bold">{needed}</span>
                </div>
              </div>
              <div className="text-center border-l border-border/50">
                <span className="text-[10px] uppercase tracking-wider text-red-500 font-bold">Déficit</span>
                <div className="flex items-center justify-center gap-1 mt-1">
                  <Cpu className="w-3 h-3 text-red-500" />
                  <span className="text-base font-bold text-red-500">{shortfall}</span>
                </div>
              </div>
            </div>

            <div className="mt-6 space-y-3">
              <Link 
                href="/dashboard/billing/credits"
                className="w-full bg-primary text-primary-foreground py-3 rounded-xl font-bold flex items-center justify-center gap-2 hover:opacity-90 transition-all shadow-lg shadow-primary/20"
                onClick={onClose}
              >
                <ShoppingCart className="w-4 h-4" />
                Adquirir Pacote de Créditos
              </Link>
              
              <Link 
                href="/dashboard/billing/plans"
                className="w-full bg-muted text-foreground py-3 rounded-xl font-bold flex items-center justify-center gap-2 hover:bg-muted/80 transition-all"
                onClick={onClose}
              >
                <Zap className="w-4 h-4 text-yellow-400" />
                Assinar Plano Pro (+1,000/mês)
              </Link>
            </div>
          </div>

          {/* Footer info */}
          <div className="bg-muted/30 p-4 border-t border-border/50 text-center">
            <p className="text-[11px] text-muted-foreground">
              Os créditos de subscrição são renovados todo dia 1º de cada mês.
            </p>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
