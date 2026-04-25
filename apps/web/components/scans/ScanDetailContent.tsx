'use client';

import { useState, useEffect } from 'react';
import { 
  Shield, 
  AlertTriangle, 
  Info, 
  ChevronDown, 
  ChevronUp, 
  Download, 
  FileJson, 
  FileText,
  Clock,
  Target,
  Zap,
  ArrowLeft,
  Loader2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { getScan, getFindings, generateReport, getReport, explainFindingAI, remediateFindingAI } from '@/lib/api';
import Link from 'next/link';
import { AIAnalysisSection } from './AIAnalysisSection';
import { FindingEvidence } from './FindingEvidence';
import { InsufficientCreditsModal } from '../ai/InsufficientCreditsModal';

interface ScanDetailContentProps {
  scanId: string;
}

export function ScanDetailContent({ scanId }: ScanDetailContentProps) {
  const [scan, setScan] = useState<any>(null);
  const [findings, setFindings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState<string | null>(null);
  const [reportStatus, setReportStatus] = useState<string | null>(null);
  const [expandedFindings, setExpandedFindings] = useState<Record<string, boolean>>({});
  const [aiLoading, setAiLoading] = useState<Record<string, string | null>>({});
  const [creditError, setCreditError] = useState<any>(null);

  const handleAIAction = async (findingId: string, action: 'explain' | 'remediate') => {
    setAiLoading(prev => ({ ...prev, [findingId]: action }));
    setCreditError(null);
    try {
      const data = action === 'explain' 
        ? await explainFindingAI(findingId)
        : await remediateFindingAI(findingId);
      
      // Update the finding in the state
      setFindings(prev => prev.map(f => f.id === findingId ? { ...f, ...data } : f));
    } catch (err: any) {
      if (err.status === 402) {
        setCreditError(err.data || { needed: 0, available: 0, shortfall: 0 });
      } else {
        console.error(`AI ${action} failed:`, err);
      }
    } finally {
      setAiLoading(prev => ({ ...prev, [findingId]: null }));
    }
  };

  useEffect(() => {
    async function loadData() {
      try {
        const [scanData, findingsData] = await Promise.all([
          getScan(scanId),
          getFindings(scanId)
        ]);
        setScan(scanData);
        // Handle both plain arrays and paginated responses { results: [...] }
        const list = Array.isArray(findingsData) ? findingsData : (findingsData?.results ?? []);
        setFindings(list);
      } catch (err) {
        console.error('Failed to load scan details:', err);
        setFindings([]);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [scanId]);

  const toggleFinding = (id: string) => {
    setExpandedFindings(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const handleExport = async (format: string) => {
    setExporting(format);
    setReportStatus('GENERATING');
    try {
      const report = await generateReport(scanId, format);
      
      // Handle potential id key mismatch (backend returns report_id, frontend expects id)
      const reportId = report.id || report.report_id;
      
      if (!reportId) {
        throw new Error('Failed to resolve report ID from backend response');
      }

      let currentReport = report;
      let attempts = 0;
      const MAX_ATTEMPTS = 60; // 2 minutes max

      while (
        (currentReport.status === 'PENDING' || currentReport.status === 'PROCESSING') && 
        attempts < MAX_ATTEMPTS
      ) {
        await new Promise(resolve => setTimeout(resolve, 2000));
        currentReport = await getReport(reportId);
        attempts++;
      }
      
      if (currentReport.status === 'COMPLETED' && currentReport.file_url) {
        window.open(currentReport.file_url, '_blank');
        setReportStatus('COMPLETED');
      } else {
        setReportStatus('FAILED');
      }
    } catch (err) {
      console.error('Export failed:', err);
      setReportStatus('FAILED');
    } finally {
      setExporting(null);
      setTimeout(() => setReportStatus(null), 3000);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
        <div className="w-12 h-12 border-4 border-neon-green border-t-transparent rounded-full animate-spin" />
        <p className="font-mono text-neon-green">INITIALIZING NEURAL LINK...</p>
      </div>
    );
  }

  if (!scan) return <div className="text-neon-red font-mono">SCAN NOT FOUND [404]</div>;

  return (
    <div className="space-y-8 pb-20">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <Link href="/dashboard" className="text-gray-400 hover:text-neon-green flex items-center gap-2 text-sm transition-colors mb-2">
            <ArrowLeft className="w-4 h-4" />
            BACK TO CONSOLE
          </Link>
          <h1 className="text-3xl font-bold text-foreground flex items-center gap-3">
            <Shield className="w-8 h-8 text-neon-green" />
            SCAN DETAIL: {scan.id.split('-')[0]}
          </h1>
          <div className="flex flex-wrap items-center gap-4 text-sm font-mono mt-2">
            <span className="flex items-center gap-1.5 text-gray-400">
              <Target className="w-4 h-4" />
              {scan.target_host}
            </span>
            <span className="flex items-center gap-1.5 text-gray-400">
              <Clock className="w-4 h-4" />
              {new Date(scan.created_at).toLocaleString()}
            </span>
            <span className={cn(
              "px-2 py-0.5 rounded-full text-xs border",
              scan.status === 'COMPLETED' ? "border-neon-green text-neon-green bg-neon-green-dim" : "border-neon-yellow text-neon-yellow bg-[rgba(255,204,0,0.1)]"
            )}>
              {scan.status}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={() => handleExport('PDF')}
            disabled={!!exporting}
            className="flex items-center gap-2 px-4 py-2 bg-neon-green text-black font-bold rounded hover:bg-opacity-90 transition-all disabled:opacity-50"
          >
            {exporting === 'PDF' ? <Zap className="w-4 h-4 animate-pulse" /> : <FileText className="w-4 h-4" />}
            PDF REPORT
          </button>
          <button 
            onClick={() => handleExport('JSON')}
            disabled={!!exporting}
            className="flex items-center gap-2 px-4 py-2 bg-card-bg border border-card-border text-foreground font-bold rounded hover:bg-[#111] transition-all disabled:opacity-50"
          >
            {exporting === 'JSON' ? <Zap className="w-4 h-4 animate-pulse" /> : <FileJson className="w-4 h-4" />}
            JSON
          </button>
        </div>
      </div>

      {reportStatus && (
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className={cn(
            "p-3 rounded border text-sm font-mono text-center",
            reportStatus === 'GENERATING' ? "bg-blue-900/20 border-blue-500 text-blue-400" :
            reportStatus === 'COMPLETED' ? "bg-green-900/20 border-green-500 text-green-400" :
            "bg-red-900/20 border-red-500 text-red-400"
          )}
        >
          {reportStatus === 'GENERATING' && "SYSTEM RECONSTRUCTING REPORT DATA..."}
          {reportStatus === 'COMPLETED' && "REPORT RECONSTRUCTED SUCCESSFULLY."}
          {reportStatus === 'FAILED' && "REPORT RECONSTRUCTION FAILED. CHECK SYSTEM LOGS."}
        </motion.div>
      )}

      {/* Severity Counters */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {[
          { label: 'CRITICAL', count: scan.critical_count, color: 'text-neon-red', border: 'border-neon-red/30' },
          { label: 'HIGH', count: scan.high_count, color: 'text-neon-yellow', border: 'border-neon-yellow/30' },
          { label: 'MEDIUM', count: scan.medium_count, color: 'text-orange-500', border: 'border-orange-500/30' },
          { label: 'LOW', count: scan.low_count, color: 'text-blue-500', border: 'border-blue-500/30' },
          { label: 'INFO', count: scan.info_count, color: 'text-gray-500', border: 'border-gray-500/30' },
        ].map((stat) => (
          <div key={stat.label} className={cn("bg-card-bg border rounded-lg p-4 flex flex-col items-center justify-center", stat.border)}>
            <span className={cn("text-2xl font-bold font-mono", stat.color)}>{stat.count || 0}</span>
            <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mt-1">{stat.label}</span>
          </div>
        ))}
      </div>

      {/* AI Analysis Section */}
      <AIAnalysisSection scanId={scanId} />

      {/* Findings List */}
      <div className="space-y-4">
        <h2 className="text-xl font-bold font-mono text-foreground flex items-center gap-2">
          SCAN FINDINGS [{findings.length}]
        </h2>
        
        <div className="space-y-3">
          {findings.map((f, i) => (
            <motion.div 
              key={f.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="bg-card-bg border border-card-border rounded-lg overflow-hidden"
            >
              <div 
                onClick={() => toggleFinding(f.id)}
                className="px-6 py-4 flex items-center justify-between cursor-pointer hover:bg-[#111] transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className={cn(
                    "w-2 h-2 rounded-full shadow-[0_0_10px_2px_currentColor]",
                    f.severity === 'CRITICAL' ? "text-neon-red" :
                    f.severity === 'HIGH' ? "text-neon-yellow" :
                    f.severity === 'MEDIUM' ? "text-orange-500" :
                    "text-blue-500"
                  )} />
                  <div className="flex flex-col">
                    <span className="font-bold text-foreground">{f.title}</span>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[10px] font-mono text-gray-500 bg-[#111] px-1.5 py-0.5 rounded border border-card-border uppercase">
                        {f.plugin_slug}
                      </span>
                      {f.status === 'active' && (
                        f.first_seen_at === f.last_seen_at ? (
                          <span className="text-[10px] font-bold text-neon-green bg-neon-green-dim px-1.5 py-0.5 rounded border border-neon-green/30">
                            NEW
                          </span>
                        ) : (
                          <span className="text-[10px] font-bold text-blue-400 bg-blue-900/20 px-1.5 py-0.5 rounded border border-blue-500/30">
                            RECURRING
                          </span>
                        )
                      )}
                      {f.status === 'resolved' && (
                        <span className="text-[10px] font-bold text-gray-400 bg-gray-800/50 px-1.5 py-0.5 rounded border border-gray-600/30">
                          RESOLVED
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-sm font-mono">
                  <div className="hidden sm:flex flex-col items-end mr-4 text-[10px] text-gray-500">
                    <span>SEEN: {new Date(f.first_seen_at).toLocaleDateString()}</span>
                    <span>LAST: {new Date(f.last_seen_at).toLocaleDateString()}</span>
                  </div>
                  <span className={cn(
                    "font-bold",
                    f.severity === 'CRITICAL' ? "text-neon-red" :
                    f.severity === 'HIGH' ? "text-neon-yellow" :
                    "text-gray-400"
                  )}>
                    {f.severity}
                  </span>
                  {expandedFindings[f.id] ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </div>
              </div>

              <AnimatePresence>
                {expandedFindings[f.id] && (
                  <motion.div 
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="border-t border-card-border"
                  >
                    <div className="p-6 space-y-6">
                      <div className="grid md:grid-cols-2 gap-8">
                        <div className="space-y-4">
                          <h4 className="text-xs font-bold text-neon-green uppercase tracking-widest flex items-center gap-2">
                            <Info className="w-3 h-3" />
                            Description
                          </h4>
                          <p className="text-sm text-gray-300 leading-relaxed">
                            {f.description}
                          </p>
                        </div>
                        <div className="space-y-4">
                          <h4 className="text-xs font-bold text-neon-green uppercase tracking-widest flex items-center gap-2">
                            <Zap className="w-3 h-3" />
                            Remediation
                          </h4>
                          <p className="text-sm text-gray-300 leading-relaxed">
                            {f.remediation}
                          </p>
                        </div>
                      </div>

                      <FindingEvidence finding={f} />

                      
                      {/* AI Insights */}
                      <div className="space-y-4">
                        {(f.ai_explanation || f.ai_remediation) ? (
                          <div className="bg-neon-green-dim border border-neon-green/30 p-4 rounded-lg space-y-4 shadow-[0_0_15px_rgba(57,255,20,0.05)]">
                            {f.ai_explanation && (
                              <div className="space-y-2">
                                <h4 className="text-[10px] font-bold text-neon-green uppercase tracking-tighter flex items-center gap-2">
                                  <Zap className="w-3 h-3 fill-neon-green" />
                                  AI-POWERED THREAT ANALYSIS
                                </h4>
                                <p className="text-sm text-neon-green/90 leading-snug">
                                  {f.ai_explanation}
                                </p>
                              </div>
                            )}
                            
                            {f.ai_remediation && (
                              <div className="space-y-2 pt-2 border-t border-neon-green/20">
                                <h4 className="text-[10px] font-bold text-neon-green uppercase tracking-tighter flex items-center gap-2">
                                  <Shield className="w-3 h-3 fill-neon-green" />
                                  AI ADVISORY: STEP-BY-STEP REMEDIATION
                                </h4>
                                <div className="text-sm text-neon-green/80 leading-relaxed whitespace-pre-wrap font-mono text-[13px]">
                                  {f.ai_remediation}
                                </div>
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="flex flex-wrap gap-3">
                            <button 
                              onClick={() => handleAIAction(f.id, 'explain')}
                              disabled={!!aiLoading[f.id]}
                              className="flex items-center gap-2 px-3 py-1.5 bg-neon-green/10 border border-neon-green/30 text-neon-green rounded text-[10px] font-bold uppercase tracking-widest hover:bg-neon-green/20 transition-all disabled:opacity-50"
                            >
                              {aiLoading[f.id] === 'explain' ? <Loader2 className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}
                              EXPLIQUE ESTE RISCO COM IA
                            </button>
                            <button 
                              onClick={() => handleAIAction(f.id, 'remediate')}
                              disabled={!!aiLoading[f.id]}
                              className="flex items-center gap-2 px-3 py-1.5 bg-blue-500/10 border border-blue-500/30 text-blue-400 rounded text-[10px] font-bold uppercase tracking-widest hover:bg-blue-500/20 transition-all disabled:opacity-50"
                            >
                              {aiLoading[f.id] === 'remediate' ? <Loader2 className="w-3 h-3 animate-spin" /> : <Shield className="w-3 h-3" />}
                              GERAR REMEDIAÇÃO PERSONALIZADA
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </div>
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
