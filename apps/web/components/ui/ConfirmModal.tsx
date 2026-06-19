'use client';

import { useEffect, useRef, useState } from 'react';
import { AlertTriangle, ShieldAlert, Info, CheckCircle, X, Terminal, Zap, Shield } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export type ConfirmVariant = 'danger' | 'warning' | 'info' | 'success' | 'primary';

interface ConfirmModalProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: ConfirmVariant;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading?: boolean;
}

const variantConfig: Record<ConfirmVariant, {
  icon: any;
  color: string;
  border: string;
  bg: string;
  glow: string;
  btnBg: string;
  btnText: string;
}> = {
  danger: {
    icon: ShieldAlert,
    color: 'text-red-500',
    border: 'border-red-500/30',
    bg: 'bg-red-500/5',
    glow: 'shadow-red-500/20',
    btnBg: 'bg-red-500 hover:bg-red-600',
    btnText: 'text-white'
  },
  warning: {
    icon: AlertTriangle,
    color: 'text-amber-500',
    border: 'border-amber-500/30',
    bg: 'bg-amber-500/5',
    glow: 'shadow-amber-500/20',
    btnBg: 'bg-amber-500 hover:bg-amber-600',
    btnText: 'text-black'
  },
  info: {
    icon: Info,
    color: 'text-blue-400',
    border: 'border-blue-400/30',
    bg: 'bg-blue-400/5',
    glow: 'shadow-blue-400/20',
    btnBg: 'bg-blue-500 hover:bg-blue-600',
    btnText: 'text-white'
  },
  success: {
    icon: CheckCircle,
    color: 'text-neon-green',
    border: 'border-neon-green/30',
    bg: 'bg-neon-green/5',
    glow: 'shadow-neon-green/20',
    btnBg: 'bg-neon-green hover:bg-emerald-400',
    btnText: 'text-black'
  },
  primary: {
    icon: Shield,
    color: 'text-white',
    border: 'border-white/10',
    bg: 'bg-white/5',
    glow: 'shadow-white/10',
    btnBg: 'bg-white hover:bg-neon-green',
    btnText: 'text-black'
  }
};

export function ConfirmModal({
  open,
  title,
  description,
  confirmLabel = 'Confirm Action',
  cancelLabel = 'Abort Mission',
  variant = 'danger',
  onConfirm,
  onCancel,
  isLoading = false,
}: ConfirmModalProps) {
  const config = variantConfig[variant];
  const Icon = config.icon;
  const [glitch, setGlitch] = useState(false);

  useEffect(() => {
    if (open) {
      const interval = setInterval(() => {
        setGlitch(true);
        setTimeout(() => setGlitch(false), 80);
      }, 4000);
      return () => clearInterval(interval);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel();
      if (e.key === 'Enter' && !isLoading) onConfirm();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onCancel, onConfirm, isLoading]);

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 md:p-8">
          {/* Neural Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/90 backdrop-blur-xl"
            onClick={onCancel}
          />

          {/* Matrix Decor */}
          <div className="absolute inset-0 pointer-events-none opacity-[0.03] overflow-hidden">
            <div className="absolute inset-0" style={{ 
              backgroundImage: 'radial-gradient(circle at 2px 2px, #39FF14 1px, transparent 0)',
              backgroundSize: '24px 24px' 
            }} />
          </div>

          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 40 }}
            animate={{ 
              opacity: 1, 
              scale: 1, 
              y: 0,
              x: glitch ? [0, -3, 3, 0] : 0
            }}
            exit={{ opacity: 0, scale: 0.9, y: 40 }}
            transition={{ type: "spring", damping: 25, stiffness: 350 }}
            className={`relative z-10 w-full max-w-md overflow-hidden rounded-[2.5rem] border ${config.border} bg-[#080809] shadow-2xl`}
          >
            {/* Top Scanning Line */}
            <motion.div 
              animate={{ top: ['0%', '100%', '0%'] }}
              transition={{ duration: 5, repeat: Infinity, ease: "linear" }}
              className={`absolute left-0 w-full h-px bg-gradient-to-r from-transparent via-${variant === 'primary' ? 'white' : config.color.replace('text-', '')} to-transparent opacity-20 z-10`}
            />

            {/* Corner Decorative Elements */}
            <div className={`absolute top-0 left-0 w-12 h-12 border-t-2 border-l-2 ${config.border} opacity-50 rounded-tl-[2rem]`} />
            <div className={`absolute bottom-0 right-0 w-12 h-12 border-b-2 border-r-2 ${config.border} opacity-50 rounded-br-[2rem]`} />

            <div className="relative p-10 space-y-8">
              {/* Icon + Title */}
              <div className="flex items-start gap-6">
                <div className={`relative flex-shrink-0 w-16 h-16 rounded-2xl ${config.bg} border ${config.border} flex items-center justify-center ${config.glow}`}>
                   <Icon className={`w-8 h-8 ${config.color} relative z-10`} />
                   <motion.div 
                      animate={{ opacity: [0.1, 0.3, 0.1] }}
                      transition={{ duration: 2, repeat: Infinity }}
                      className={`absolute inset-0 rounded-2xl ${config.bg} blur-xl`} 
                    />
                </div>
                <div className="flex-1 pt-1">
                  <h3 className={`text-2xl font-mono font-black ${config.color} uppercase tracking-tighter italic leading-none mb-3`}>
                    {glitch ? title.replace(/[a-z]/g, '#') : title}
                  </h3>
                  <div className={`h-0.5 w-12 ${config.color.replace('text', 'bg')} opacity-30`} />
                </div>
              </div>

              {/* Description Buffer */}
              <div className="bg-black/40 border border-white/[0.03] rounded-2xl p-6 relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-full pointer-events-none opacity-[0.02]" style={{ backgroundImage: 'linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06))', backgroundSize: '100% 2px, 3px 100%' }} />
                
                <div className="flex items-center gap-2 mb-3">
                  <Terminal className="w-3 h-3 text-gray-700" />
                  <span className="text-[9px] font-mono text-gray-700 uppercase tracking-widest">Protocol Instructions</span>
                </div>
                
                <p className="text-sm font-mono text-gray-400 leading-relaxed italic">
                  {description}
                </p>
              </div>

              {/* Actions */}
              <div className="flex flex-col sm:flex-row gap-4 pt-2">
                <button
                  onClick={onCancel}
                  className="flex-1 px-8 py-4 bg-white/5 border border-white/10 rounded-2xl text-xs font-mono font-black text-gray-500 uppercase tracking-widest hover:text-white hover:bg-white/10 transition-all"
                >
                  {cancelLabel}
                </button>
                <button
                  onClick={onConfirm}
                  disabled={isLoading}
                  className={`flex-[2] px-10 py-4 ${config.btnBg} ${config.btnText} rounded-2xl text-xs font-mono font-black uppercase tracking-[0.2em] transition-all shadow-xl disabled:opacity-50 flex items-center justify-center gap-3 active:scale-95`}
                >
                  {isLoading ? (
                    <Zap className="w-4 h-4 animate-spin" />
                  ) : (
                    <Terminal className="w-4 h-4" />
                  )}
                  {confirmLabel}
                </button>
              </div>
            </div>

            {/* Bottom Status Bar */}
            <div className="bg-white/[0.01] border-t border-white/[0.03] px-10 py-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className={`w-1.5 h-1.5 rounded-full ${variant === 'danger' ? 'bg-red-500' : 'bg-neon-green'} animate-pulse`} />
                <span className="text-[8px] font-mono text-gray-600 uppercase tracking-[0.3em]">Neural Link: Stable</span>
              </div>
              <div className="text-[8px] font-mono text-gray-700 uppercase">
                CRC: <span className="text-gray-500 font-bold">0x88F2A1</span>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}


