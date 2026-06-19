'use client';

import { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  Clock, 
  CheckCircle, 
  XSquare, 
  ExternalLink, 
  Terminal, 
  RefreshCw,
  Search,
  MessageSquare,
  DollarSign,
  ChevronLeft,
  Loader2,
  AlertCircle,
  FileText,
  Paperclip,
  Upload,
  Fingerprint,
  Download
} from 'lucide-react';
import Link from 'next/link';
import { 
  getResearcherSubmissions, 
  verifySubmissionProof, 
  generateSubmissionCertificate,
  uploadSubmissionAttachment,
  getBountyTransparencyLog
} from '@/lib/api';

export default function ResearcherSubmissionsPage() {
  const [submissions, setSubmissions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [verifyingId, setVerifyingId] = useState<string | null>(null);
  const [generatingId, setGeneratingId] = useState<string | null>(null);
  const [uploadingId, setUploadingId] = useState<string | null>(null);
  const [showLog, setShowLog] = useState(false);
  const [logs, setLogs] = useState<any[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [logPage, setLogPage] = useState(1);
  const [hasMoreLogs, setHasMoreLogs] = useState(false);
  const [logFilter, setLogFilter] = useState('');

  useEffect(() => {
    loadSubmissions();
  }, []);

  async function loadSubmissions() {
    try {
      const data = await getResearcherSubmissions();
      // Handle both plain arrays and paginated responses { results: [...] }
      let list: any[] = [];
      if (Array.isArray(data)) {
        list = data;
      } else if (data && typeof data === 'object' && 'results' in data) {
        list = (data as any).results;
      }
      setSubmissions(list);
    } catch (error) {
      console.error('Failed to load submissions:', error);
      setSubmissions([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleVerify(id: string) {
    setVerifyingId(id);
    try {
      const result = await verifySubmissionProof(id);
      alert(result.message);
      loadSubmissions();
    } catch (error) {
      alert('Falha na verificação: ' + (error as any).message);
    } finally {
      setVerifyingId(null);
    }
  }

  async function handleGenerateCertificate(id: string) {
    setGeneratingId(id);
    try {
      const result = await generateSubmissionCertificate(id);
      window.open(result.certificate_url, '_blank');
      loadSubmissions();
    } catch (error) {
      alert('Falha ao gerar certificado: ' + (error as any).message);
    } finally {
      setGeneratingId(null);
    }
  }

  async function handleFileUpload(id: string, e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingId(id);
    try {
      await uploadSubmissionAttachment(id, file);
      alert('Anexo enviado com sucesso!');
      loadSubmissions();
    } catch (error) {
      alert('Erro no upload: ' + (error as any).message);
    } finally {
      setUploadingId(null);
    }
  }

  async function handleShowLogs() {
    setShowLog(true);
    setLoadingLogs(true);
    setLogPage(1);
    try {
      const data = await getBountyTransparencyLog(1);
      let list: any[] = [];
      let more = false;
      if (Array.isArray(data)) {
        list = data;
      } else if (data && typeof data === 'object' && 'results' in data) {
        list = (data as any).results;
        more = !!(data as any).next;
      }
      setLogs(list);
      setHasMoreLogs(more);
    } catch (error) {
      console.error('Failed to load logs:', error);
    } finally {
      setLoadingLogs(false);
    }
  }

  async function handleLoadMoreLogs() {
    const nextPage = logPage + 1;
    setLoadingLogs(true);
    try {
      const data = await getBountyTransparencyLog(nextPage);
      let list: any[] = [];
      let more = false;
      if (Array.isArray(data)) {
        list = data;
      } else if (data && typeof data === 'object' && 'results' in data) {
        list = (data as any).results;
        more = !!(data as any).next;
      }
      setLogs(prev => [...prev, ...list]);
      setLogPage(nextPage);
      setHasMoreLogs(more);
    } catch (error) {
      console.error('Failed to load more logs:', error);
    } finally {
      setLoadingLogs(false);
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'NEW': return 'text-blue-400 bg-blue-400/10 border-blue-400/20';
      case 'TRIAGED': return 'text-amber-400 bg-amber-400/10 border-amber-400/20';
      case 'RESOLVED': return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20';
      case 'DUPLICATE': return 'text-zinc-500 bg-zinc-500/10 border-zinc-500/20';
      default: return 'text-zinc-500 bg-zinc-500/10 border-zinc-500/20';
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white p-8">
      <div className="max-w-6xl mx-auto">
        <Link 
          href="/dashboard/bounty" 
          className="flex items-center gap-2 text-zinc-500 hover:text-white transition-colors mb-8 group"
        >
          <ChevronLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
          Voltar para o Diretório
        </Link>

        <div className="flex items-center justify-between mb-12">
          <div>
            <h1 className="text-4xl font-black mb-2 flex items-center gap-3">
              <ShieldCheck className="text-emerald-500 w-10 h-10" />
              PORTAL DO PESQUISADOR
            </h1>
            <p className="text-zinc-500">Acompanhe o status de suas descobertas e recompensas.</p>
          </div>
          <div className="flex gap-4">
             <button 
               onClick={handleShowLogs}
               className="bg-zinc-900 border border-zinc-800 p-4 rounded-2xl flex items-center gap-3 hover:border-emerald-500/50 transition-all group"
             >
                <Terminal className="text-zinc-500 group-hover:text-emerald-500 w-6 h-6 transition-colors" />
                <div className="text-left">
                   <div className="text-zinc-500 text-[10px] font-bold uppercase">Transparency Log</div>
                   <div className="text-sm font-bold">Ver Auditoria Pública</div>
                </div>
             </button>
             <div className="bg-zinc-900 border border-zinc-800 p-4 rounded-2xl flex items-center gap-4">
                <DollarSign className="text-emerald-500 w-8 h-8" />
                <div>
                   <div className="text-zinc-500 text-[10px] font-bold uppercase">Total Ganho</div>
                   <div className="text-2xl font-black">$0.00</div>
                </div>
             </div>
          </div>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="w-10 h-10 text-emerald-500 animate-spin mb-4" />
            <p className="text-zinc-500 font-mono tracking-widest">Sincronizando Nexus...</p>
          </div>
        ) : submissions.length > 0 ? (
          <div className="space-y-4">
            {submissions.map((sub) => (
              <div key={sub.id} className="bg-[#121212] border border-zinc-800 rounded-3xl p-8 hover:border-zinc-700 transition-all shadow-xl">
                <div className="flex flex-col lg:flex-row justify-between gap-8">
                  <div className="flex-1 space-y-6">
                    <div>
                      <div className="flex items-center gap-3 mb-3">
                         <span className={`px-3 py-1 rounded-full text-[10px] font-bold border ${getStatusColor(sub.status)}`}>
                           {sub.status}
                         </span>
                         <span className="text-zinc-600 text-xs font-mono">{sub.id.substring(0,8)}</span>
                      </div>
                      <h3 className="text-2xl font-bold mb-2 group cursor-pointer flex items-center gap-2">
                        {sub.title}
                        <ExternalLink className="w-4 h-4 text-zinc-700 group-hover:text-emerald-500 transition-colors" />
                      </h3>
                      <p className="text-zinc-500 text-sm flex items-center gap-2">
                         <Target className="w-4 h-4" /> {sub.program_title}
                      </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {sub.proof_verified ? (
                        <div className="p-4 bg-emerald-500/5 border border-emerald-500/10 rounded-2xl flex items-start gap-3">
                          <CheckCircle className="w-5 h-5 text-emerald-500 mt-1" />
                          <div>
                            <div className="text-sm text-white font-bold mb-1">PoP Validado</div>
                            <div className="text-xs text-zinc-400 leading-relaxed">
                              Sua descoberta foi validada via Proof-of-Possession. O controle do domínio foi confirmado.
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="p-4 bg-zinc-950 border border-zinc-800 rounded-2xl space-y-3">
                          <div className="flex items-center gap-2 text-amber-500 text-[10px] font-bold uppercase px-2 py-1 bg-amber-500/10 w-fit rounded">
                            <Terminal className="w-3 h-3" /> Verificação Necessária
                          </div>
                          <div className="bg-black p-3 rounded-xl border border-zinc-800 flex items-center justify-between group/token">
                            <code className="text-emerald-400 font-mono text-[10px] break-all">{sub.proof_token}</code>
                            <button 
                              onClick={() => {
                                navigator.clipboard.writeText(sub.proof_token);
                                alert('Token copiado!');
                              }}
                              className="text-zinc-600 hover:text-white transition-colors p-1"
                            >
                              <RefreshCw className="w-3 h-3" />
                            </button>
                          </div>
                        </div>
                      )}

                      <div className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-2xl space-y-3">
                        <div className="flex items-center gap-2 text-zinc-400 text-[10px] font-bold uppercase px-2 py-1 bg-zinc-800 w-fit rounded">
                          <Fingerprint className="w-3 h-3 text-emerald-500" /> Audit Integrity Hash
                        </div>
                        <code className="block text-[9px] text-zinc-600 font-mono break-all bg-black/30 p-2 rounded-lg border border-zinc-800/50">
                          {sub.verification_hash}
                        </code>
                      </div>
                    </div>

                    {/* Attachments Section */}
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <h4 className="text-zinc-500 text-[10px] font-bold uppercase tracking-widest flex items-center gap-2">
                          <Paperclip className="w-3 h-3" /> Evidências Técnicas ({sub.attachments?.length || 0})
                        </h4>
                        <div className="relative">
                          <input 
                            type="file" 
                            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10" 
                            onChange={(e) => handleFileUpload(sub.id, e)}
                            disabled={uploadingId === sub.id}
                          />
                          <button 
                            className="text-[10px] bg-zinc-800 hover:bg-zinc-700 text-white px-3 py-1 rounded-full transition-colors flex items-center gap-2"
                            disabled={uploadingId === sub.id}
                          >
                            {uploadingId === sub.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <Upload className="w-3 h-3" />}
                            ADICIONAR ANEXO
                          </button>
                        </div>
                      </div>
                      
                      {sub.attachments && sub.attachments.length > 0 ? (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          {sub.attachments.map((att: any) => (
                            <a 
                              key={att.id} 
                              href={att.file} 
                              target="_blank" 
                              rel="noreferrer"
                              className="flex items-center justify-between p-3 bg-black/40 border border-zinc-800/50 rounded-xl hover:border-emerald-500/30 transition-all group"
                            >
                              <div className="flex items-center gap-3 overflow-hidden">
                                <div className="w-8 h-8 rounded-lg bg-zinc-800 flex items-center justify-center shrink-0">
                                  <FileText className="w-4 h-4 text-zinc-500 group-hover:text-emerald-500 transition-colors" />
                                </div>
                                <div className="overflow-hidden">
                                  <div className="text-[11px] font-bold truncate">{att.filename}</div>
                                  <div className="text-[9px] text-zinc-600 font-mono">{(att.file_size / 1024).toFixed(1)} KB</div>
                                </div>
                              </div>
                              <Download className="w-3 h-3 text-zinc-700 group-hover:text-emerald-500 transition-colors" />
                            </a>
                          ))}
                        </div>
                      ) : (
                        <div className="text-center py-4 bg-black/20 border border-dashed border-zinc-800 rounded-xl">
                          <p className="text-[10px] text-zinc-600 uppercase font-mono tracking-tighter">Nenhuma evidência adicional anexada</p>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="lg:w-64 flex flex-col justify-between gap-4 border-l border-zinc-800/50 pl-0 lg:pl-8">
                    <div className="space-y-6">
                      <div className="text-right">
                        <div className="text-zinc-600 text-[10px] font-bold uppercase mb-1">PoP Status</div>
                        {sub.proof_verified ? (
                           <div className="flex items-center justify-end gap-1 text-emerald-500 text-xs font-bold">
                             <CheckCircle className="w-4 h-4" /> Verificado
                           </div>
                        ) : (
                           <button 
                             onClick={() => handleVerify(sub.id)}
                             disabled={verifyingId === sub.id}
                             className="flex items-center justify-end gap-1 text-amber-500 hover:text-amber-400 text-xs font-bold transition-colors disabled:opacity-50 ml-auto"
                           >
                             {verifyingId === sub.id ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Clock className="w-4 h-4" />}
                             Pedir Verificação
                           </button>
                        )}
                      </div>

                      <div className="text-right">
                        <div className="text-zinc-600 text-[10px] font-bold uppercase mb-1">Recompensa</div>
                        <div className="text-2xl font-black text-white">$ {sub.payout_amount}</div>
                      </div>

                      <div className="space-y-2">
                        {sub.compliance_certificate ? (
                          <a 
                            href={sub.compliance_certificate} 
                            target="_blank"
                            rel="noreferrer"
                            className="w-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 py-3 rounded-xl font-bold text-xs hover:bg-emerald-500/20 transition-all flex items-center justify-center gap-2"
                          >
                            <Download className="w-4 h-4" /> CERTIFICADO PDF
                          </a>
                        ) : (
                          <button 
                            onClick={() => handleGenerateCertificate(sub.id)}
                            disabled={generatingId === sub.id}
                            className="w-full bg-zinc-900 border border-zinc-800 text-white py-3 rounded-xl font-bold text-xs hover:border-emerald-500/50 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                          >
                            {generatingId === sub.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4 text-emerald-500" />}
                            GERAR CERTIFICADO
                          </button>
                        )}
                        <p className="text-[9px] text-zinc-500 text-center italic leading-tight">
                          Certificado de conformidade com hash criptográfico para fins de auditoria.
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex gap-2 justify-end">
                       <button className="p-3 bg-zinc-900 border border-zinc-800 rounded-xl hover:border-emerald-500/50 transition-colors text-zinc-500 hover:text-emerald-500">
                         <MessageSquare className="w-5 h-5" />
                       </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

        ) : (
          <div className="text-center py-20 bg-zinc-900/10 border border-dashed border-zinc-800 rounded-3xl">
            <ShieldCheck className="w-16 h-16 text-zinc-800 mx-auto mb-6" />
            <h2 className="text-xl font-bold mb-2">Sem atividade pública detectada</h2>
            <p className="text-zinc-500 mb-8">Você ainda não submeteu vulnerabilidades ao ecossistema.</p>
            <Link 
              href="/dashboard/bounty"
              className="bg-emerald-500 text-black px-8 py-3 rounded-xl font-bold hover:bg-emerald-400 transition-colors inline-block"
            >
              Explorar Programas
            </Link>
          </div>
        )}
      </div>

      {/* Transparency Log Modal */}
      {showLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={() => setShowLog(false)} />
          <div className="relative bg-[#121212] border border-zinc-800 w-full max-w-4xl max-h-[80vh] rounded-3xl overflow-hidden shadow-2xl flex flex-col">
            <div className="p-6 border-b border-zinc-800 flex items-center justify-between">
               <h2 className="text-xl font-bold flex items-center gap-3">
                  <Fingerprint className="text-emerald-500 w-6 h-6" />
                  BOUNTY TRANSPARENCY LOG
               </h2>
                <div className="flex items-center gap-4">
                   <Link 
                      href="/dashboard/bounty/transparency" 
                      className="text-xs text-emerald-500 hover:text-emerald-400 font-bold flex items-center gap-1 transition-colors"
                   >
                      VER TUDO <ExternalLink className="w-3 h-3" />
                   </Link>
                   <button onClick={() => setShowLog(false)} className="text-zinc-500 hover:text-white transition-colors">
                      <XSquare className="w-6 h-6" />
                   </button>
                </div>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6 scrollbar-hide">
               <div className="mb-6 flex gap-4">
                  <div className="flex-1 relative">
                     <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                     <input 
                        type="text" 
                        placeholder="Filtrar por ação ou ID do recurso..."
                        value={logFilter}
                        onChange={(e) => setLogFilter(e.target.value)}
                        className="w-full bg-black/40 border border-zinc-800 rounded-xl py-3 pl-12 pr-4 text-xs focus:border-emerald-500/50 outline-none transition-all"
                     />
                  </div>
               </div>

               {loadingLogs && logs.length === 0 ? (
                 <div className="flex items-center justify-center py-20">
                    <Loader2 className="w-8 h-8 text-emerald-500 animate-spin" />
                 </div>
               ) : logs.length > 0 ? (
                 <div className="space-y-4">
                    {logs.filter(log => 
                      log.action.toLowerCase().includes(logFilter.toLowerCase()) ||
                      (log.resource_id && log.resource_id.includes(logFilter))
                    ).map((log) => (
                      <div key={log.id} className="p-4 bg-black/40 border border-zinc-800/50 rounded-2xl hover:border-zinc-700 transition-all group">
                         <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center gap-3">
                               <div className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase ${
                                 log.action.includes('create') ? 'bg-emerald-500/10 text-emerald-500' :
                                 log.action.includes('triage') ? 'bg-amber-500/10 text-amber-500' :
                                 log.action.includes('verify') ? 'bg-purple-500/10 text-purple-500' :
                                 'bg-blue-500/10 text-blue-500'
                               }`}>
                                  {log.action.replace('bounty.', '').replace('.', ' ')}
                               </div>
                               <span className="text-zinc-500 text-[10px] font-mono">{new Date(log.created_at).toLocaleString()}</span>
                            </div>
                            <div className="flex items-center gap-2">
                               <span className="text-[10px] text-zinc-600 uppercase font-bold">Trace</span>
                               <code className="text-[9px] text-zinc-600 font-mono">{log.id.substring(0,8)}</code>
                            </div>
                         </div>
                         <div className="flex items-center gap-4 text-xs">
                            <div className="flex items-center gap-1.5 text-zinc-300">
                               <UserIcon className="w-3 h-3 text-zinc-500" />
                               {log.user_email}
                            </div>
                            <div className="flex items-center gap-1.5 text-zinc-500">
                               <Terminal className="w-3 h-3" />
                               {log.ip_address}
                            </div>
                            {log.resource_id && (
                              <div className="flex items-center gap-1.5 text-zinc-600 font-mono text-[10px]">
                                <Paperclip className="w-3 h-3" />
                                {log.resource_id.substring(0, 12)}...
                              </div>
                            )}
                         </div>
                         {log.metadata && Object.keys(log.metadata).length > 0 && (
                            <div className="mt-3 bg-black/60 p-4 rounded-xl border border-zinc-800/50 relative overflow-hidden">
                               <div className="absolute top-0 left-0 w-1 h-full bg-emerald-500/20" />
                               <pre className="text-[9px] text-emerald-400/70 font-mono overflow-x-auto">
                                  {JSON.stringify(log.metadata, null, 2)}
                                </pre>
                            </div>
                         )}
                      </div>
                    ))}

                    {hasMoreLogs && (
                      <button 
                        onClick={handleLoadMoreLogs}
                        disabled={loadingLogs}
                        className="w-full py-4 border border-zinc-800 border-dashed rounded-2xl text-zinc-500 hover:text-white hover:border-zinc-600 transition-all text-xs font-bold flex items-center justify-center gap-2 disabled:opacity-50"
                      >
                        {loadingLogs ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                        CARREGAR MAIS REGISTROS
                      </button>
                    )}
                 </div>
               ) : (
                 <div className="text-center py-20">
                    <p className="text-zinc-500">Nenhum log de transparência encontrado.</p>
                 </div>
               )}
            </div>
            
            <div className="p-6 border-t border-zinc-800 bg-black/20 flex items-center justify-between shrink-0">
               <div className="flex flex-col gap-1">
                  <p className="text-[10px] text-zinc-500 max-w-md">
                     Este log é imutável e registrado em tempo real para garantir a integridade de todas as submissões e triagens.
                  </p>
                  <p className="text-[9px] text-zinc-700 font-mono">
                    NEXUS_PROTOCOL_v1.4.2 // SHA256_VERIFIED
                  </p>
               </div>
               <div className="flex items-center gap-2 text-emerald-500 font-bold text-[10px] bg-emerald-500/10 px-3 py-1.5 rounded-full border border-emerald-500/20">
                  <CheckCircle className="w-3 h-3" /> VERIFICADO PELO NEXUS
               </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function UserIcon({ className }: { className?: string }) {
   return (
     <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
   )
}

function Target({ className }: { className?: string }) {
   return (
     <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>
   )
}
