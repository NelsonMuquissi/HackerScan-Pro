'use client';

import { useEffect, useState, ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Shield, X, Zap, Terminal, Cpu, Binary, Lock, 
  ChevronRight, Command, Fingerprint, Activity,
  Maximize2, Minimize2, Save, RotateCcw
} from 'lucide-react';

interface AdminCommandCenterProps {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
  icon?: any;
  variant?: 'primary' | 'danger' | 'warning' | 'info' | 'cyan' | 'purple';
  size?: 'md' | 'lg' | 'xl' | '2xl' | '4xl' | 'full';
  sections?: { id: string; label: string; icon: any }[];
  activeSection?: string;
  onSectionChange?: (id: string) => void;
  isLoading?: boolean;
  onSave?: () => void;
  saveLabel?: string;
}

const variantStyles = {
  primary: { color: 'text-neon-green', border: 'border-neon-green/30', bg: 'bg-neon-green/5', accent: 'bg-neon-green', shadow: 'shadow-neon-green/20' },
  danger: { color: 'text-red-500', border: 'border-red-500/30', bg: 'bg-red-500/5', accent: 'bg-red-500', shadow: 'shadow-red-500/20' },
  warning: { color: 'text-amber-500', border: 'border-amber-500/30', bg: 'bg-amber-500/5', accent: 'bg-amber-500', shadow: 'shadow-amber-500/20' },
  info: { color: 'text-blue-400', border: 'border-blue-400/30', bg: 'bg-blue-400/5', accent: 'bg-blue-400', shadow: 'shadow-blue-400/20' },
  cyan: { color: 'text-cyan-400', border: 'border-cyan-400/30', bg: 'bg-cyan-400/5', accent: 'bg-cyan-400', shadow: 'shadow-cyan-400/20' },
  purple: { color: 'text-purple-500', border: 'border-purple-500/30', bg: 'bg-purple-500/5', accent: 'bg-purple-500', shadow: 'shadow-purple-500/20' },
};

const sizeClasses = {
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  '2xl': 'max-w-2xl',
  '4xl': 'max-w-4xl',
  full: 'max-w-[95vw] h-[90vh]',
};

export function AdminCommandCenter({
  open,
  onClose,
  title,
  subtitle,
  children,
  footer,
  icon: HeaderIcon = Command,
  variant = 'primary',
  size = '2xl',
  sections,
  activeSection,
  onSectionChange,
  isLoading = false,
  onSave,
  saveLabel = 'Commit Changes'
}: AdminCommandCenterProps) {
  const [isMaximized, setIsMaximized] = useState(size === 'full');
  const [glitch, setGlitch] = useState(false);
  const styles = variantStyles[variant];

  useEffect(() => {
    if (open) {
      const interval = setInterval(() => {
        setGlitch(true);
        setTimeout(() => setGlitch(false), 80);
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[500] flex items-center justify-center p-4 md:p-8">
          {/* Neural Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/90 backdrop-blur-2xl"
            onClick={onClose}
          />

          {/* Background Grid Layer */}
          <div className="fixed inset-0 pointer-events-none opacity-[0.03]" style={{ 
            backgroundImage: 'radial-gradient(circle at 2px 2px, #39FF14 1px, transparent 0)',
            backgroundSize: '32px 32px' 
          }} />

          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20, rotateX: 5 }}
            animate={{ 
              opacity: 1, 
              scale: 1, 
              y: 0,
              rotateX: 0,
              x: glitch ? [0, -2, 2, 0] : 0
            }}
            exit={{ opacity: 0, scale: 0.95, y: 20, rotateX: -5 }}
            transition={{ type: "spring", damping: 30, stiffness: 400 }}
            className={`relative z-10 w-full ${isMaximized ? 'max-w-[98vw] h-[95vh]' : sizeClasses[size]} bg-[#050506] border ${styles.border} rounded-[2.5rem] shadow-[0_0_150px_-30px_rgba(0,0,0,1)] overflow-hidden flex flex-col transition-all duration-500`}
          >
            {/* Top Scanning Line */}
            <motion.div 
              animate={{ top: ['0%', '100%', '0%'] }}
              transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
              className={`absolute left-0 w-full h-px bg-gradient-to-r from-transparent via-${variant === 'primary' ? 'neon-green' : styles.color.replace('text-', '')} to-transparent opacity-20 z-10 pointer-events-none`}
            />

            {/* Corner Decorative Markers */}
            <div className={`absolute top-0 left-0 w-24 h-24 border-t-2 border-l-2 ${styles.border} opacity-20 rounded-tl-[2.5rem] pointer-events-none`} />
            <div className={`absolute bottom-0 right-0 w-24 h-24 border-b-2 border-r-2 ${styles.border} opacity-20 rounded-br-[2.5rem] pointer-events-none`} />

            {/* Header Terminal */}
            <div className="relative flex-shrink-0 px-8 py-6 border-b border-white/[0.03] bg-white/[0.01] flex items-center justify-between">
              <div className="flex items-center gap-6">
                <div className={`relative w-14 h-14 rounded-2xl ${styles.bg} border ${styles.border} flex items-center justify-center ${styles.shadow}`}>
                   <HeaderIcon className={`w-7 h-7 ${styles.color}`} />
                   <motion.div 
                    animate={{ opacity: [0.1, 0.4, 0.1] }}
                    transition={{ duration: 3, repeat: Infinity }}
                    className={`absolute inset-0 rounded-2xl ${styles.bg} blur-xl`} 
                  />
                </div>
                <div>
                  <h3 className={`text-2xl font-mono font-black ${styles.color} uppercase tracking-tighter italic leading-none`}>
                    {glitch ? title.replace(/[A-Z]/g, '#') : title}
                  </h3>
                  {subtitle && (
                    <div className="flex items-center gap-2 mt-2">
                       <Terminal className="w-3 h-3 text-gray-700" />
                       <span className="text-[10px] font-mono text-gray-600 uppercase tracking-[0.2em]">{subtitle}</span>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-4">
                <button 
                  onClick={() => setIsMaximized(!isMaximized)}
                  className="p-3 bg-white/5 rounded-xl text-gray-600 hover:text-white transition-all border border-white/5"
                >
                  {isMaximized ? <Minimize2 className="w-5 h-5" /> : <Maximize2 className="w-5 h-5" />}
                </button>
                <button 
                  onClick={onClose}
                  className="p-3 bg-red-500/5 rounded-xl text-red-500/50 hover:text-red-500 transition-all border border-red-500/10"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Main Command Workspace */}
            <div className="flex-1 flex overflow-hidden">
              {/* Internal Sidebar (Optional) */}
              {sections && (
                <div className="w-72 flex-shrink-0 border-r border-white/[0.03] bg-black/40 py-8 px-4 flex flex-col gap-2">
                  <div className="px-4 mb-4">
                    <span className="text-[9px] font-mono text-gray-700 uppercase tracking-[0.4em] font-black">Subsystems</span>
                  </div>
                  {sections.map((section) => (
                    <button
                      key={section.id}
                      onClick={() => onSectionChange?.(section.id)}
                      className={`w-full flex items-center gap-4 px-4 py-4 rounded-2xl transition-all group ${
                        activeSection === section.id 
                          ? `${styles.bg} border ${styles.border} shadow-lg` 
                          : 'hover:bg-white/[0.02] border border-transparent hover:border-white/5'
                      }`}
                    >
                      <div className={`p-2 rounded-lg transition-all ${
                        activeSection === section.id ? styles.color : 'text-gray-600 group-hover:text-gray-400'
                      }`}>
                        <section.icon className="w-4 h-4" />
                      </div>
                      <span className={`text-[11px] font-mono font-black uppercase tracking-widest transition-colors ${
                        activeSection === section.id ? 'text-white' : 'text-gray-500 group-hover:text-gray-300'
                      }`}>
                        {section.label}
                      </span>
                      {activeSection === section.id && (
                        <div className={`w-1 h-4 rounded-full ${styles.accent} ml-auto shadow-[0_0_8px_rgba(57,255,20,0.5)] animate-pulse`} />
                      )}
                    </button>
                  ))}
                </div>
              )}

              {/* Main Content Area */}
              <div className="flex-1 overflow-y-auto p-10 custom-scrollbar relative">
                {isLoading && (
                  <div className="absolute inset-0 z-20 bg-[#050506]/80 backdrop-blur-sm flex flex-col items-center justify-center gap-6">
                    <div className="relative">
                      <div className={`w-16 h-16 border-4 border-white/5 border-t-${variant === 'primary' ? 'neon-green' : styles.color.replace('text-', '')} rounded-full animate-spin`} />
                      <div className={`absolute inset-0 ${styles.bg} blur-2xl animate-pulse rounded-full`} />
                    </div>
                    <span className={`text-xs font-mono ${styles.color} uppercase tracking-[0.4em] animate-pulse`}>Processing System Request...</span>
                  </div>
                )}
                
                <motion.div
                  key={activeSection}
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="h-full"
                >
                  {children}
                </motion.div>
              </div>
            </div>

            {/* Global Actions Terminal Footer */}
            <div className="flex-shrink-0 px-10 py-6 border-t border-white/[0.03] bg-white/[0.01] flex items-center justify-between">
              <div className="flex items-center gap-8">
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${styles.accent} animate-pulse`} />
                  <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">Protocol: <span className="text-white font-black">{variant.toUpperCase()}</span></span>
                </div>
                <div className="h-4 w-px bg-white/5" />
                <div className="flex items-center gap-3">
                  <Binary className="w-3.5 h-3.5 text-gray-700" />
                  <span className="text-[9px] font-mono text-gray-700 uppercase tracking-[0.2em]">Hash: 0x{Math.random().toString(16).substring(2, 8).toUpperCase()}</span>
                </div>
              </div>

              {footer ? footer : (
                <div className="flex items-center gap-4">
                  <button 
                    onClick={onClose}
                    className="px-8 py-3 bg-white/5 border border-white/10 rounded-xl text-[10px] font-mono font-black text-gray-500 uppercase tracking-widest hover:text-white hover:bg-white/10 transition-all flex items-center gap-2"
                  >
                    <RotateCcw className="w-3.5 h-3.5" /> Abort Mission
                  </button>
                  {onSave && (
                    <button 
                      onClick={onSave}
                      disabled={isLoading}
                      className={`px-10 py-3 ${styles.accent} text-black rounded-xl font-mono font-black text-[10px] uppercase tracking-[0.2em] shadow-xl hover:scale-105 active:scale-95 transition-all flex items-center gap-3 disabled:opacity-50`}
                    >
                      <Save className="w-4 h-4" /> {saveLabel}
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Ultra-bottom status indicator */}
            <div className={`h-1 w-full bg-gradient-to-r from-transparent ${variant === 'primary' ? 'via-neon-green/30' : `via-${styles.color.replace('text-', '')}/30`} to-transparent`} />
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
