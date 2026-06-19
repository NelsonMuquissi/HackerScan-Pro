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
  Loader2,
  ThumbsUp,
  ThumbsDown,
  CheckCircle,
  Play,
  RefreshCw,
  Terminal,
  Copy,
  Check,
  ExternalLink,
  Bot
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { 
  getScan, 
  getFindings, 
  generateReport, 
  getReport, 
  explainFindingAI, 
  remediateFindingAI,
  analyzeFalsePositiveAI,
  submitFindingFeedback,
  cancelScan,
  verifyFindingAI,
  generateFindingPOCAI,
  assessScanRiskAI,
  triggerScan,
  rescanScan,
  startScan,
  verifyAllFindings
} from '@/lib/api';
import Link from 'next/link';
import { AIAnalysisSection } from './AIAnalysisSection';
import { FindingEvidence } from './FindingEvidence';
import { InsufficientCreditsModal } from '../ai/InsufficientCreditsModal';
import { FindingCopilot } from './FindingCopilot';

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
  const [verifyAllStatus, setVerifyAllStatus] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');
  const [remediationLanguages, setRemediationLanguages] = useState<Record<string, string>>({});
  const [copilotOpen, setCopilotOpen] = useState<Record<string, boolean>>({});

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Performance Optimization: Memoize framework calculations
  const complianceStats = (findings: any[]) => {
    const getWeight = (sev: string) => {
      switch (sev?.toUpperCase()) {
        case 'CRITICAL': return 10;
        case 'HIGH': return 5;
        case 'MEDIUM': return 2;
        case 'LOW': return 1;
        default: return 0;
      }
    };

    const frameworks = ['owasp', 'mitre', 'pci', 'hipaa', 'soc2'];
    const totalRisk = findings.reduce((acc, f) => acc + getWeight(f.severity), 0);
    
    const stats = frameworks.map(framework => {
      const affected = findings.filter(f => f.compliance_mapping && f.compliance_mapping[framework]);
      const frameworkRisk = affected.reduce((acc, f) => acc + getWeight(f.severity), 0);
      return {
        id: framework,
        affected,
        risk: frameworkRisk,
        impact: totalRisk > 0 ? (frameworkRisk / totalRisk) * 100 : 0
      };
    }).filter(s => s.affected.length > 0);

    // Calculate overall health score (0-100)
    // 100 is perfect, each risk point reduces it
    const maxRisk = findings.length * 10; // Theoretical max if all were critical
    const healthScore = Math.max(0, 100 - (totalRisk / Math.max(1, maxRisk) * 100));

    return { stats, totalRisk, healthScore };
  };

  const { stats, totalRisk, healthScore } = complianceStats(findings);

  const handleAIAction = async (findingId: string, action: 'explain' | 'remediate', language?: string) => {
    setAiLoading(prev => ({ ...prev, [findingId]: action }));
    setCreditError(null);
    try {
      const data = action === 'explain' 
        ? await explainFindingAI(findingId)
        : await remediateFindingAI(findingId, false, language);
      
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

  const handleAnalyzeFP = async (findingId: string) => {
    setAiLoading(prev => ({ ...prev, [findingId]: 'analyze-fp' }));
    setCreditError(null);
    try {
      const data = await analyzeFalsePositiveAI(findingId);
      setFindings(prev => prev.map(f => f.id === findingId ? { ...f, ...data } : f));
    } catch (err: any) {
      if (err.status === 402) {
        setCreditError(err.data || { needed: 0, available: 0, shortfall: 0 });
      } else {
        console.error('AI False Positive analysis failed:', err);
      }
    } finally {
      setAiLoading(prev => ({ ...prev, [findingId]: null }));
    }
  };

  const handleVerifyFinding = async (findingId: string) => {
    setAiLoading(prev => ({ ...prev, [findingId]: 'verify' }));
    setCreditError(null);
    try {
      const data = await verifyFindingAI(findingId);
      setFindings(prev => prev.map(f => f.id === findingId ? { ...f, ...data.finding } : f));
    } catch (err: any) {
      if (err.status === 402) {
        setCreditError(err.data || { needed: 0, available: 0, shortfall: 0 });
      } else {
        console.error('Finding verification failed:', err);
      }
    } finally {
      setAiLoading(prev => ({ ...prev, [findingId]: null }));
    }
  };

  const handleGeneratePOC = async (findingId: string) => {
    setAiLoading(prev => ({ ...prev, [findingId]: 'poc' }));
    setCreditError(null);
    try {
      const data = await generateFindingPOCAI(findingId);
      setFindings(prev => prev.map(f => f.id === findingId ? { ...f, ...data.finding } : f));
    } catch (err: any) {
      if (err.status === 402) {
        setCreditError(err.data || { needed: 0, available: 0, shortfall: 0 });
      } else {
        console.error('POC generation failed:', err);
      }
    } finally {
      setAiLoading(prev => ({ ...prev, [findingId]: null }));
    }
  };

  const handleCancelScan = async () => {
    if (!scan) return;
    try {
      const updated = await cancelScan(scanId);
      setScan((prev: any) => ({ ...prev, status: 'CANCELLED' }));
    } catch (err) {
      console.error('Failed to cancel scan:', err);
    }
  };

  const handleAssessRisk = async () => {
    setAiLoading(prev => ({ ...prev, global: 'assess-risk' }));
    setCreditError(null);
    try {
      const data = await assessScanRiskAI(scanId);
      setScan(data.scan);
    } catch (err: any) {
      if (err.status === 402) {
        setCreditError(err.data || { needed: 0, available: 0, shortfall: 0 });
      } else {
        console.error('Risk assessment failed:', err);
      }
    } finally {
      setAiLoading(prev => ({ ...prev, global: null }));
    }
  };

  const handleTriggerScan = async () => {
    setAiLoading(prev => ({ ...prev, global: 'trigger' }));
    setCreditError(null);
    try {
      const updated = await triggerScan(scanId);
      setScan(updated);
    } catch (err: any) {
      if (err.status === 402) {
        setCreditError(err.data || { needed: 0, available: 0, shortfall: 0 });
      } else {
        console.error('Failed to trigger scan:', err);
      }
    } finally {
      setAiLoading(prev => ({ ...prev, global: null }));
    }
  };

  const handleRescan = async () => {
    if (!scan) return;
    setAiLoading(prev => ({ ...prev, global: 'rescan' }));
    setCreditError(null);
    try {
      const result = await rescanScan(scanId);
      window.location.href = `/dashboard/scans/${result.id}`;
    } catch (err: any) {
      if (err.status === 402) {
        setCreditError(err.data || { needed: 0, available: 0, shortfall: 0 });
      } else {
        console.error('Rescan failed:', err);
      }
    } finally {
      setAiLoading(prev => ({ ...prev, global: null }));
    }
  };

  const handleFeedback = async (findingId: string, feedback: 'confirmed_valid' | 'confirmed_fp') => {
    setAiLoading(prev => ({ ...prev, [findingId]: 'feedback' }));
    try {
      const result = await submitFindingFeedback(findingId, feedback);
      
      // Refresh scan and findings to reflect status changes (like ACTIVE -> SUPPRESSED)
      const [scanData, findingsData] = await Promise.all([
        getScan(scanId),
        getFindings(scanId)
      ]);
      setScan(scanData);
      const list = Array.isArray(findingsData) ? findingsData : (findingsData?.results ?? []);
      setFindings(list);
    } catch (err) {
      console.error('Feedback submission failed:', err);
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

        <div className="flex flex-wrap items-center gap-3">
          {scan.status === 'RUNNING' && (
            <button 
              onClick={handleCancelScan}
              className="flex items-center gap-2 px-4 py-2 bg-red-900/10 border border-neon-red/30 text-neon-red font-bold rounded hover:bg-red-900/30 transition-all shadow-[0_0_10px_rgba(255,49,49,0.1)] hover:shadow-[0_0_15px_rgba(255,49,49,0.2)]"
            >
              <AlertTriangle className="w-4 h-4" />
              CANCELAR SCAN
            </button>
          )}

          <button 
            onClick={handleAssessRisk}
            disabled={!!aiLoading.global}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-900/20 to-indigo-900/20 border border-blue-500/30 text-blue-400 font-bold rounded hover:from-blue-900/30 hover:to-indigo-900/30 hover:border-blue-500/50 transition-all disabled:opacity-50 shadow-[0_0_10px_rgba(59,130,246,0.1)]"
          >
            {aiLoading.global === 'assess-risk' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
            AVALIAÇÃO DE RISCO IA
          </button>

          {scan.status === 'PENDING' && (
            <button 
              onClick={handleTriggerScan}
              disabled={!!aiLoading.global}
              className="group relative flex items-center gap-2 px-6 py-2 bg-neon-green text-black font-extrabold rounded overflow-hidden transition-all hover:scale-105 active:scale-95 disabled:opacity-50 disabled:scale-100 shadow-[0_0_20px_rgba(57,255,20,0.4)]"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-500" />
              {aiLoading.global === 'trigger' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4 fill-black" />}
              INICIAR SCAN AGORA
            </button>
          )}

          {scan.status === 'COMPLETED' && (
            <>
              <button 
                onClick={handleRescan}
                disabled={!!aiLoading.global}
                className="flex items-center gap-2 px-5 py-2 bg-[#050505] border border-neon-green/40 text-neon-green font-bold rounded hover:bg-neon-green/10 hover:border-neon-green transition-all disabled:opacity-50 shadow-[0_0_15px_rgba(57,255,20,0.1)] hover:shadow-[0_0_20px_rgba(57,255,20,0.2)]"
              >
                {aiLoading.global === 'rescan' ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                RE-SCAN HOST
              </button>

              <button 
                onClick={async () => {
                  setVerifyAllStatus('loading');
                  try {
                    const result = await verifyAllFindings(scanId);
                    setVerifyAllStatus(`Verificação de ${result.queued} findings iniciada...`);
                    // Poll for updates
                    setTimeout(async () => {
                      try {
                        const updatedFindings = await getFindings(scanId);
                        setFindings(Array.isArray(updatedFindings) ? updatedFindings : (updatedFindings as any).results);
                        setVerifyAllStatus(null);
                      } catch { setVerifyAllStatus(null); }
                    }, 15000);
                  } catch (err) {
                    console.error('Verify all failed:', err);
                    setVerifyAllStatus('error');
                    setTimeout(() => setVerifyAllStatus(null), 3000);
                  }
                }}
                disabled={verifyAllStatus === 'loading' || !!aiLoading.global}
                className="group relative flex items-center gap-2 px-5 py-2 bg-gradient-to-r from-emerald-900/30 to-cyan-900/30 border border-emerald-500/40 text-emerald-400 font-bold rounded overflow-hidden transition-all hover:from-emerald-900/50 hover:to-cyan-900/50 hover:border-emerald-400 disabled:opacity-50 shadow-[0_0_15px_rgba(16,185,129,0.1)] hover:shadow-[0_0_20px_rgba(16,185,129,0.25)]"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-emerald-400/10 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
                {verifyAllStatus === 'loading' ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                VERIFICAR TODAS AS VULNERABILIDADES
              </button>
            </>
          )}

          {scan.report_file && (
            <a 
              href={scan.report_file}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2 bg-neon-green/20 border border-neon-green/50 text-neon-green font-bold rounded hover:bg-neon-green/30 transition-all shadow-[0_0_10px_rgba(57,255,20,0.1)]"
            >
              <Download className="w-4 h-4" />
              TECHNICAL REPORT (PDF)
            </a>
          )}

        </div>
      </div>

      {/* Scan Metadata HUD */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-6">
        <div className="bg-[#0a0a0a] border border-white/5 p-3 rounded flex flex-col justify-center">
          <span className="text-[8px] text-gray-500 font-bold uppercase tracking-widest">Engine Status</span>
          <div className="flex items-center gap-2 mt-1">
            <div className={cn(
              "w-1.5 h-1.5 rounded-full",
              scan.status === 'COMPLETED' ? "bg-neon-green" : "bg-neon-yellow animate-pulse"
            )} />
            <span className="text-xs font-mono text-gray-300">{scan.status}</span>
          </div>
        </div>
        <div className="bg-[#0a0a0a] border border-white/5 p-3 rounded flex flex-col justify-center">
          <span className="text-[8px] text-gray-500 font-bold uppercase tracking-widest">Target Host</span>
          <span className="text-xs font-mono text-blue-400 mt-1 truncate">{scan.target}</span>
        </div>
        <div className="bg-[#0a0a0a] border border-white/5 p-3 rounded flex flex-col justify-center">
          <span className="text-[8px] text-gray-500 font-bold uppercase tracking-widest">Scan Duration</span>
          <span className="text-xs font-mono text-gray-300 mt-1">
            {scan.completed_at && scan.created_at 
              ? `${Math.round((new Date(scan.completed_at).getTime() - new Date(scan.created_at).getTime()) / 1000)}s`
              : 'N/A'
            }
          </span>
        </div>
        <div className="bg-[#0a0a0a] border border-white/5 p-3 rounded flex flex-col justify-center">
          <span className="text-[8px] text-gray-500 font-bold uppercase tracking-widest">Audit ID</span>
          <span className="text-xs font-mono text-gray-500 mt-1">#{scanId.slice(0, 8)}...</span>
        </div>
      </div>

      {reportStatus && (
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className={cn(
            "p-3 rounded border text-sm font-mono text-center mb-4",
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

      {/* Critical Vulnerability Alert Banner */}
      {findings.some(f => f.severity === 'CRITICAL') && (
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-neon-red/10 border border-neon-red/30 p-4 rounded-xl mb-6 flex items-center justify-between shadow-[0_0_30px_rgba(255,49,49,0.1)]"
        >
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-full bg-neon-red/20 flex items-center justify-center">
              <AlertTriangle className="w-6 h-6 text-neon-red animate-pulse" />
            </div>
            <div>
              <h3 className="text-sm font-black text-neon-red uppercase tracking-widest">Immediate Action Required</h3>
              <p className="text-[11px] text-gray-400 font-mono mt-0.5">
                {findings.filter(f => f.severity === 'CRITICAL').length} CRITICAL EXPLOITABLE PATHS DETECTED ON TARGET
              </p>
            </div>
          </div>
          <button 
            onClick={() => {
              const firstCritical = findings.find(f => f.severity === 'CRITICAL');
              if (firstCritical) {
                toggleFinding(firstCritical.id);
                document.getElementById(`finding-${firstCritical.id}`)?.scrollIntoView({ behavior: 'smooth' });
              }
            }}
            className="px-4 py-2 bg-neon-red text-black font-black text-[10px] rounded hover:bg-white transition-all shadow-[0_0_15px_rgba(255,49,49,0.4)]"
          >
            ISOLATE THREATS
          </button>
        </motion.div>
      )}

      {verifyAllStatus && verifyAllStatus !== 'loading' && (
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className={cn(
            "p-3 rounded border text-sm font-mono text-center flex items-center justify-center gap-2",
            verifyAllStatus === 'error' 
              ? "bg-red-900/20 border-red-500 text-red-400" 
              : "bg-emerald-900/20 border-emerald-500 text-emerald-400"
          )}
        >
          {verifyAllStatus === 'error' ? (
            <><AlertTriangle className="w-4 h-4" /> VERIFICAÇÃO FALHOU. VERIFIQUE OS LOGS DO SISTEMA.</>
          ) : (
            <><CheckCircle className="w-4 h-4" /> {verifyAllStatus}</>
          )}
        </motion.div>
      )}
      {/* Severity Counters */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
        {[
          { label: 'CRITICAL', count: scan.critical_count, color: 'text-neon-red', border: 'border-neon-red/30' },
          { label: 'HIGH', count: scan.high_count, color: 'text-neon-yellow', border: 'border-neon-yellow/30' },
          { label: 'MEDIUM', count: scan.medium_count, color: 'text-orange-500', border: 'border-orange-500/30' },
          { label: 'LOW', count: scan.low_count, color: 'text-blue-500', border: 'border-blue-500/30' },
          { label: 'AI RISK', count: scan.ml_risk_score ? scan.ml_risk_score.toFixed(1) : '?', color: 'text-blue-400', border: 'border-blue-500/30' },
          { label: 'INFO', count: scan.info_count, color: 'text-gray-500', border: 'border-gray-500/30' },
        ].map((stat) => (
          <div key={stat.label} className={cn("bg-card-bg border rounded-lg p-4 flex flex-col items-center justify-center", stat.border)}>
            <span className={cn("text-2xl font-bold font-mono", stat.color)}>{stat.count || 0}</span>
            <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mt-1">{stat.label}</span>
          </div>
        ))}
      </div>
      
      {/* Compliance & Posture Overview */}
      {findings.length > 0 && (
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
        >
          {/* Global Posture Card */}
          <div className="bg-[#050505] border border-blue-500/20 rounded-xl p-5 relative overflow-hidden group shadow-[0_0_20px_rgba(59,130,246,0.05)]">
            <div className="absolute top-0 right-0 p-4 opacity-[0.05] group-hover:opacity-[0.1] transition-opacity pointer-events-none">
              <Shield className="w-20 h-20 text-blue-400" />
            </div>
            <div className="flex flex-col h-full justify-between">
              <div>
                <span className="text-[10px] font-black text-blue-400/60 uppercase tracking-[0.2em]">Security Posture</span>
                <div className="flex items-baseline gap-2 mt-1">
                  <h3 className="text-4xl font-black font-mono text-white">{healthScore.toFixed(0)}</h3>
                  <span className="text-xs font-bold text-gray-500">/100</span>
                </div>
              </div>
              <div className="mt-4 space-y-2">
                <div className="flex items-center justify-between text-[10px] font-bold">
                  <span className="text-gray-500 uppercase">Resilience Index</span>
                  <span className={healthScore > 80 ? "text-neon-green" : healthScore > 50 ? "text-neon-yellow" : "text-neon-red"}>
                    {healthScore > 80 ? 'EXCELLENT' : healthScore > 50 ? 'DEGRADED' : 'CRITICAL'}
                  </span>
                </div>
                <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: `${healthScore}%` }}
                    className={cn(
                      "h-full transition-colors duration-500",
                      healthScore > 80 ? "bg-neon-green shadow-[0_0_10px_rgba(57,255,20,0.5)]" : 
                      healthScore > 50 ? "bg-neon-yellow shadow-[0_0_10px_rgba(255,255,0,0.5)]" : 
                      "bg-neon-red shadow-[0_0_10px_rgba(255,49,49,0.5)]"
                    )}
                  />
                </div>
              </div>
            </div>
          </div>

          {stats.map((framework) => {
            const frameworkNames = {
              owasp: { name: 'OWASP TOP 10', color: 'text-neon-green', border: 'border-neon-green/20', icon: Shield, bg: 'bg-neon-green/5' },
              mitre: { name: 'MITRE ATT&CK', color: 'text-blue-400', border: 'border-blue-500/20', icon: Target, bg: 'bg-blue-500/5' },
              pci: { name: 'PCI-DSS 4.0', color: 'text-purple-400', border: 'border-purple-500/20', icon: FileText, bg: 'bg-purple-500/5' },
              hipaa: { name: 'HIPAA Compliance', color: 'text-cyan-400', border: 'border-cyan-500/20', icon: Info, bg: 'bg-cyan-500/5' },
              soc2: { name: 'SOC2 Type II', color: 'text-orange-400', border: 'border-orange-500/20', icon: CheckCircle, bg: 'bg-orange-500/5' }
            };
            
            const config = frameworkNames[framework.id as keyof typeof frameworkNames] || frameworkNames.owasp;
            const Icon = config.icon;
            
            // Framework specific health grade
            const getGrade = (risk: number) => {
              if (risk === 0) return 'A+';
              if (risk < 10) return 'B';
              if (risk < 20) return 'C';
              if (risk < 50) return 'D';
              return 'F';
            };
            const grade = getGrade(framework.risk);

            return (
              <div key={framework.id} className={cn("bg-card-bg border rounded-xl p-4 relative overflow-hidden group transition-all hover:border-white/20", config.border)}>
                <div className="absolute top-0 right-0 p-4 opacity-[0.03] group-hover:opacity-[0.08] transition-opacity pointer-events-none">
                  <Icon className="w-24 h-24" />
                </div>
                
                <div className="flex items-center justify-between mb-4 relative z-10">
                  <div className="flex items-center gap-2">
                    <div className={cn("p-1.5 rounded-lg", config.bg)}>
                      <Icon className={cn("w-4 h-4", config.color)} />
                    </div>
                    <span className="text-[11px] font-black uppercase tracking-[0.15em] text-gray-500">{config.name}</span>
                  </div>
                  <div className="flex flex-col items-end">
                    <div className={cn("text-lg font-black font-mono leading-none mb-1", config.color)}>{grade}</div>
                    <span className="text-[8px] text-gray-500 font-bold uppercase tracking-widest">GRADE</span>
                  </div>
                </div>

                <div className="space-y-3 relative z-10">
                  <div className="flex items-center justify-between text-[10px] font-mono">
                    <span className="text-gray-500 uppercase">Impact</span>
                    <span className={config.color}>{framework.impact.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-white/5 h-1.5 rounded-full overflow-hidden border border-white/5">
                    <motion.div 
                      initial={{ width: 0 }}
                      animate={{ width: `${framework.impact}%` }}
                      transition={{ duration: 1, ease: "easeOut" }}
                      className={cn("h-full relative", config.color.replace('text-', 'bg-'))}
                    >
                      <div className="absolute inset-0 bg-white/20 animate-pulse" />
                    </motion.div>
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-white/5 flex items-center justify-between relative z-10">
                  <div className="flex items-center gap-2">
                    <span className={cn("text-xs font-bold font-mono", config.color)}>{framework.affected.length}</span>
                    <span className="text-[9px] text-gray-600 font-bold uppercase">Violations</span>
                  </div>
                  <span className="text-[9px] text-gray-500 font-mono italic">RISK_SCORE: {framework.risk}</span>
                </div>
              </div>
            );
          })}
        </motion.div>
      )}


      {/* AI Analysis Section */}
      <AIAnalysisSection scanId={scanId} />

      {/* Findings List */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <h2 className="text-xl font-bold font-mono text-foreground flex items-center gap-2">
            SCAN FINDINGS [{findings.length}]
          </h2>
          <div className="flex items-center gap-2">
            <div className="relative group">
              <div className="absolute inset-0 bg-neon-green/5 blur group-hover:bg-neon-green/10 transition-all" />
              <input 
                type="text" 
                placeholder="SEARCH_FINDINGS_..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="relative bg-[#050505] border border-white/10 rounded-lg px-4 py-1.5 text-xs font-mono text-gray-300 w-64 focus:border-neon-green/50 outline-none transition-all"
              />
            </div>
            <select 
              value={filterSeverity}
              onChange={(e) => setFilterSeverity(e.target.value)}
              className="bg-[#050505] border border-white/10 rounded-lg px-3 py-1.5 text-xs font-mono text-gray-400 focus:border-neon-green/50 outline-none"
            >
              <option value="ALL">ALL_SEVERITIES</option>
              <option value="CRITICAL">CRITICAL</option>
              <option value="HIGH">HIGH</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="LOW">LOW</option>
            </select>
          </div>
        </div>
        
        <div className="flex items-center gap-4 text-[10px] font-mono text-gray-500 border-b border-white/5 pb-2">
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-neon-green" />
            <span>{findings.filter(f => f.status === 'resolved').length} RESOLVED</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
            <span>{findings.filter(f => f.status === 'active').length} ACTIVE</span>
          </div>
        </div>

        <div className="space-y-3">
          {findings
            .filter(f => 
              (filterSeverity === 'ALL' || f.severity === filterSeverity) &&
              ((f.title ?? '').toLowerCase().includes(searchQuery.toLowerCase()) || 
               (f.description ?? '').toLowerCase().includes(searchQuery.toLowerCase()))
            )
            .map((f, i) => (
            <motion.div 
              key={f.id}
              id={`finding-${f.id}`}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className={cn(
                "bg-card-bg border rounded-lg overflow-hidden transition-all duration-500",
                expandedFindings[f.id] ? "border-white/20 shadow-[0_0_40px_rgba(0,0,0,0.5)]" : "border-card-border"
              )}
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
                      {f.is_false_positive && (
                        <span className="text-[10px] font-bold text-neon-red bg-red-900/20 px-1.5 py-0.5 rounded border border-neon-red/30 flex items-center gap-1">
                          <AlertTriangle className="w-2.5 h-2.5" />
                          FALSE POSITIVE (AI)
                        </span>
                      )}
                      {f.user_verification === 'confirmed_valid' && (
                        <span className="text-[10px] font-bold text-neon-green bg-neon-green/10 px-1.5 py-0.5 rounded border border-neon-green/30 flex items-center gap-1">
                          <CheckCircle className="w-2.5 h-2.5" />
                          VERIFIED VALID
                        </span>
                      )}
                      {f.user_verification === 'confirmed_fp' && (
                        <span className="text-[10px] font-bold text-neon-red bg-neon-red/10 px-1.5 py-0.5 rounded border border-neon-red/30 flex items-center gap-1">
                          <ThumbsDown className="w-2.5 h-2.5" />
                          VERIFIED FP
                        </span>
                      )}
                      {f.is_verified && (
                        <span className="text-[10px] font-bold text-emerald-400 bg-emerald-950/30 px-1.5 py-0.5 rounded border border-emerald-500/30 flex items-center gap-1 shadow-[0_0_8px_rgba(52,211,153,0.1)]">
                          <Shield className="w-2.5 h-2.5 fill-emerald-400" />
                          REAL-WORLD PROOF
                        </span>
                      )}
                      {f.compliance_mapping && (
                        <div className="flex items-center gap-1">
                          {f.compliance_mapping.owasp && (
                            <span className="text-[8px] font-bold text-neon-green/70 border border-neon-green/20 px-1 py-0 rounded bg-neon-green/5 tracking-tighter">OWASP</span>
                          )}
                          {f.compliance_mapping.mitre && (
                            <span className="text-[8px] font-bold text-blue-400/70 border border-blue-500/20 px-1 py-0 rounded bg-blue-500/5 tracking-tighter">MITRE</span>
                          )}
                          {f.compliance_mapping.pci && (
                            <span className="text-[8px] font-bold text-purple-400/70 border border-purple-500/20 px-1 py-0 rounded bg-purple-500/5 tracking-tighter">PCI</span>
                          )}
                          {f.compliance_mapping.hipaa && (
                            <span className="text-[8px] font-bold text-cyan-400/70 border border-cyan-500/20 px-1 py-0 rounded bg-cyan-500/5 tracking-tighter">HIPAA</span>
                          )}
                          {f.compliance_mapping.soc2 && (
                            <span className="text-[8px] font-bold text-orange-400/70 border border-orange-500/20 px-1 py-0 rounded bg-orange-500/5 tracking-tighter">SOC2</span>
                          )}
                        </div>
                      )}
                      {f.status === 'active' && !f.is_false_positive && (
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
                      <div className="flex items-center gap-1 ml-2 border-l border-white/10 pl-2">
                        <span className="text-[9px] font-mono text-gray-600">VECTOR:</span>
                        <div className="flex gap-0.5">
                          {[1, 2, 3].map(v => (
                            <div key={v} className={cn(
                              "w-1.5 h-3 rounded-sm",
                              v <= (f.severity === 'CRITICAL' ? 3 : f.severity === 'HIGH' ? 2 : 1) 
                                ? (f.severity === 'CRITICAL' ? "bg-neon-red" : f.severity === 'HIGH' ? "bg-neon-yellow" : "bg-blue-500")
                                : "bg-white/5"
                            )} />
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-sm font-mono">
                  <div className="hidden sm:flex flex-col items-end mr-4 text-[10px] text-gray-500">
                    <span className={cn(
                      "font-black tracking-widest px-2 py-0.5 rounded-full mb-1",
                      f.severity === 'CRITICAL' ? "bg-red-950 text-neon-red border border-neon-red/30" :
                      f.severity === 'HIGH' ? "bg-orange-950 text-neon-yellow border border-neon-yellow/30" :
                      "bg-gray-900 text-gray-500 border border-white/5"
                    )}>
                      {f.severity === 'CRITICAL' || f.severity === 'HIGH' ? 'PRIORITY_1' : 'STABILIZE'}
                    </span>
                    <span>SEEN: {new Date(f.first_seen_at).toLocaleDateString()}</span>
                  </div>
                  <div className="flex flex-col items-end mr-4">
                    <span className={cn(
                      "font-bold",
                      f.severity === 'CRITICAL' ? "text-neon-red" :
                      f.severity === 'HIGH' ? "text-neon-yellow" :
                      "text-gray-400"
                    )}>
                      {f.severity}
                    </span>
                    {f.cvss_score && (
                      <span className="text-[10px] font-mono text-gray-500">
                        CVSS: {f.cvss_score}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button 
                      onClick={(e) => {
                        e.stopPropagation();
                        const md = `### Finding: ${f.title}\nSeverity: ${f.severity}\nDescription: ${f.description}\nRemediation: ${f.remediation}`;
                        copyToClipboard(md, `${f.id}-md`);
                      }}
                      className="p-1.5 text-gray-500 hover:text-white transition-colors"
                      title="Copy as Markdown"
                    >
                      {copiedId === `${f.id}-md` ? <Check className="w-4 h-4 text-neon-green" /> : <Copy className="w-4 h-4" />}
                    </button>
                    {expandedFindings[f.id] ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </div>
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

                      {f.poc && (
                        <div className="space-y-4 pt-4 border-t border-card-border">
                          <div className="flex items-center justify-between">
                            <h4 className="text-xs font-bold text-neon-yellow uppercase tracking-widest flex items-center gap-2">
                              <Terminal className="w-3 h-3" />
                              Actionable Proof of Concept (POC)
                            </h4>
                            <div className="flex items-center gap-3">
                              <button 
                                onClick={(e) => {
                                  e.stopPropagation();
                                  copyToClipboard(f.poc, f.id);
                                }}
                                className="flex items-center gap-1.5 text-[10px] font-mono text-gray-500 hover:text-neon-yellow transition-colors"
                              >
                                {copiedId === f.id ? (
                                  <><Check className="w-3 h-3 text-neon-green" /> COPIED</>
                                ) : (
                                  <><Copy className="w-3 h-3" /> COPY POC</>
                                )}
                              </button>
                              <span className="text-[9px] font-mono text-neon-yellow/50 bg-neon-yellow/5 px-2 py-0.5 rounded border border-neon-yellow/10">
                                AI-GENERATED_VERIFICATION_SCRIPT
                              </span>
                            </div>
                          </div>
                          <div className="relative group">
                            <div className="absolute -inset-0.5 bg-gradient-to-r from-neon-yellow/20 to-orange-500/20 rounded blur opacity-20 group-hover:opacity-40 transition duration-500"></div>
                            <pre className="relative bg-[#050505] p-5 rounded border border-neon-yellow/30 font-mono text-[11px] text-neon-yellow/90 whitespace-pre-wrap leading-relaxed shadow-xl overflow-x-auto">
                              {f.poc}
                            </pre>
                          </div>
                        </div>
                      )}

                      {/* Compliance Mapping Section */}
                      {f.compliance_mapping && Object.keys(f.compliance_mapping).length > 0 && (
                        <div className="space-y-4 pt-4 border-t border-card-border">
                          <h4 className="text-xs font-bold text-blue-400 uppercase tracking-widest flex items-center gap-2">
                            <Target className="w-3 h-3" />
                            Regulatory & Framework Compliance
                          </h4>
                          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            {f.compliance_mapping.owasp && (
                              <div className="bg-[#0a0a0a] border border-neon-green/20 p-4 rounded-xl flex flex-col gap-2 relative overflow-hidden group hover:border-neon-green/40 transition-colors">
                                <div className="absolute top-0 right-0 p-2 opacity-5 group-hover:opacity-10 transition-opacity">
                                  <Shield className="w-12 h-12 text-neon-green" />
                                </div>
                                <div className="text-[9px] text-gray-500 uppercase font-black tracking-[0.2em] flex items-center gap-1.5">
                                  <div className="w-1 h-1 rounded-full bg-neon-green shadow-[0_0_5px_rgba(57,255,20,1)]" />
                                  OWASP TOP 10
                                </div>
                                <div className="text-xs font-mono text-neon-green font-bold leading-tight group-hover:text-white transition-colors">
                                  {f.compliance_mapping.owasp}
                                </div>
                                <div className="mt-1 flex items-center gap-1 text-[8px] text-gray-600 font-bold uppercase tracking-widest">
                                  <ExternalLink className="w-2 h-2" />
                                  Framework Reference
                                </div>
                              </div>
                            )}
                            {f.compliance_mapping.mitre && (
                              <div className="bg-[#0a0a0a] border border-blue-500/20 p-4 rounded-xl flex flex-col gap-2 relative overflow-hidden group hover:border-blue-500/40 transition-colors">
                                <div className="absolute top-0 right-0 p-2 opacity-5 group-hover:opacity-10 transition-opacity">
                                  <Target className="w-12 h-12 text-blue-500" />
                                </div>
                                <div className="text-[9px] text-gray-500 uppercase font-black tracking-[0.2em] flex items-center gap-1.5">
                                  <div className="w-1 h-1 rounded-full bg-blue-500 shadow-[0_0_5px_rgba(59,130,246,1)]" />
                                  MITRE ATT&CK
                                </div>
                                <div className="text-xs font-mono text-blue-400 font-bold leading-tight group-hover:text-white transition-colors">
                                  {f.compliance_mapping.mitre}
                                </div>
                                <div className="mt-1 flex items-center gap-1 text-[8px] text-gray-600 font-bold uppercase tracking-widest">
                                  <ExternalLink className="w-2 h-2" />
                                  Tactics & Techniques
                                </div>
                              </div>
                            )}
                            {f.compliance_mapping.pci && (
                              <div className="bg-[#0a0a0a] border-purple-500/20 p-4 rounded-xl border flex flex-col gap-2 relative overflow-hidden group hover:border-purple-500/40 transition-colors">
                                <div className="absolute top-0 right-0 p-2 opacity-5 group-hover:opacity-10 transition-opacity">
                                  <FileText className="w-12 h-12 text-purple-500" />
                                </div>
                                <div className="text-[9px] text-gray-500 uppercase font-black tracking-[0.2em] flex items-center gap-1.5">
                                  <div className="w-1 h-1 rounded-full bg-purple-500 shadow-[0_0_5px_rgba(168,85,247,1)]" />
                                  PCI-DSS 4.0
                                </div>
                                <div className="text-xs font-mono text-purple-400 font-bold leading-tight group-hover:text-white transition-colors">
                                  {f.compliance_mapping.pci}
                                </div>
                                <div className="mt-1 flex items-center gap-1 text-[8px] text-gray-600 font-bold uppercase tracking-widest">
                                  <ExternalLink className="w-2 h-2" />
                                  Security Standards
                                </div>
                              </div>
                            )}
                            {f.compliance_mapping.hipaa && (
                              <div className="bg-[#0a0a0a] border-cyan-500/20 p-4 rounded-xl border flex flex-col gap-2 relative overflow-hidden group hover:border-cyan-500/40 transition-colors">
                                <div className="absolute top-0 right-0 p-2 opacity-5 group-hover:opacity-10 transition-opacity">
                                  <Info className="w-12 h-12 text-cyan-500" />
                                </div>
                                <div className="text-[9px] text-gray-500 uppercase font-black tracking-[0.2em] flex items-center gap-1.5">
                                  <div className="w-1 h-1 rounded-full bg-cyan-500 shadow-[0_0_5px_rgba(34,211,238,1)]" />
                                  HIPAA
                                </div>
                                <div className="text-xs font-mono text-cyan-400 font-bold leading-tight group-hover:text-white transition-colors">
                                  {f.compliance_mapping.hipaa}
                                </div>
                                <div className="mt-1 flex items-center gap-1 text-[8px] text-gray-600 font-bold uppercase tracking-widest">
                                  <ExternalLink className="w-2 h-2" />
                                  Privacy Safeguards
                                </div>
                              </div>
                            )}
                            {f.compliance_mapping.soc2 && (
                              <div className="bg-[#0a0a0a] border-orange-500/20 p-4 rounded-xl border flex flex-col gap-2 relative overflow-hidden group hover:border-orange-500/40 transition-colors">
                                <div className="absolute top-0 right-0 p-2 opacity-5 group-hover:opacity-10 transition-opacity">
                                  <CheckCircle className="w-12 h-12 text-orange-500" />
                                </div>
                                <div className="text-[9px] text-gray-500 uppercase font-black tracking-[0.2em] flex items-center gap-1.5">
                                  <div className="w-1 h-1 rounded-full bg-orange-500 shadow-[0_0_5px_rgba(251,146,60,1)]" />
                                  SOC2 TYPE II
                                </div>
                                <div className="text-xs font-mono text-orange-400 font-bold leading-tight group-hover:text-white transition-colors">
                                  {f.compliance_mapping.soc2}
                                </div>
                                <div className="mt-1 flex items-center gap-1 text-[8px] text-gray-600 font-bold uppercase tracking-widest">
                                  <ExternalLink className="w-2 h-2" />
                                  Trust Services Criteria
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Technical Evidence Portfolio */}
                      {(f.request || f.response || f.technical_details) && (
                        <div className="space-y-4 pt-6 border-t border-card-border">
                          <div className="flex items-center justify-between">
                            <h4 className="text-[10px] font-bold text-gray-400 uppercase tracking-[0.2em] flex items-center gap-2">
                              <Terminal className="w-3 h-3" />
                              Technical Evidence Portfolio
                            </h4>
                            <div className="flex items-center gap-2">
                              <div className="h-1 w-1 rounded-full bg-neon-green animate-pulse" />
                              <span className="text-[9px] font-mono text-gray-500">READY_FOR_AUDIT</span>
                            </div>
                          </div>

                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                            {f.request && (
                              <div className="space-y-2 group/evidence">
                                <div className="flex items-center justify-between px-2 py-1 bg-black/40 border-x border-t border-card-border rounded-t-lg">
                                  <div className="flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full bg-neon-yellow/50" />
                                    <span className="text-[9px] text-gray-400 font-bold uppercase tracking-widest">HTTP Request</span>
                                  </div>
                                  <button 
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      copyToClipboard(f.request, `${f.id}-req`);
                                    }}
                                    className="text-[9px] text-gray-500 hover:text-neon-green transition-all flex items-center gap-1.5 px-2 py-0.5 rounded hover:bg-white/5"
                                  >
                                    {copiedId === `${f.id}-req` ? (
                                      <><Check className="w-3 h-3 text-neon-green" /> COPIED</>
                                    ) : (
                                      <><Copy className="w-3 h-3" /> COPY</>
                                    )}
                                  </button>
                                </div>
                                <div className="relative overflow-hidden rounded-b-lg border border-card-border bg-[#050505]">
                                  <div className="absolute top-0 left-0 w-1 h-full bg-neon-yellow/20" />
                                  <pre className="p-4 text-[10px] font-mono text-gray-400 h-64 overflow-y-auto custom-scrollbar whitespace-pre-wrap selection:bg-neon-yellow/30 selection:text-white">
                                    {f.request}
                                  </pre>
                                </div>
                              </div>
                            )}

                            {f.response && (
                              <div className="space-y-2 group/evidence">
                                <div className="flex items-center justify-between px-2 py-1 bg-black/40 border-x border-t border-card-border rounded-t-lg">
                                  <div className="flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full bg-neon-green/50" />
                                    <span className="text-[9px] text-gray-400 font-bold uppercase tracking-widest">HTTP Response</span>
                                  </div>
                                  <button 
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      copyToClipboard(f.response, `${f.id}-res`);
                                    }}
                                    className="text-[9px] text-gray-500 hover:text-neon-green transition-all flex items-center gap-1.5 px-2 py-0.5 rounded hover:bg-white/5"
                                  >
                                    {copiedId === `${f.id}-res` ? (
                                      <><Check className="w-3 h-3 text-neon-green" /> COPIED</>
                                    ) : (
                                      <><Copy className="w-3 h-3" /> COPY</>
                                    )}
                                  </button>
                                </div>
                                <div className="relative overflow-hidden rounded-b-lg border border-card-border bg-[#050505]">
                                  <div className="absolute top-0 left-0 w-1 h-full bg-neon-green/20" />
                                  <pre className="p-4 text-[10px] font-mono text-gray-400 h-64 overflow-y-auto custom-scrollbar whitespace-pre-wrap selection:bg-neon-green/30 selection:text-white">
                                    {f.response}
                                  </pre>
                                </div>
                              </div>
                            )}
                          </div>

                          {f.technical_details && (
                            <div className="relative group/details">
                              <div className="absolute -inset-0.5 bg-gradient-to-r from-neon-green/10 to-transparent rounded-lg blur opacity-20" />
                              <div className="relative bg-[#080808] border border-white/5 p-5 rounded-lg space-y-3">
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-2">
                                    <Info className="w-3 h-3 text-neon-green" />
                                    <span className="text-[10px] text-gray-500 font-bold uppercase tracking-[0.2em]">Deep Analysis Context</span>
                                  </div>
                                  <span className="text-[8px] font-mono text-neon-green/40">CORE_ENGINE_LOGS</span>
                                </div>
                                <div className="text-xs text-gray-300 font-mono whitespace-pre-wrap leading-relaxed pl-4 border-l border-neon-green/20">
                                  {f.technical_details}
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      )}


                      <FindingEvidence finding={f} />

                      
                      {/* AI Insights & Feedback */}
                      <div className="space-y-4">
                        {(f.ai_explanation || f.ai_remediation || f.ai_reasoning) ? (
                          <div className={cn(
                            "relative border p-5 rounded-xl space-y-5 overflow-hidden",
                            f.is_false_positive 
                              ? "bg-red-950/10 border-neon-red/20" 
                              : "bg-[#050505] border-neon-green/20 shadow-[0_0_20px_rgba(57,255,20,0.02)]"
                          )}>
                            {/* Decorative background pulse */}
                            {!f.is_false_positive && (
                              <div className="absolute top-0 right-0 w-32 h-32 bg-neon-green/5 blur-3xl rounded-full -mr-16 -mt-16 pointer-events-none" />
                            )}
                            
                            {f.ai_reasoning && (
                              <div className="space-y-3 relative z-10">
                                <div className="flex items-center justify-between">
                                  <h4 className={cn(
                                    "text-[10px] font-black uppercase tracking-[0.2em] flex items-center gap-2",
                                    f.is_false_positive ? "text-neon-red" : "text-neon-green"
                                  )}>
                                    <div className={cn("w-1.5 h-1.5 rounded-full animate-pulse", f.is_false_positive ? "bg-neon-red" : "bg-neon-green")} />
                                    AI_VERIFICATION_PROTOCOL: {f.is_false_positive ? "ANOMALY_DETECTED" : "SIGNATURE_MATCH"}
                                    {f.ai_confidence && (
                                      <span className="opacity-40 font-mono ml-2">[{ (f.ai_confidence * 100).toFixed(0) }%_CONFIDENCE]</span>
                                    )}
                                  </h4>
                                  
                                  {/* User Feedback Buttons */}
                                  <div className="flex items-center gap-2 bg-black/40 p-1 rounded-lg border border-white/5">
                                    <span className="text-[8px] text-gray-500 font-bold uppercase tracking-widest px-2">Validate AI?</span>
                                    <button 
                                      onClick={(e) => { e.stopPropagation(); handleFeedback(f.id, 'confirmed_valid'); }}
                                      disabled={!!aiLoading[f.id]}
                                      className={cn(
                                        "p-1.5 rounded transition-all",
                                        f.user_verification === 'confirmed_valid' 
                                          ? "bg-neon-green text-black" 
                                          : "bg-gray-800/50 text-gray-500 hover:text-neon-green"
                                      )}
                                      title="Confirm as Valid"
                                    >
                                      <ThumbsUp className="w-3 h-3" />
                                    </button>
                                    <button 
                                      onClick={(e) => { e.stopPropagation(); handleFeedback(f.id, 'confirmed_fp'); }}
                                      disabled={!!aiLoading[f.id]}
                                      className={cn(
                                        "p-1.5 rounded transition-all",
                                        f.user_verification === 'confirmed_fp' 
                                          ? "bg-neon-red text-black" 
                                          : "bg-gray-800/50 text-gray-500 hover:text-neon-red"
                                      )}
                                      title="Confirm as False Positive"
                                    >
                                      <ThumbsDown className="w-3 h-3" />
                                    </button>
                                  </div>
                                </div>
                                <div className="relative">
                                  <div className={cn("absolute left-0 top-0 bottom-0 w-0.5", f.is_false_positive ? "bg-neon-red/30" : "bg-neon-green/30")} />
                                  <p className={cn(
                                    "text-[13px] leading-relaxed font-mono pl-4 italic",
                                    f.is_false_positive ? "text-neon-red/80" : "text-neon-green/80"
                                  )}>
                                    &quot;{f.ai_reasoning}&quot;
                                  </p>
                                </div>
                              </div>
                            )}

                            {f.ai_explanation && (
                              <div className={cn("space-y-2 relative z-10", f.ai_reasoning && "pt-4 border-t border-white/5")}>
                                <h4 className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] flex items-center gap-2">
                                  <Zap className="w-3 h-3 text-neon-green" />
                                  Intelligence Deep Dive
                                </h4>
                                <p className="text-[13px] text-gray-300 leading-relaxed font-sans">
                                  {f.ai_explanation}
                                </p>
                              </div>
                            )}
                            
                            {f.ai_remediation && (
                              <div className="space-y-3 pt-4 border-t border-white/5 relative z-10">
                                <div className="flex flex-wrap items-center justify-between gap-3">
                                  <h4 className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] flex items-center gap-2">
                                    <Shield className="w-3 h-3 text-blue-400" />
                                    Strategic Remediation Plan
                                  </h4>
                                  <div className="flex flex-wrap items-center gap-2">
                                    <select 
                                      className="bg-black border border-white/10 rounded px-2 py-1 text-[10px] font-bold text-gray-300 uppercase outline-none"
                                      value={remediationLanguages[f.id] || ''}
                                      onChange={(e) => setRemediationLanguages(prev => ({ ...prev, [f.id]: e.target.value }))}
                                    >
                                      <option value="">Linguagem (Auto)</option>
                                      <option value="Python">Python</option>
                                      <option value="Node.js">Node.js</option>
                                      <option value="PHP">PHP</option>
                                      <option value="Java">Java</option>
                                      <option value="C#">C#</option>
                                      <option value="Go">Go</option>
                                      <option value="Ruby">Ruby</option>
                                    </select>
                                    <button 
                                      onClick={() => handleAIAction(f.id, 'remediate', remediationLanguages[f.id])}
                                      disabled={!!aiLoading[f.id]}
                                      className="flex items-center gap-2 px-3 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-400 rounded text-[10px] font-bold uppercase hover:bg-blue-500/20 disabled:opacity-50"
                                    >
                                      {aiLoading[f.id] === 'remediate' ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
                                      RE-GERAR
                                    </button>
                                    <button
                                      onClick={() => setCopilotOpen(prev => ({ ...prev, [f.id]: !prev[f.id] }))}
                                      className="flex items-center gap-2 px-3 py-1 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 text-[10px] rounded font-bold uppercase border border-emerald-500/30"
                                    >
                                      <Bot className="w-3 h-3" />
                                      {copilotOpen[f.id] ? "FECHAR COPILOT" : "AI COPILOT"}
                                    </button>
                                  </div>
                                </div>
                                <div className="bg-black/60 p-4 rounded-lg border border-white/5 text-[12px] text-gray-300 leading-relaxed whitespace-pre-wrap font-mono">
                                  {f.ai_remediation}
                                </div>
                                {copilotOpen[f.id] && (
                                  <FindingCopilot findingId={f.id} />
                                )}
                              </div>
                            )}

                            {!f.ai_explanation && (
                              <div className="flex flex-wrap gap-3 pt-2 border-t border-white/5">
                                <button 
                                  onClick={() => handleAIAction(f.id, 'explain')}
                                  disabled={!!aiLoading[f.id]}
                                  className="flex items-center gap-2 px-3 py-1.5 bg-neon-green/10 border border-neon-green/30 text-neon-green rounded text-[10px] font-bold uppercase tracking-widest hover:bg-neon-green/20 transition-all disabled:opacity-50"
                                >
                                  {aiLoading[f.id] === 'explain' ? <Loader2 className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}
                                  AI DEEP DIVE
                                </button>
                                <button 
                                  onClick={() => handleAnalyzeFP(f.id)}
                                  disabled={!!aiLoading[f.id]}
                                  className="flex items-center gap-2 px-3 py-1.5 bg-gray-500/10 border border-gray-500/30 text-gray-400 rounded text-[10px] font-bold uppercase tracking-widest hover:bg-gray-500/20 transition-all disabled:opacity-50"
                                >
                                  {aiLoading[f.id] === 'analyze-fp' ? <Loader2 className="w-3 h-3 animate-spin" /> : <AlertTriangle className="w-3 h-3" />}
                                  REFRESH AI ANALYSIS
                                </button>
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
                                <div className="flex items-center rounded border border-blue-500/30 bg-blue-500/5 overflow-hidden">
                                  <select 
                                    className="bg-transparent border-none px-2 py-1.5 text-[10px] font-bold text-gray-300 uppercase outline-none focus:ring-0"
                                    value={remediationLanguages[f.id] || ''}
                                    onChange={(e) => setRemediationLanguages(prev => ({ ...prev, [f.id]: e.target.value }))}
                                  >
                                    <option value="">Linguagem (Auto)</option>
                                    <option value="Python">Python</option>
                                    <option value="Node.js">Node.js</option>
                                    <option value="PHP">PHP</option>
                                    <option value="Java">Java</option>
                                    <option value="C#">C#</option>
                                    <option value="Go">Go</option>
                                    <option value="Ruby">Ruby</option>
                                  </select>
                                  <button 
                                    onClick={() => handleAIAction(f.id, 'remediate', remediationLanguages[f.id])}
                                    disabled={!!aiLoading[f.id]}
                                    className="flex items-center gap-2 px-3 py-1.5 bg-blue-500/10 text-blue-400 text-[10px] font-bold uppercase tracking-widest hover:bg-blue-500/20 transition-all disabled:opacity-50 border-l border-blue-500/30"
                                  >
                                    {aiLoading[f.id] === 'remediate' ? <Loader2 className="w-3 h-3 animate-spin" /> : <Shield className="w-3 h-3" />}
                                    GERAR REMEDIAÇÃO
                                  </button>
                                </div>
                                <button 
                                  onClick={() => handleVerifyFinding(f.id)}
                                  disabled={!!aiLoading[f.id]}
                                  className="flex items-center gap-2 px-3 py-1.5 bg-neon-yellow/10 border border-neon-yellow/30 text-neon-yellow rounded text-[10px] font-bold uppercase tracking-widest hover:bg-neon-yellow/20 transition-all disabled:opacity-50"
                                >
                                  {aiLoading[f.id] === 'verify' ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle className="w-3 h-3" />}
                                  VERIFICAR VULNERABILIDADE
                                </button>
                                <button 
                                  onClick={() => handleGeneratePOC(f.id)}
                                  disabled={!!aiLoading[f.id] || !!f.poc}
                                  className="flex items-center gap-2 px-3 py-1.5 bg-purple-500/10 border border-purple-500/30 text-purple-400 rounded text-[10px] font-bold uppercase tracking-widest hover:bg-purple-500/20 transition-all disabled:opacity-50"
                                >
                                  {aiLoading[f.id] === 'poc' ? <Loader2 className="w-3 h-3 animate-spin" /> : <FileText className="w-3 h-3" />}
                                  {f.poc ? 'POC GERADA' : 'GERAR POC COM IA'}
                                </button>
                                <button 
                                    onClick={() => handleAnalyzeFP(f.id)}
                                    disabled={!!aiLoading[f.id]}
                                    className="flex items-center gap-2 px-3 py-1.5 bg-gray-500/10 border border-gray-500/30 text-gray-400 rounded text-[10px] font-bold uppercase tracking-widest hover:bg-gray-500/20 transition-all disabled:opacity-50"
                                  >
                                    {aiLoading[f.id] === 'analyze-fp' ? <Loader2 className="w-3 h-3 animate-spin" /> : <AlertTriangle className="w-3 h-3" />}
                                    RE-ANALISAR FALSE POSITIVE
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
