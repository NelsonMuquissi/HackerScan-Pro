'use client';

import { useEffect, useState, ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Shield, AlertTriangle, CheckCircle, Info, X, Zap, 
  Terminal, Cpu, Binary, Lock, ShieldAlert 
} from 'lucide-react';

export type HackerModalVariant = 'danger' | 'warning' | 'success' | 'info' | 'primary' | 'cyan';

interface HackerModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children?: ReactNode;
  footer?: ReactNode;
  variant?: HackerModalVariant;
  size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl';
  isLoading?: boolean;
  showIcon?: boolean;
  glitchEffect?: boolean;
}

const variantStyles: Record<HackerModalVariant, {
  color: string;
  glow: string;
  border: string;
  bg: string;
  icon: any;
  accent: string;
  scanningLine: string;
}> = {
  danger: {
    color: 'text-red-500',
    glow: 'shadow-red-500/20',
    border: 'border-red-500/30',
    bg: 'bg-red-500/5',
    icon: ShieldAlert,
    accent: 'bg-red-500',
    scanningLine: 'via-red-500'
  },
  warning: {
    color: 'text-amber-500',
    glow: 'shadow-amber-500/20',
    border: 'border-amber-500/30',
    bg: 'bg-amber-500/5',
    icon: AlertTriangle,
    accent: 'bg-amber-500',
    scanningLine: 'via-amber-500'
  },
  success: {
    color: 'text-neon-green',
    glow: 'shadow-neon-green/20',
    border: 'border-neon-green/30',
    bg: 'bg-neon-green/5',
    icon: CheckCircle,
    accent: 'bg-neon-green',
    scanningLine: 'via-neon-green'
  },
  info: {
    color: 'text-blue-400',
    glow: 'shadow-blue-400/20',
    border: 'border-blue-400/30',
    bg: 'bg-blue-400/5',
    icon: Info,
    accent: 'bg-blue-400',
    scanningLine: 'via-blue-400'
  },
  primary: {
    color: 'text-neon-green',
    glow: 'shadow-neon-green/20',
    border: 'border-neon-green/30',
    bg: 'bg-neon-green/5',
    icon: Shield,
    accent: 'bg-neon-green',
    scanningLine: 'via-neon-green'
  },
  cyan: {
    color: 'text-cyan-400',
    glow: 'shadow-cyan-400/20',
    border: 'border-cyan-400/30',
    bg: 'bg-cyan-400/5',
    icon: Cpu,
    accent: 'bg-cyan-400',
    scanningLine: 'via-cyan-400'
  }
};

const sizeClasses = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  '2xl': 'max-w-2xl',
};

export function HackerModal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  variant = 'primary',
  size = 'lg',
  isLoading = false,
  showIcon = true,
  glitchEffect = true
}: HackerModalProps) {
  const [glitch, setGlitch] = useState(false);
  const style = variantStyles[variant];
  const Icon = style.icon;

  useEffect(() => {
    if (open && glitchEffect) {
      const interval = setInterval(() => {
        setGlitch(true);
        setTimeout(() => setGlitch(false), 80);
      }, 4000);
      return () => clearInterval(interval);
    }
  }, [open, glitchEffect]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 md:p-8 overflow-y-auto">
          {/* Neural Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/90 backdrop-blur-xl"
            onClick={onClose}
          />

          {/* Animated Background Grid */}
          <div className="fixed inset-0 pointer-events-none opacity-[0.05] overflow-hidden">
            <div className="absolute inset-0" style={{ 
              backgroundImage: 'radial-gradient(circle at 2px 2px, #39FF14 1px, transparent 0)',
              backgroundSize: '24px 24px' 
            }} />
          </div>

          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 40, rotateX: 10 }}
            animate={{ 
              opacity: 1, 
              scale: 1, 
              y: 0,
              rotateX: 0,
              x: glitch ? [0, -3, 3, 0] : 0
            }}
            exit={{ opacity: 0, scale: 0.9, y: 40, rotateX: -10 }}
            transition={{ type: "spring", damping: 25, stiffness: 350 }}
            className={`relative z-10 w-full ${sizeClasses[size]} overflow-hidden rounded-[2.5rem] border ${style.border} bg-[#080809] shadow-[0_0_100px_-20px_rgba(0,0,0,1)] my-auto`}
          >
            {/* Scanning Line */}
            <motion.div 
              animate={{ top: ['0%', '100%', '0%'] }}
              transition={{ duration: 6, repeat: Infinity, ease: "linear" }}
              className={`absolute left-0 w-full h-px bg-gradient-to-r from-transparent ${style.scanningLine} to-transparent opacity-20 z-10`}
            />

            {/* Corner Markers */}
            <div className={`absolute top-0 left-0 w-16 h-16 border-t-2 border-l-2 ${style.border} opacity-40 rounded-tl-[2rem]`} />
            <div className={`absolute bottom-0 right-0 w-16 h-16 border-b-2 border-r-2 ${style.border} opacity-40 rounded-br-[2rem]`} />
            <div className="absolute top-8 right-8 flex gap-2">
               <div className={`w-1 h-1 rounded-full ${style.accent} animate-pulse`} />
               <div className={`w-1 h-1 rounded-full ${style.accent} animate-pulse delay-75`} />
               <div className={`w-1 h-1 rounded-full ${style.accent} animate-pulse delay-150`} />
            </div>

            <div className="relative p-8 md:p-10 space-y-8">
              {/* Header */}
              <div className="flex items-start gap-6">
                {showIcon && (
                  <div className={`relative flex-shrink-0 w-16 h-16 rounded-2xl ${style.bg} border ${style.border} flex items-center justify-center ${style.glow}`}>
                     <Icon className={`w-8 h-8 ${style.color} relative z-10`} />
                     <motion.div 
                        animate={{ opacity: [0.1, 0.3, 0.1] }}
                        transition={{ duration: 2, repeat: Infinity }}
                        className={`absolute inset-0 rounded-2xl ${style.bg} blur-xl`} 
                      />
                  </div>
                )}
                <div className="flex-1 pt-1">
                  <div className="flex items-center justify-between">
                    <h3 className={`text-2xl font-mono font-black ${style.color} uppercase tracking-tighter italic leading-none mb-3`}>
                      {glitch ? title.replace(/[a-z]/g, '#') : title}
                    </h3>
                    {!children && (
                      <button onClick={onClose} className="p-2 text-gray-700 hover:text-white transition-colors">
                        <X className="w-5 h-5" />
                      </button>
                    )}
                  </div>
                  <div className={`h-0.5 w-16 ${style.accent} opacity-30`} />
                </div>
              </div>

              {/* Description (Terminal Style) */}
              {description && (
                <div className="bg-black/40 border border-white/[0.03] rounded-2xl p-5 relative overflow-hidden group">
                  <div className="absolute top-0 left-0 w-full h-full pointer-events-none opacity-[0.02]" style={{ backgroundImage: 'linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06))', backgroundSize: '100% 2px, 3px 100%' }} />
                  
                  <div className="flex items-center gap-2 mb-3">
                    <Terminal className="w-3 h-3 text-gray-700" />
                    <span className="text-[8px] font-mono text-gray-700 uppercase tracking-widest">Protocol Buffer</span>
                  </div>
                  
                  <p className="text-sm font-mono text-gray-400 leading-relaxed italic">
                    {description}
                  </p>
                </div>
              )}

              {/* Main Content */}
              {children && (
                <div className="relative">
                  {children}
                </div>
              )}

              {/* Footer / Actions */}
              {footer && (
                <div className="pt-4 border-t border-white/[0.05]">
                  {footer}
                </div>
              )}
            </div>

            {/* Bottom Status Bar */}
            <div className="bg-white/[0.01] border-t border-white/[0.03] px-10 py-4 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <div className={`w-1.5 h-1.5 rounded-full ${style.accent} animate-pulse`} />
                  <span className="text-[8px] font-mono text-gray-600 uppercase tracking-[0.3em]">Neural Status: Secure</span>
                </div>
                <div className="h-3 w-px bg-white/5" />
                <div className="flex items-center gap-2">
                  <Binary className="w-2.5 h-2.5 text-gray-700" />
                  <span className="text-[8px] font-mono text-gray-700 uppercase tracking-[0.1em]">CRC: 0x88F2A1</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Lock className="w-2.5 h-2.5 text-gray-700" />
                <span className="text-[8px] font-mono text-gray-700 uppercase">Superadmin Layer</span>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
