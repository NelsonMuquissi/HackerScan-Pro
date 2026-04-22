'use client';

import { useState, useEffect } from 'react';
import { 
  Shield, 
  Terminal, 
  AlertTriangle, 
  CheckCircle, 
  Target, 
  DollarSign, 
  FileText,
  Send,
  Info,
  Copy,
  ChevronLeft,
  Loader2,
  Lock
} from 'lucide-react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { getBountyProgram, submitFinding } from '@/lib/api';

export default function BountyDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const [program, setProgram] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [pastedToken, setPastedToken] = useState<string | null>(null);

  // Form State
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    severity: 'MEDIUM'
  });

  useEffect(() => {
    if (id) loadProgram();
  }, [id]);

  async function loadProgram() {
    try {
      const data = await getBountyProgram(id as string);
      setProgram(data);
    } catch (error) {
      console.error('Failed to load program:', error);
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const result = await submitFinding({
        program: id,
        ...formData
      });
      setPastedToken(result.proof_token);
      setSuccess(true);
    } catch (error) {
      alert('Erro ao enviar submissão: ' + (error as any).message);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-emerald-500 animate-spin" />
      </div>
    );
  }

  if (!program) return <div>Programa não encontrado.</div>;

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white p-8">
      <div className="max-w-5xl mx-auto">
        <Link 
          href="/dashboard/bounty" 
          className="flex items-center gap-2 text-zinc-500 hover:text-white transition-colors mb-8 group"
        >
          <ChevronLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
          Voltar para o Diretório
        </Link>

        {success ? (
          <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-3xl p-12 text-center shadow-2xl">
            <div className="w-20 h-20 bg-emerald-500 rounded-full flex items-center justify-center mx-auto mb-6 shadow-[0_0_30px_rgba(16,185,129,0.3)]">
              <CheckCircle className="w-10 h-10 text-black" />
            </div>
            <h1 className="text-3xl font-black mb-4">Submissão Enviada com Sucesso!</h1>
            <p className="text-zinc-400 mb-8 max-w-md mx-auto">
              Sua descoberta foi registrada. Para validar seu controle sobre o alvo, complete o desafio de <span className="text-emerald-400 font-bold">Proof-of-Possession</span> abaixo:
            </p>

            <div className="bg-black/50 border border-zinc-800 rounded-2xl p-8 max-w-2xl mx-auto text-left">
              <div className="flex items-center gap-2 text-emerald-500 mb-4 font-bold uppercase tracking-widest text-xs">
                <Lock className="w-4 h-4" /> Desafio Host-Based
              </div>
              <p className="text-zinc-400 text-sm mb-4">
                Crie um arquivo no diretório raiz do alvo reportado com o seguinte nome e conteúdo:
              </p>
              
              <div className="flex items-center justify-between bg-zinc-900 border border-zinc-700 rounded-xl p-4 font-mono text-emerald-400 text-sm mb-6">
                <span>hackerscan-{pastedToken}.txt</span>
                <button 
                  onClick={() => navigator.clipboard.writeText(`hackerscan-proof-\n${pastedToken}`)}
                  className="p-2 hover:bg-zinc-800 rounded-lg transition-colors text-zinc-500 hover:text-emerald-500"
                >
                  <Copy className="w-4 h-4" />
                </button>
              </div>

              <div className="flex items-start gap-3 bg-amber-500/5 border border-amber-500/20 p-4 rounded-xl text-amber-200 text-sm">
                <Info className="w-5 h-5 shrink-0" />
                <p>Nossos scanners verificarão este arquivo automaticamente em até 24h. A verificação manual acelera a triagem.</p>
              </div>
            </div>

            <button 
              onClick={() => router.push('/dashboard/bounty/submissions')}
              className="mt-10 bg-white text-black px-8 py-3 rounded-xl font-bold hover:bg-zinc-200 transition-colors"
            >
              Ir para Minhas Submissões
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Left Column: Info */}
            <div className="lg:col-span-2 space-y-8">
              <div className="bg-[#121212] border border-zinc-800 rounded-3xl p-8">
                <div className="flex items-center gap-4 mb-6">
                  <div className="w-16 h-16 bg-emerald-500/10 rounded-2xl flex items-center justify-center border border-emerald-500/20">
                    <Shield className="w-8 h-8 text-emerald-500" />
                  </div>
                  <div>
                    <h1 className="text-3xl font-black">{program.title}</h1>
                    <p className="text-zinc-500">Hosteado por {program.workspace_name}</p>
                  </div>
                </div>

                <div className="prose prose-invert max-w-none mb-10">
                  <h3 className="text-white text-lg font-bold mb-2">Descrição do Programa</h3>
                  <p className="text-zinc-400 whitespace-pre-wrap">{program.description}</p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-zinc-900/50 border border-zinc-800 p-6 rounded-2xl">
                    <Target className="text-emerald-500 mb-2 w-6 h-6" />
                    <h4 className="text-zinc-500 text-xs font-bold uppercase mb-1">Escopo</h4>
                    <ul className="text-sm space-y-1">
                      {program.scope?.map((s: string, idx: number) => (
                        <li key={idx} className="font-mono text-zinc-300">*.{s}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="bg-zinc-900/50 border border-zinc-800 p-6 rounded-2xl">
                    <DollarSign className="text-emerald-500 mb-2 w-6 h-6" />
                    <h4 className="text-zinc-500 text-xs font-bold uppercase mb-1">Rewards</h4>
                    <p className="text-emerald-400 font-bold">$100 - ${program.rewards.CRITICAL || '5,000'}</p>
                  </div>
                </div>
              </div>

              {/* Submission Form */}
              <div className="bg-[#121212] border border-zinc-800 rounded-3xl p-8">
                <h2 className="text-2xl font-black mb-6 flex items-center gap-2">
                  <Send className="w-6 h-6 text-emerald-500" />
                  SUBMETER DESCOBERTA
                </h2>
                <form onSubmit={handleSubmit} className="space-y-6">
                  <div className="space-y-2">
                    <label className="text-zinc-500 text-xs font-bold uppercase">Título da Vulnerabilidade</label>
                    <input 
                      required
                      placeholder="Ex: SQL Injection em /api/search"
                      className="w-full bg-black border border-zinc-800 rounded-xl py-3 px-4 focus:border-emerald-500 outline-none"
                      value={formData.title}
                      onChange={e => setFormData({...formData, title: e.target.value})}
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-zinc-500 text-xs font-bold uppercase">Severidade Estimada</label>
                    <select 
                      className="w-full bg-black border border-zinc-800 rounded-xl py-3 px-4 focus:border-emerald-500 outline-none appearance-none"
                      value={formData.severity}
                      onChange={e => setFormData({...formData, severity: e.target.value})}
                    >
                      <option value="CRITICAL">Critical (9.0 - 10.0)</option>
                      <option value="HIGH">High (7.0 - 8.9)</option>
                      <option value="MEDIUM">Medium (4.0 - 6.9)</option>
                      <option value="LOW">Low (0.1 - 3.9)</option>
                    </select>
                  </div>

                  <div className="space-y-2">
                    <label className="text-zinc-500 text-xs font-bold uppercase">Descrição Técnica (PoC)</label>
                    <textarea 
                      required
                      rows={6}
                      placeholder="Descreva os passos para reproduzir, impacto e sugestão de correção..."
                      className="w-full bg-black border border-zinc-800 rounded-xl py-4 px-4 focus:border-emerald-500 outline-none font-mono text-sm"
                      value={formData.description}
                      onChange={e => setFormData({...formData, description: e.target.value})}
                    />
                  </div>

                  <button 
                    disabled={submitting}
                    className="w-full bg-emerald-500 text-black py-4 rounded-xl font-black text-lg hover:bg-emerald-400 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    {submitting ? <Loader2 className="w-5 h-5 animate-spin" /> : 'ENVIAR REPORTE CRIPTOGRAFADO'}
                  </button>
                </form>
              </div>
            </div>

            {/* Right Column: Rules */}
            <div className="space-y-6">
              <div className="bg-zinc-900/40 border border-zinc-800 rounded-3xl p-6">
                <h3 className="text-white font-bold flex items-center gap-2 mb-4">
                  <AlertTriangle className="w-5 h-5 text-amber-500" />
                  Regras de Engajamento
                </h3>
                <ul className="space-y-3 text-sm text-zinc-400">
                  <li className="flex gap-2">
                    <span className="text-emerald-500">✓</span> 
                    Não realize ataques DoS/DDoS.
                  </li>
                  <li className="flex gap-2">
                    <span className="text-emerald-500">✓</span> 
                    Não acesse dados de outros usuários.
                  </li>
                  <li className="flex gap-2">
                    <span className="text-emerald-500">✓</span> 
                    Siga a Política de Divulgação Responsável.
                  </li>
                  <li className="flex gap-2">
                    <span className="text-emerald-500">✓</span> 
                    Teste apenas nos domínios em escopo.
                  </li>
                </ul>
              </div>

              <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-3xl p-6">
                <h3 className="text-emerald-500 font-bold flex items-center gap-2 mb-4">
                  <Terminal className="w-5 h-5" />
                  Recompensas Estimadas
                </h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-center bg-black/50 p-3 rounded-xl border border-zinc-800">
                    <span className="text-zinc-500 text-xs font-bold">CRITICAL</span>
                    <span className="text-emerald-400 font-mono font-bold">${program.rewards.CRITICAL || '5000'}+</span>
                  </div>
                  <div className="flex justify-between items-center bg-black/50 p-3 rounded-xl border border-zinc-800">
                    <span className="text-zinc-500 text-xs font-bold">HIGH</span>
                    <span className="text-emerald-400 font-mono font-bold">${program.rewards.HIGH || '2000'}+</span>
                  </div>
                  <div className="flex justify-between items-center bg-black/50 p-3 rounded-xl border border-zinc-800">
                    <span className="text-zinc-500 text-xs font-bold">MEDIUM</span>
                    <span className="text-emerald-400 font-mono font-bold">${program.rewards.MEDIUM || '500'}+</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
