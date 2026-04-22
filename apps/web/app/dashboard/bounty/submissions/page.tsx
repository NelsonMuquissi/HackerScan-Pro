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
  AlertCircle
} from 'lucide-react';
import Link from 'next/link';
import { getResearcherSubmissions, verifySubmissionProof } from '@/lib/api';

export default function ResearcherSubmissionsPage() {
  const [submissions, setSubmissions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [verifyingId, setVerifyingId] = useState<string | null>(null);

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
              <div key={sub.id} className="bg-[#121212] border border-zinc-800 rounded-2xl p-6 hover:border-zinc-700 transition-colors shadow-lg">
                <div className="flex flex-col md:flex-row justify-between gap-6">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                       <span className={`px-3 py-1 rounded-full text-[10px] font-bold border ${getStatusColor(sub.status)}`}>
                         {sub.status}
                       </span>
                       <span className="text-zinc-600 text-xs font-mono">{sub.id.substring(0,8)}</span>
                    </div>
                    <h3 className="text-xl font-bold mb-2 group cursor-pointer flex items-center gap-2">
                      {sub.title}
                      <ExternalLink className="w-4 h-4 text-zinc-700 group-hover:text-emerald-500 transition-colors" />
                    </h3>
                    <p className="text-zinc-500 text-sm flex items-center gap-2 mb-4">
                       <Target className="w-4 h-4" /> {sub.program_title}
                    </p>

                    {sub.proof_verified ? (
                      <div className="p-4 bg-emerald-500/5 border border-emerald-500/10 rounded-xl flex items-center gap-3">
                        <CheckCircle className="w-5 h-5 text-emerald-500" />
                        <div className="text-xs text-zinc-400">
                          <span className="text-emerald-500 font-bold">Verificado.</span> Sua descoberta foi validada via Proof-of-Possession.
                        </div>
                      </div>
                    ) : (
                      <div className="p-4 bg-zinc-950 border border-zinc-800 rounded-xl">
                        <div className="flex items-center gap-2 text-amber-500 text-[10px] font-bold uppercase mb-3 px-2 py-1 bg-amber-500/10 w-fit rounded">
                          <Terminal className="w-3 h-3" /> Instruções de Verificação (PoP)
                        </div>
                        <p className="text-xs text-zinc-400 mb-3 leading-relaxed">
                          Adicione o token abaixo como um registro <span className="text-white font-mono text-[9px]">TXT</span> em <span className="text-white font-mono text-[9px]">{sub.target_domain}</span> ou crie um arquivo em <span className="text-white font-mono text-[9px]">/.well-known/hackerscan-proof.txt</span>:
                        </p>
                        <div className="bg-black p-3 rounded-lg border border-zinc-800 flex items-center justify-between group/token">
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
                  </div>

                  <div className="flex flex-row md:flex-col justify-between items-end gap-2 shrink-0">
                    <div className="flex items-center gap-6">
                      <div className="text-right">
                        <div className="text-zinc-600 text-[10px] font-bold uppercase mb-1">PoP Status</div>
                        {sub.proof_verified ? (
                           <div className="flex items-center gap-1 text-emerald-500 text-xs font-bold">
                             <CheckCircle className="w-4 h-4" /> Verificado
                           </div>
                        ) : (
                           <button 
                             onClick={() => handleVerify(sub.id)}
                             disabled={verifyingId === sub.id}
                             className="flex items-center gap-1 text-amber-500 hover:text-amber-400 text-xs font-bold transition-colors disabled:opacity-50"
                           >
                             {verifyingId === sub.id ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Clock className="w-4 h-4" />}
                             Pedir Verificação
                           </button>
                        )}
                      </div>
                      <div className="text-right">
                        <div className="text-zinc-600 text-[10px] font-bold uppercase mb-1">Pagamento</div>
                        <div className="text-white font-mono font-bold">$ {sub.payout_amount}</div>
                      </div>
                    </div>
                    
                    <div className="flex gap-2">
                       <button className="p-2 bg-zinc-900 border border-zinc-800 rounded-lg hover:border-emerald-500/50 transition-colors text-zinc-500 hover:text-emerald-500">
                         <MessageSquare className="w-4 h-4" />
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
    </div>
  );
}

function Target({ className }: { className?: string }) {
   return (
     <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>
   )
}
