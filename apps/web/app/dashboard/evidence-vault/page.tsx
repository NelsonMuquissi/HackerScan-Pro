'use client';

import { useState, useEffect } from 'react';
import { getEvidenceVault, logEvidenceAction, exportEvidenceVault, verifySubmissionIntegrity, adminVerifySubmissionIntegrity } from '@/lib/api';
import { useAuthStore } from '@/store/useAuthStore';
import { 
  Camera, 
  Shield, 
  FileText, 
  Search, 
  ExternalLink, 
  Filter, 
  AlertTriangle, 
  CheckCircle2, 
  Clock,
  ChevronRight,
  Maximize2,
  FileCode,
  Download,
  Zap,
  Package,
  Loader2,
  Terminal,
  Copy,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import Link from 'next/link';

interface EvidenceItem {
  id: string;
  type: 'SCAN_FINDING' | 'BOUNTY_SUBMISSION';
  title: string;
  severity: string;
  status: string;
  target_host?: string;
  scan_id?: string;
  compliance_mapping: any;
  visual_proof_b64: string | null;
  technical_details: any;
  created_at: string;
  poc: string;
  ai_explanation: string;
  verification_hash?: string;
}

function JsonViewer({ data }: { data: any }) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [copied, setCopied] = useState(false);

  if (!data || Object.keys(data).length === 0) {
    return <div className="text-gray-500 italic text-[10px] font-mono bg-black/20 p-4 rounded-lg border border-dashed border-white/5 uppercase tracking-widest">NO_ARTIFACT_METADATA_STREAM</div>;
  }
  
  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-black/40 rounded-xl border border-white/5 overflow-hidden font-mono transition-all group/json">
      <div 
        className="flex items-center justify-between px-4 py-2 border-b border-white/5 bg-white/[0.02] cursor-pointer hover:bg-white/[0.05]"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          <Terminal className="w-3 h-3 text-blue-400" />
          <span className="text-[9px] font-bold text-gray-500 uppercase tracking-widest">METADATA_PAYLOAD</span>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={handleCopy}
            className="text-[9px] text-gray-500 hover:text-white flex items-center gap-1 transition-colors"
          >
            {copied ? <CheckCircle2 className="w-3 h-3 text-neon-green" /> : <Copy className="w-3 h-3" />}
            {copied ? 'COPIED' : 'COPY'}
          </button>
          {isExpanded ? <ChevronUp className="w-3 h-3 text-gray-600" /> : <ChevronDown className="w-3 h-3 text-gray-600" />}
        </div>
      </div>
      
      {isExpanded && (
        <pre className="p-4 overflow-auto text-[10px] leading-relaxed text-blue-300 scrollbar-thin scrollbar-thumb-white/10 max-h-[300px]">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}

export default function EvidenceVaultPage() {
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [search, setSearch] = useState('');
  const [filterSeverity, setFilterSeverity] = useState('all');
  const [selectedItem, setSelectedItem] = useState<EvidenceItem | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState<{ is_valid: boolean; checked: boolean }>({ is_valid: false, checked: false });
  const { user } = useAuthStore();

  useEffect(() => {
    getEvidenceVault()
      .then(response => {
        // Handle both old array response and new paginated response for safety
        const items = Array.isArray(response) ? response : response.results;
        setEvidence(items);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const filteredEvidence = evidence.filter(item => {
    const matchesSearch = item.title.toLowerCase().includes(search.toLowerCase()) || 
                         item.target_host?.toLowerCase().includes(search.toLowerCase());
    const matchesSeverity = filterSeverity === 'all' || item.severity.toLowerCase() === filterSeverity.toLowerCase();
    return matchesSearch && matchesSeverity;
  });

  const downloadFile = (content: string, filename: string, type: string) => {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleSelectItem = (item: EvidenceItem) => {
    setSelectedItem(item);
    setVerificationResult({ is_valid: false, checked: false });
    logEvidenceAction(item.id, 'VIEW', item.type, { 
      source: 'evidence_vault',
      title: item.title,
      severity: item.severity 
    }).catch(console.error);
    logEvidenceAction(item.id, 'VIEW_DETAILS', item.type).catch(console.error);
  };

  const handleVerifyIntegrity = async (item: EvidenceItem) => {
    if (item.type !== 'BOUNTY_SUBMISSION') return;
    setVerifying(true);
    try {
      const isAdmin = user?.role === 'admin' || user?.role === 'superadmin';
      const result = isAdmin 
        ? await adminVerifySubmissionIntegrity(item.id)
        : await verifySubmissionIntegrity(item.id);
      
      setVerificationResult({ is_valid: result.is_valid, checked: true });
      logEvidenceAction(item.id, 'VERIFY_INTEGRITY', item.type, { is_valid: result.is_valid }).catch(console.error);
    } catch (error) {
      console.error('Verification failed:', error);
    } finally {
      setVerifying(false);
    }
  };

  const handleDownloadPOC = (item: EvidenceItem) => {
    if (!item.poc) return;
    downloadFile(item.poc, `poc-${item.id}.txt`, 'text/plain');
    logEvidenceAction(item.id, 'DOWNLOAD_POC', item.type).catch(console.error);
  };

  const handleExportEvidence = (item: EvidenceItem) => {
    const evidencePack = {
      finding: item.title,
      id: item.id,
      type: item.type,
      timestamp: item.created_at,
      target: item.target_host,
      compliance: item.compliance_mapping,
      poc: item.poc,
      ai_analysis: item.ai_explanation,
      visual_proof_present: !!item.visual_proof_b64,
      technical_details: item.technical_details,
      verification_hash: item.verification_hash
    };

    const manifest = {
      version: "1.0",
      generator: "HackerScan Pro Evidence Engine",
      artifact_id: item.id,
      fingerprint: item.verification_hash,
      signed_at: new Date().toISOString(),
      integrity_protocol: "SHA-256",
      compliance_ready: true
    };

    // Download manifest along with evidence pack
    downloadFile(JSON.stringify(evidencePack, null, 2), `evidence-pack-${item.id}.json`, 'application/json');
    downloadFile(JSON.stringify(manifest, null, 2), `manifest-${item.id}.json`, 'application/json');
    logEvidenceAction(item.id, 'EXPORT_JSON', item.type).catch(console.error);
  };

  const handleBulkExport = async () => {
    setExporting(true);
    try {
      const blob = await exportEvidenceVault();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `HackerScan-Evidence-Vault-${new Date().toISOString().split('T')[0]}.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setExporting(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'CRITICAL': return 'text-red-500 border-red-500/20 bg-red-500/10';
      case 'HIGH': return 'text-orange-500 border-orange-500/20 bg-orange-500/10';
      case 'MEDIUM': return 'text-yellow-500 border-yellow-500/20 bg-yellow-500/10';
      case 'LOW': return 'text-blue-500 border-blue-500/20 bg-blue-500/10';
      default: return 'text-gray-400 border-gray-500/20 bg-gray-500/10';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-mono font-bold text-foreground flex items-center gap-2">
            <Camera className="w-6 h-6 text-neon-green" />
            Evidence Vault
          </h1>
          <p className="text-gray-500 text-sm font-mono mt-1 uppercase tracking-tighter">
            Centralized repository for technical proofs, screenshots, and compliance mapping.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handleBulkExport}
            disabled={exporting || evidence.length === 0}
            className="flex items-center gap-2 bg-neon-green text-black font-mono font-bold text-xs px-4 py-2 rounded-lg hover:bg-neon-green/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {exporting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Package className="w-4 h-4" />
            )}
            EXPORT EVIDENCE BUNDLE (.ZIP)
          </button>
          
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input 
              type="text"
              placeholder="SEARCH EVIDENCE..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-[#0a0a0a] border border-white/5 rounded-lg pl-10 pr-4 py-2 text-xs font-mono focus:outline-none focus:border-neon-green/50 text-foreground w-64"
            />
          </div>
          <select 
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="bg-[#0a0a0a] border border-white/5 rounded-lg px-4 py-2 text-xs font-mono focus:outline-none focus:border-neon-green/50 text-gray-400 uppercase"
          >
            <option value="all">ALL SEVERITIES</option>
            <option value="critical">CRITICAL</option>
            <option value="high">HIGH</option>
            <option value="medium">MEDIUM</option>
            <option value="low">LOW</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <div key={i} className="bg-card-bg border border-card-border rounded-xl h-64 animate-pulse" />
          ))}
        </div>
      ) : filteredEvidence.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredEvidence.map(item => (
            <div 
              key={item.id}
              className="group bg-card-bg border border-card-border rounded-xl overflow-hidden hover:border-neon-green/30 transition-all cursor-pointer flex flex-col"
              onClick={() => handleSelectItem(item)}
            >
              {/* Preview Header */}
              <div className="aspect-video bg-black relative flex items-center justify-center overflow-hidden">
                {item.visual_proof_b64 ? (
                  <img 
                    src={`data:image/png;base64,${item.visual_proof_b64}`} 
                    alt={item.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                  />
                ) : (
                  <div className="flex flex-col items-center gap-2 opacity-20">
                    <Shield className="w-12 h-12 text-gray-400" />
                    <span className="text-[10px] font-mono">NO VISUAL PROOF</span>
                  </div>
                )}
                
                {/* HUD Overlay */}
                <div className="absolute top-3 left-3 flex gap-2">
                  <span className={`px-2 py-0.5 rounded text-[8px] font-mono font-bold border uppercase ${getSeverityColor(item.severity)}`}>
                    {item.severity}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[8px] font-mono font-bold border border-white/20 bg-black/50 text-white uppercase">
                    {item.type === 'SCAN_FINDING' ? 'SCAN' : 'BOUNTY'}
                  </span>
                </div>
                
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-4">
                   <button className="flex items-center gap-2 text-neon-green text-[10px] font-mono font-bold uppercase tracking-widest">
                     <Maximize2 className="w-3 h-3" /> Inspect Artifact
                   </button>
                </div>
              </div>

              {/* Card Body */}
              <div className="p-4 flex-1 flex flex-col gap-3">
                <div>
                  <h3 className="text-sm font-mono font-bold text-foreground line-clamp-1 group-hover:text-neon-green transition-colors">
                    {item.title}
                  </h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] font-mono text-gray-500 uppercase">{item.target_host}</span>
                    <span className="text-gray-700">•</span>
                    <span className="text-[10px] font-mono text-gray-500">{new Date(item.created_at).toLocaleDateString()}</span>
                  </div>
                </div>

                {/* Compliance Badges */}
                <div className="flex flex-wrap gap-1.5">
                  {item.compliance_mapping?.owasp && (
                    <span className="bg-blue-500/5 text-blue-400 border border-blue-500/10 px-1.5 py-0.5 rounded text-[8px] font-mono">
                      {item.compliance_mapping.owasp}
                    </span>
                  )}
                  {item.compliance_mapping?.mitre && (
                    <span className="bg-purple-500/5 text-purple-400 border border-purple-500/10 px-1.5 py-0.5 rounded text-[8px] font-mono">
                      {item.compliance_mapping.mitre}
                    </span>
                  )}
                </div>

                <div className="mt-auto flex items-center justify-between pt-3 border-t border-white/5">
                  <div className="flex items-center gap-1.5">
                    {item.status === 'resolved' ? (
                      <CheckCircle2 className="w-3 h-3 text-neon-green" />
                    ) : (
                      <AlertTriangle className="w-3 h-3 text-orange-500" />
                    )}
                    <span className="text-[9px] font-mono text-gray-400 uppercase tracking-widest">
                      {item.status}
                    </span>
                  </div>
                  {item.type === 'SCAN_FINDING' && item.scan_id ? (
                    <Link 
                      href={`/dashboard/scans/${item.scan_id}`}
                      onClick={(e) => e.stopPropagation()}
                      className="p-1.5 rounded-lg hover:bg-white/5 text-gray-500 hover:text-foreground transition-all"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </Link>
                  ) : (
                    <Link 
                      href={`/dashboard/bounty/submissions/${item.id}`}
                      onClick={(e) => e.stopPropagation()}
                      className="p-1.5 rounded-lg hover:bg-white/5 text-gray-500 hover:text-foreground transition-all"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </Link>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-card-bg border border-card-border rounded-xl p-20 text-center flex flex-col items-center justify-center">
          <Camera className="w-16 h-16 text-gray-700 mb-4" />
          <h2 className="text-xl font-mono font-bold text-gray-400">VAULT IS EMPTY</h2>
          <p className="text-gray-500 text-sm font-mono mt-2 max-w-md">
            Execute a deep-scan to capture visual proofs and automated compliance evidence for your audit trail.
          </p>
        </div>
      )}

      {/* Detail Modal */}
      {selectedItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90 backdrop-blur-sm animate-in fade-in">
          <div className="bg-[#0a0a0a] border border-white/10 rounded-2xl w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl shadow-neon-green/5">
            <div className="flex items-center justify-between p-6 border-b border-white/5">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg bg-white/5 ${getSeverityColor(selectedItem.severity)}`}>
                  <Shield className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-xl font-mono font-bold">{selectedItem.title}</h2>
                  <p className="text-xs font-mono text-gray-500 uppercase tracking-widest mt-0.5">{selectedItem.target_host}</p>
                </div>
              </div>
              <button 
                onClick={() => setSelectedItem(null)}
                className="text-gray-500 hover:text-white font-mono text-sm uppercase tracking-widest"
              >
                [CLOSE_VAULT]
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-8">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
                <div className="space-y-8">
                  {/* Visual Proof Section */}
                  <div>
                    <h3 className="text-[10px] font-mono font-bold text-neon-green uppercase tracking-[0.2em] mb-4 flex items-center gap-2">
                      <Camera className="w-3 h-3" /> Primary Visual Proof
                    </h3>
                    <div className="rounded-xl border border-white/5 bg-black overflow-hidden relative group">
                      {selectedItem.visual_proof_b64 ? (
                        <img 
                          src={`data:image/png;base64,${selectedItem.visual_proof_b64}`} 
                          alt="Evidence"
                          className="w-full h-auto"
                        />
                      ) : (
                        <div className="aspect-video flex items-center justify-center text-gray-700 italic text-xs font-mono">
                          NO CAPTURED FRAME AVAILABLE
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Compliance Section */}
                  <div>
                    <h3 className="text-[10px] font-mono font-bold text-blue-400 uppercase tracking-[0.2em] mb-4 flex items-center gap-2">
                      {selectedItem.type === 'SCAN_FINDING' ? (
                        <><Shield className="w-3 h-3" /> Compliance Mapping</>
                      ) : (
                        <><FileText className="w-3 h-3" /> Submission Metadata</>
                      )}
                    </h3>
                    <div className="grid grid-cols-2 gap-4">
                      {Object.entries(selectedItem.compliance_mapping || {}).length > 0 ? (
                        Object.entries(selectedItem.compliance_mapping || {}).map(([key, value]) => (
                          <div key={key} className="bg-white/5 border border-white/5 rounded-lg p-3">
                            <div className="text-[9px] font-mono text-gray-500 uppercase mb-1">{key}</div>
                            <div className="text-xs font-mono text-foreground font-bold">{value as string}</div>
                          </div>
                        ))
                      ) : (
                        <div className="col-span-2 bg-white/5 border border-white/5 border-dashed rounded-lg p-4 text-center">
                          <p className="text-[10px] font-mono text-gray-500 italic uppercase">NO_COMPLIANCE_MAPPING_DATA</p>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Digital Integrity Fingerprint */}
                  {selectedItem.verification_hash && (
                    <div>
                      <h3 className="text-[10px] font-mono font-bold text-emerald-400 uppercase tracking-[0.2em] mb-4 flex items-center gap-2">
                        <Shield className="w-3 h-3" /> Digital Integrity Fingerprint
                      </h3>
                      <div className="bg-emerald-500/5 border border-emerald-500/10 rounded-xl p-4 flex items-center justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="text-[9px] font-mono text-emerald-500/60 uppercase mb-1 font-bold">SHA-256 PROOF HASH</div>
                          <div className="text-[10px] font-mono text-emerald-400 font-bold break-all">{selectedItem.verification_hash}</div>
                        </div>
                        <div className="shrink-0 flex flex-col items-end gap-2">
                          <button
                            onClick={() => handleVerifyIntegrity(selectedItem)}
                            disabled={verifying}
                            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg font-mono text-[9px] font-bold transition-all ${
                              verificationResult.checked 
                                ? (verificationResult.is_valid ? 'bg-emerald-500 text-black' : 'bg-red-500 text-white')
                                : 'bg-emerald-500/20 text-emerald-500 hover:bg-emerald-500/30'
                            }`}
                          >
                            {verifying ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : verificationResult.checked ? (
                              verificationResult.is_valid ? (
                                <><CheckCircle2 className="w-3 h-3" /> VERIFIED</>
                              ) : (
                                <><AlertTriangle className="w-3 h-3" /> FAILED</>
                              )
                            ) : (
                              'VERIFY SIGNATURE'
                            )}
                          </button>
                          {verificationResult.checked && (
                            <div className="flex flex-col items-end gap-1">
                              <span className={`text-[8px] font-mono uppercase font-bold ${verificationResult.is_valid ? 'text-emerald-500' : 'text-red-500'}`}>
                                {verificationResult.is_valid ? 'Integrity Confirmed' : 'Integrity Mismatch'}
                              </span>
                              {verificationResult.is_valid && (
                                <span className="text-[7px] font-mono text-gray-500 uppercase tracking-widest text-right max-w-[150px]">
                                  Audit Trail Certified
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <div className="space-y-8">
                  {/* Technical Proof (POC) */}
                  <div>
                    <h3 className="text-[10px] font-mono font-bold text-orange-400 uppercase tracking-[0.2em] mb-4 flex items-center gap-2">
                      <FileCode className="w-3 h-3" /> Technical Evidence (POC)
                    </h3>
                    <div className="bg-black/50 border border-white/5 rounded-xl p-5 font-mono text-[11px] text-gray-300 relative group overflow-x-auto whitespace-pre">
                       <code>{selectedItem.poc || "// NO TECHNICAL POC PROVIDED"}</code>
                       {selectedItem.poc && (
                         <button 
                           onClick={() => handleDownloadPOC(selectedItem)}
                           className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity bg-white/10 hover:bg-white/20 p-2 rounded"
                         >
                           <Download className="w-3 h-3" />
                         </button>
                       )}
                    </div>
                  </div>

                  {/* AI Context / Researcher Context */}
                  <div>
                    <h3 className="text-[10px] font-mono font-bold text-purple-400 uppercase tracking-[0.2em] mb-4 flex items-center gap-2">
                      {selectedItem.type === 'SCAN_FINDING' ? (
                        <><Zap className="w-3 h-3" /> AI Analysis & Reasoning</>
                      ) : (
                        <><FileText className="w-3 h-3" /> Submission Context</>
                      )}
                    </h3>
                    <div className="bg-purple-500/5 border border-purple-500/10 rounded-xl p-5 italic text-sm text-gray-300 leading-relaxed">
                      &quot;{selectedItem.ai_explanation || (selectedItem.type === 'SCAN_FINDING' ? "No AI explanation available for this artifact." : "Researcher submission details.")}&quot;
                    </div>
                  </div>

                  {/* Structured Technical Metadata */}
                  <div>
                    <h3 className="text-[10px] font-mono font-bold text-blue-300 uppercase tracking-[0.2em] mb-4 flex items-center gap-2">
                      <Terminal className="w-3 h-3" /> Technical Metadata (JSON)
                    </h3>
                    <JsonViewer data={selectedItem.technical_details} />
                  </div>

                  <div className="pt-6 border-t border-white/5 flex gap-4">
                      <Link 
                        href={selectedItem.type === 'SCAN_FINDING' ? `/dashboard/scans/${selectedItem.scan_id}` : `/dashboard/bounty/submissions/${selectedItem.id}`}
                        className="flex-1 bg-white text-black font-mono font-bold text-[10px] uppercase tracking-widest py-3 rounded-lg text-center hover:bg-gray-200 transition-all"
                      >
                        {selectedItem.type === 'SCAN_FINDING' ? 'Full Report Access' : 'View Submission Details'}
                      </Link>
                     <button 
                       onClick={() => handleExportEvidence(selectedItem)}
                       className="flex-1 bg-white/5 border border-white/10 text-white font-mono font-bold text-[10px] uppercase tracking-widest py-3 rounded-lg hover:bg-white/10 transition-all"
                     >
                       Export Proof Folder
                     </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
