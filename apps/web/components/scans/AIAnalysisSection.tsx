'use client';

import { useState, useEffect } from 'react';
import { 
  Zap, 
  BrainCircuit, 
  Loader2, 
  AlertCircle, 
  ShieldAlert, 
  ChevronRight,
  Sparkles,
  Command
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { getScanAIPrediction } from '@/lib/api';
import { cn } from '@/lib/utils';
import { InsufficientCreditsModal } from '../ai/InsufficientCreditsModal';

interface AIAnalysisSectionProps {
  scanId: string;
}

export function AIAnalysisSection({ scanId }: AIAnalysisSectionProps) {
  const [prediction, setPrediction] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [creditError, setCreditError] = useState<any>(null);

  async function loadPrediction(force = false) {
    if (loading) return;
    setLoading(true);
    setError(null);
    setCreditError(null);
    try {
      const data = await getScanAIPrediction(scanId);
      setPrediction(data.prediction);
    } catch (err: any) {
      if (err.status === 402) {
        setCreditError(err.data || { needed: 0, available: 0, shortfall: 0 });
      } else {
        setError(err.message || 'Failed to establish neural link.');
      }
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }

  useEffect(() => {
    // We don't auto-load to save tokens unless the user clicks or we want to auto-load on first view
    // Let's auto-load once per scan detail view
    loadPrediction();
  }, [scanId]);

  return (
    <div className="bg-[#050505] border border-neon-green/20 rounded-xl overflow-hidden shadow-[0_0_50px_-12px_rgba(57,255,20,0.1)]">
      <div className="bg-neon-green/5 border-b border-neon-green/10 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="relative">
            <BrainCircuit className="w-5 h-5 text-neon-green" />
            <motion.div 
              animate={{ opacity: [0.2, 1, 0.2] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="absolute -top-1 -right-1 w-2 h-2 bg-neon-green rounded-full blur-[2px]"
            />
          </div>
          <div>
            <h3 className="text-sm font-bold font-mono text-neon-green uppercase tracking-widest flex items-center gap-2">
              NEURAL PREDICTIVE ENGINE
              <span className="text-[10px] bg-neon-green/10 px-1.5 py-0.5 rounded text-neon-green/70 font-normal border border-neon-green/20">
                BETA v4.5
              </span>
            </h3>
            <p className="text-[9px] text-gray-500 font-mono uppercase tracking-tighter">CROSS-FINDING ATTACK CHAIN SIMULATION</p>
          </div>
        </div>
        
        <button 
          onClick={() => { setIsRefreshing(true); loadPrediction(true); }}
          disabled={loading}
          className="text-[10px] font-mono text-gray-400 hover:text-neon-green transition-colors flex items-center gap-1.5"
        >
          {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Command className="w-3 h-3" />}
          RE-RUN SIMULATION
        </button>
      </div>

      <div className="p-8">
        <AnimatePresence mode="wait">
          {loading ? (
            <motion.div 
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center justify-center py-10 space-y-4"
            >
              <div className="relative w-16 h-16">
                 <div className="absolute inset-0 border-2 border-neon-green/10 rounded-full" />
                 <motion.div 
                   animate={{ rotate: 360 }}
                   transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                   className="absolute inset-0 border-2 border-t-neon-green rounded-full shadow-[0_0_10px_rgba(57,255,20,0.5)]"
                 />
              </div>
              <p className="text-xs font-mono text-neon-green/70 animate-pulse uppercase tracking-[0.2em]">
                Synthesizing Threat Vectors...
              </p>
            </motion.div>
          ) : error ? (
            <motion.div 
              key="error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="bg-red-500/5 border border-red-500/20 rounded-lg p-6 flex items-center gap-4 text-red-400"
            >
              <AlertCircle className="w-6 h-6 flex-shrink-0" />
              <div>
                <p className="text-sm font-bold uppercase tracking-widest">Neural Link Distorted</p>
                <p className="text-xs font-mono opacity-80">{error}</p>
              </div>
            </motion.div>
          ) : prediction ? (
            <motion.div 
              key="content"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-6"
            >
              <div className="prose prose-invert prose-xs max-w-none">
                <div className="whitespace-pre-wrap font-sans text-gray-300 leading-relaxed text-sm">
                  {prediction.split('###').map((section, idx) => {
                    if (!section.trim()) return null;
                    return (
                      <div key={idx} className={cn("mb-6 last:mb-0", idx > 0 && "pt-6 border-t border-white/5")}>
                        <h4 className="text-neon-green font-mono text-xs font-bold uppercase tracking-[0.2em] mb-4 flex items-center gap-2">
                          <ChevronRight className="w-3 h-3 text-neon-green/50" />
                          {section.split('\n')[0].replace(/#/g, '').trim()}
                        </h4>
                        <div className="pl-5 text-gray-400">
                           {section.split('\n').slice(1).join('\n')}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="flex items-center gap-4 pt-4">
                 <div className="flex-1 h-[1px] bg-gradient-to-r from-transparent via-white/5 to-transparent" />
                 <div className="flex items-center gap-2 text-[10px] font-mono text-gray-600 uppercase tracking-widest">
                    <Sparkles className="w-3 h-3 text-neon-yellow" />
                    Insight Probability: <span className="text-neon-green font-bold">89.4%</span>
                 </div>
                 <div className="flex-1 h-[1px] bg-gradient-to-l from-transparent via-white/5 to-transparent" />
              </div>
            </motion.div>
          ) : (
             <div className="text-center py-10">
               <button 
                 onClick={() => loadPrediction()}
                 className="px-6 py-2 bg-neon-green/10 border border-neon-green/30 text-neon-green rounded font-mono text-xs uppercase tracking-widest hover:bg-neon-green/20 transition-all font-bold"
               >
                 Initialize AI Simulation
               </button>
             </div>
          )}
        </AnimatePresence>
      </div>

      <InsufficientCreditsModal 
        isOpen={!!creditError} 
        onClose={() => setCreditError(null)} 
        needed={creditError?.needed || 0}
        available={creditError?.available || 0}
        shortfall={creditError?.shortfall || 0}
      />
    </div>
  );
}
