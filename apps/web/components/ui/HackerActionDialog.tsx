'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { Shield, AlertTriangle, CheckCircle, Info, X, Zap, Terminal } from 'lucide-react';
import { useEffect, useState } from 'react';

export type HackerDialogVariant = 'danger' | 'warning' | 'success' | 'info' | 'primary';

interface HackerActionDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm?: () => void;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: HackerDialogVariant;
  isLoading?: boolean;
  showIcon?: boolean;
}

const variantStyles: Record<HackerDialogVariant, {
  color: string;
  glow: string;
  border: string;
  bg: string;
  icon: any;
  btnBg: string;
  btnText: string;
}> = {
  danger: {
    color: 'text-red-500',
    glow: 'shadow-red-500/20',
    border: 'border-red-500/30',
    bg: 'bg-red-500/5',
    icon: AlertTriangle,
    btnBg: 'bg-red-500 hover:bg-red-600',
    btnText: 'text-white'
  },
  warning: {
    color: 'text-amber-500',
    glow: 'shadow-amber-500/20',
    border: 'border-amber-500/30',
    bg: 'bg-amber-500/5',
    icon: AlertTriangle,
    btnBg: 'bg-amber-500 hover:bg-amber-600',
    btnText: 'text-black'
  },
  success: {
    color: 'text-neon-green',
    glow: 'shadow-neon-green/20',
    border: 'border-neon-green/30',
    bg: 'bg-neon-green/5',
    icon: CheckCircle,
    btnBg: 'bg-neon-green hover:bg-emerald-400',
    btnText: 'text-black'
  },
  info: {
    color: 'text-blue-400',
    glow: 'shadow-blue-400/20',
    border: 'border-blue-400/30',
    bg: 'bg-blue-400/5',
    icon: Info,
    btnBg: 'bg-blue-500 hover:bg-blue-600',
    btnText: 'text-white'
  },
  primary: {
    color: 'text-neon-green',
    glow: 'shadow-neon-green/20',
    border: 'border-neon-green/30',
    bg: 'bg-neon-green/5',
    icon: Shield,
    btnBg: 'bg-white hover:bg-neon-green',
    btnText: 'text-black'
  }
};

export function HackerActionDialog({
  open,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel = 'Execute',
  cancelLabel = 'Abort',
  variant = 'primary',
  isLoading = false,
  showIcon = true
}: HackerActionDialogProps) {
  const [glitch, setGlitch] = useState(false);
  const style = variantStyles[variant];
  const Icon = style.icon;

  useEffect(() => {
    if (open) {
      const interval = setInterval(() => {
        setGlitch(true);
        setTimeout(() => setGlitch(false), 100);
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [open]);

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 md:p-8 overflow-hidden">
          {/* Neural Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/90 backdrop-blur-xl"
            onClick={onClose}
          />

          {/* Animated Matrix-like Background */}
          <div className="absolute inset-0 pointer-events-none opacity-10 overflow-hidden">
            <div className="absolute inset-0" style={{ 
              backgroundImage: 'radial-gradient(circle at 2px 2px, #39FF14 1px, transparent 0)',
              backgroundSize: '32px 32px' 
            }} />
          </div>

          <motion.div
            initial={{ opacity: 0, scale: 0.9, rotateX: 20 }}
            animate={{ 
              opacity: 1, 
              scale: 1, 
              rotateX: 0,
              x: glitch ? [0, -2, 2, 0] : 0 
            }}
            exit={{ opacity: 0, scale: 0.9, rotateX: -20 }}
            className={`relative w-full max-w-lg bg-[#080809] border ${style.border} rounded-[2rem] shadow-2xl overflow-hidden`}
          >
            {/* Top Scanning Line */}
            <motion.div 
              animate={{ top: ['0%', '100%', '0%'] }}
              transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
              className={`absolute left-0 w-full h-px bg-gradient-to-r from-transparent via-${variant === 'primary' ? 'neon-green' : variant === 'danger' ? 'red-500' : 'blue-400'} to-transparent opacity-20 z-10`}
            />

            {/* Corner Decorative Elements */}
            <div className={`absolute top-0 left-0 w-12 h-12 border-t-2 border-l-2 ${style.border} opacity-50 rounded-tl-[2rem]`} />
            <div className={`absolute bottom-0 right-0 w-12 h-12 border-b-2 border-r-2 ${style.border} opacity-50 rounded-br-[2rem]`} />

            {/* Content Container */}
            <div className="relative p-10 space-y-8">
              {/* Header section */}
              <div className="flex items-start gap-6">
                {showIcon && (
                  <div className={`relative flex-shrink-0 w-16 h-16 rounded-2xl ${style.bg} border ${style.border} flex items-center justify-center ${style.glow}`}>
                    <Icon className={`w-8 h-8 ${style.color}`} />
                    <motion.div 
                      animate={{ opacity: [0.1, 0.3, 0.1] }}
                      transition={{ duration: 2, repeat: Infinity }}
                      className={`absolute inset-0 rounded-2xl ${style.bg} blur-xl`} 
                    />
                  </div>
                )}
                <div className="flex-1 space-y-2">
                  <h3 className={`text-2xl font-mono font-black ${style.color} uppercase tracking-tighter italic`}>
                    {glitch ? title.replace(/[aeiou]/gi, '*') : title}
                  </h3>
                  <div className={`h-0.5 w-16 ${variant === 'primary' ? 'bg-neon-green' : style.color.replace('text', 'bg')} opacity-30`} />
                </div>
                <button 
                  onClick={onClose}
                  className="p-2 text-gray-600 hover:text-white transition-colors"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              {/* Description Terminal Box */}
              <div className="bg-black/50 border border-white/[0.03] rounded-2xl p-6 relative group overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-full pointer-events-none opacity-[0.02]" style={{ backgroundImage: 'linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06))', backgroundSize: '100% 2px, 3px 100%' }} />
                
                <div className="flex items-center gap-2 mb-3">
                  <Terminal className="w-3 h-3 text-gray-700" />
                  <span className="text-[9px] font-mono text-gray-700 uppercase tracking-widest">Protocol Description Buffer</span>
                </div>
                
                <p className="text-sm font-mono text-gray-400 leading-relaxed italic">
                  {description}
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-4 pt-4">
                <button
                  onClick={onClose}
                  className="flex-1 px-8 py-4 bg-white/5 border border-white/10 rounded-2xl text-xs font-mono font-black text-gray-500 uppercase tracking-widest hover:text-white hover:bg-white/10 transition-all active:scale-95"
                >
                  {cancelLabel}
                </button>
                {onConfirm && (
                  <button
                    onClick={onConfirm}
                    disabled={isLoading}
                    className={`flex-[2] px-10 py-4 ${style.btnBg} ${style.btnText} rounded-2xl text-xs font-mono font-black uppercase tracking-[0.2em] transition-all shadow-xl active:scale-95 disabled:opacity-50 flex items-center justify-center gap-3`}
                  >
                    {isLoading ? (
                      <Zap className="w-4 h-4 animate-spin" />
                    ) : (
                      <Terminal className="w-4 h-4" />
                    )}
                    {confirmLabel}
                  </button>
                )}
              </div>
            </div>

            {/* Bottom Status Bar */}
            <div className="bg-white/[0.01] border-t border-white/[0.03] px-10 py-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className={`w-1.5 h-1.5 rounded-full ${variant === 'danger' ? 'bg-red-500' : 'bg-neon-green'} animate-pulse`} />
                <span className="text-[8px] font-mono text-gray-600 uppercase tracking-[0.3em]">Integrity Check: Verified</span>
              </div>
              <div className="text-[8px] font-mono text-gray-700 uppercase">
                Access Level: <span className="text-gray-500 font-bold">SUPERADMIN</span>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
