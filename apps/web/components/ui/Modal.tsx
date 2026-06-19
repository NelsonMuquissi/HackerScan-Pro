'use client';

import { useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full';
}

export function Modal({ open, onClose, title, children, size = 'md' }: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleEsc);
    return () => document.removeEventListener('keydown', handleEsc);
  }, [open, onClose]);

  const sizeClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    '2xl': 'max-w-2xl',
    full: 'max-w-[95%] h-[90vh]',
  };

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 overflow-hidden">
          {/* Enhanced Backdrop */}
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-[#020203]/90 backdrop-blur-xl"
            onClick={onClose}
          >
            {/* Ambient Animated Glow */}
            <motion.div 
              animate={{ 
                opacity: [0.1, 0.2, 0.1],
                scale: [1, 1.2, 1],
              }}
              transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
              className="absolute inset-0 bg-gradient-to-tr from-neon-green/5 via-transparent to-blue-500/5"
            />
          </motion.div>

          {/* Modal Container */}
          <motion.div 
            ref={modalRef}
            initial={{ opacity: 0, scale: 0.9, y: 30, rotateX: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0, rotateX: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 30, rotateX: 10 }}
            transition={{ type: 'spring', damping: 20, stiffness: 300 }}
            className={`relative w-full ${sizeClasses[size]} bg-[#0a0a0b]/95 backdrop-blur-3xl border border-white/10 rounded-[2rem] shadow-[0_0_100px_-20px_rgba(0,0,0,0.9)] overflow-hidden flex flex-col`}
            style={{
              boxShadow: '0 0 0 1px rgba(255,255,255,0.05), 0 25px 50px -12px rgba(0,0,0,0.7), 0 0 40px rgba(57,255,20,0.03)'
            }}
          >
            {/* Circuit Background Pattern */}
            <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{
              backgroundImage: `url("data:image/svg+xml,%3Csvg width='100' height='100' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M10 10h80v80H10z' fill='none' stroke='%2339FF14' stroke-width='0.5'/%3E%3Ccircle cx='10' cy='10' r='1' fill='%2339FF14'/%3E%3Ccircle cx='90' cy='10' r='1' fill='%2339FF14'/%3E%3Ccircle cx='90' cy='90' r='1' fill='%2339FF14'/%3E%3Ccircle cx='10' cy='90' r='1' fill='%2339FF14'/%3E%3Cpath d='M10 50h10m60 0h10M50 10v10m0 60v10' stroke='%2339FF14' stroke-width='0.5'/%3E%3C/svg%3E")`,
              backgroundSize: '100px 100px'
            }} />

            {/* Top Scanning Gradient */}
            <div className="absolute top-0 left-0 w-full h-1.5 bg-gradient-to-r from-transparent via-neon-green/40 to-transparent overflow-hidden">
               <motion.div 
                 animate={{ x: ['-100%', '100%'] }}
                 transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                 className="w-1/3 h-full bg-white/20 blur-md"
               />
            </div>

            {/* Header */}
            <div className="flex items-center justify-between px-8 py-7 border-b border-white/5 bg-white/[0.01] relative z-10">
              <div className="space-y-1">
                <div className="flex items-center gap-3">
                  <div className="relative flex items-center justify-center">
                    <div className="w-2.5 h-2.5 rounded-full bg-neon-green shadow-[0_0_12px_#39FF14]" />
                    <motion.div 
                      animate={{ scale: [1, 2, 1], opacity: [0.5, 0, 0.5] }}
                      transition={{ duration: 2, repeat: Infinity }}
                      className="absolute inset-0 w-2.5 h-2.5 rounded-full bg-neon-green"
                    />
                  </div>
                  <h2 className="text-xl font-mono font-black text-white tracking-tighter uppercase italic">
                    {title}
                  </h2>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-[1px] w-8 bg-neon-green opacity-30" />
                  <span className="text-[8px] font-mono text-gray-500 uppercase tracking-[0.4em]">Secure Protocol v4.0</span>
                </div>
              </div>

              <button 
                onClick={onClose}
                className="p-3 rounded-2xl bg-white/[0.02] border border-white/5 hover:bg-white/10 hover:border-white/20 text-gray-400 hover:text-white transition-all group"
              >
                <X className="w-5 h-5 group-hover:rotate-90 transition-transform duration-500" />
              </button>
            </div>

            {/* Content Container */}
            <div className="px-8 py-8 overflow-y-auto custom-scrollbar flex-grow relative z-10">
              <div className="relative">
                {children}
              </div>
            </div>
            
            {/* Technical Footer Accent */}
            <div className="px-8 py-4 bg-black/40 border-t border-white/[0.03] flex items-center justify-between text-[8px] font-mono text-gray-600 uppercase tracking-widest relative z-10">
              <div className="flex items-center gap-4">
                <span>Memory Lock: Active</span>
                <span className="text-gray-800">|</span>
                <span>Thread: 0x{Math.random().toString(16).slice(2, 8).toUpperCase()}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-1 h-1 rounded-full bg-neon-green/40" />
                <span>Authorized Only</span>
              </div>
            </div>

            {/* Cyber Corner Markers */}
            <div className="absolute top-0 left-0 w-6 h-6 border-t-[1px] border-l-[1px] border-white/20 rounded-tl-3xl pointer-events-none" />
            <div className="absolute top-0 right-0 w-6 h-6 border-t-[1px] border-r-[1px] border-white/20 rounded-tr-3xl pointer-events-none" />
            <div className="absolute bottom-0 left-0 w-6 h-6 border-b-[1px] border-l-[1px] border-white/20 rounded-bl-3xl pointer-events-none" />
            <div className="absolute bottom-0 right-0 w-6 h-6 border-b-[1px] border-r-[1px] border-white/20 rounded-br-3xl pointer-events-none" />
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
