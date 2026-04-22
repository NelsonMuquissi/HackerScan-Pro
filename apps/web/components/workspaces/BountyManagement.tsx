'use client';

import { useState, useEffect } from 'react';
import { 
  Shield, 
  Plus, 
  Trash2, 
  Settings, 
  Eye, 
  CheckCircle, 
  XSquare, 
  MessageSquare,
  AlertTriangle,
  Loader2,
  ExternalLink,
  Target,
  DollarSign,
  Briefcase,
  User,
  Clock,
  ChevronRight
} from 'lucide-react';
import { 
  getWorkspaceBountyPrograms, 
  createBountyProgram, 
  getMe, 
  getWorkspaceSubmissions, 
  triageSubmission, 
  resolveSubmission 
} from '@/lib/api';
import { cn } from '@/lib/utils';

export function BountyManagement() {
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'programs' | 'submissions'>('programs');
  const [programs, setPrograms] = useState<any[]>([]);
  const [submissions, setSubmissions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [selectedSubmission, setSelectedSubmission] = useState<any | null>(null);
  
  const [newProgram, setNewProgram] = useState({
    title: '',
    description: '',
    scope: '',
    critical_reward: '5000',
    high_reward: '2000',
    medium_reward: '500'
  });

  const [triageData, setTriageData] = useState({
    severity: '',
    payout_amount: 0,
    internal_notes: ''
  });

  useEffect(() => {
    init();
  }, []);

  useEffect(() => {
    if (workspaceId) {
      if (activeTab === 'programs') loadPrograms();
      else loadSubmissions();
    }
  }, [workspaceId, activeTab]);

  async function init() {
    try {
      const me = await getMe();
      if (me.workspace_id) {
        setWorkspaceId(me.workspace_id);
      }
    } catch (error) {
      console.error('Failed to init workspace:', error);
    }
  }

  async function loadPrograms() {
    if (!workspaceId) return;
    setLoading(true);
    try {
      const data = await getWorkspaceBountyPrograms(workspaceId);
      const list = Array.isArray(data) ? data : (data?.results ?? []);
      setPrograms(list);
    } catch (error) {
      console.error('Failed to load programs:', error);
      setPrograms([]);
    } finally {
      setLoading(false);
    }
  }

  async function loadSubmissions() {
    if (!workspaceId) return;
    setLoading(true);
    try {
      const data = await getWorkspaceSubmissions(workspaceId);
      const list = Array.isArray(data) ? data : (data?.results ?? []);
      setSubmissions(list);
    } catch (error) {
      console.error('Failed to load submissions:', error);
      setSubmissions([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!workspaceId) return;
    try {
      await createBountyProgram({
        workspace: workspaceId,
        title: newProgram.title,
        description: newProgram.description,
        scope: newProgram.scope.split(',').map(s => s.trim()),
        rewards: {
          CRITICAL: newProgram.critical_reward,
          HIGH: newProgram.high_reward,
          MEDIUM: newProgram.medium_reward
        },
        status: 'ACTIVE'
      });
      setIsCreating(false);
      loadPrograms();
    } catch (error) {
      alert('Erro ao criar programa: ' + (error as any).message);
    }
  }

  async function handleTriage(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedSubmission) return;
    try {
      await triageSubmission(selectedSubmission.id, triageData);
      setSelectedSubmission(null);
      loadSubmissions();
    } catch (error) {
      alert('Erro na triagem: ' + (error as any).message);
    }
  }

  async function handleResolve(id: string) {
    if (!confirm('Deseja marcar esta submissão como resolvida?')) return;
    try {
      await resolveSubmission(id);
      loadSubmissions();
      if (selectedSubmission?.id === id) setSelectedSubmission(null);
    } catch (error) {
      alert('Erro ao resolver: ' + (error as any).message);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-black flex items-center gap-2">
            <Shield className="text-emerald-500" />
            HACKER HUB <span className="text-zinc-700 mx-2 text-xl font-light">/</span> GESTÃO
          </h2>
          <p className="text-zinc-500 text-sm">Controle seus programas de recompensas e triagem de vulnerabilidades.</p>
        </div>
        <div className="flex gap-2">
          <div className="bg-black/40 border border-zinc-800 p-1 rounded-2xl flex">
            <button 
              onClick={() => setActiveTab('programs')}
              className={cn(
                "px-4 py-2 rounded-xl text-sm font-bold transition-all",
                activeTab === 'programs' ? "bg-zinc-800 text-white" : "text-zinc-500 hover:text-zinc-300"
              )}
            >
              Programas
            </button>
            <button 
              onClick={() => setActiveTab('submissions')}
              className={cn(
                "px-4 py-2 rounded-xl text-sm font-bold transition-all flex items-center gap-2",
                activeTab === 'submissions' ? "bg-zinc-800 text-white" : "text-zinc-500 hover:text-zinc-300"
              )}
            >
              Submissões
              {submissions.filter(s => s.status === 'NEW').length > 0 && (
                <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
              )}
            </button>
          </div>
          <button 
            onClick={() => setIsCreating(true)}
            className="bg-emerald-500 text-black px-4 py-2 rounded-xl font-bold flex items-center gap-2 hover:bg-emerald-400 transition-colors"
          >
            <Plus className="w-4 h-4" /> Novo Programa
          </button>
        </div>
      </div>

      {activeTab === 'programs' ? (
        <>
          {isCreating && (
            <div className="bg-[#121212] border border-zinc-800 rounded-3xl p-8 mb-8 animate-in fade-in slide-in-from-top-4">
              <h3 className="text-xl font-bold mb-6">Configurar Novo Programa de Bounty</h3>
              <form onSubmit={handleCreate} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <div>
                      <label className="text-zinc-500 text-[10px] font-bold uppercase block mb-2">Nome do Programa</label>
                      <input 
                        required
                        className="w-full bg-black border border-zinc-800 rounded-xl px-4 py-3 focus:border-emerald-500 outline-none"
                        placeholder="Ex: Main Infrastructure VDP"
                        value={newProgram.title}
                        onChange={e => setNewProgram({...newProgram, title: e.target.value})}
                      />
                    </div>
                    <div>
                      <label className="text-zinc-500 text-[10px] font-bold uppercase block mb-2">Domínios em Escopo (Separados por vírgula)</label>
                      <input 
                        required
                        className="w-full bg-black border border-zinc-800 rounded-xl px-4 py-3 focus:border-emerald-500 outline-none font-mono text-sm"
                        placeholder="example.com, api.example.com"
                        value={newProgram.scope}
                        onChange={e => setNewProgram({...newProgram, scope: e.target.value})}
                      />
                    </div>
                  </div>
                  <div className="space-y-4">
                    <label className="text-zinc-500 text-[10px] font-bold uppercase block">Recompensas Padrão (USD)</label>
                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <span className="text-[10px] text-zinc-600 block mb-1 font-bold">CRITICAL</span>
                        <input 
                          className="w-full bg-black border border-zinc-800 rounded-xl px-3 py-2 text-emerald-500 font-mono text-sm"
                          value={newProgram.critical_reward}
                          onChange={e => setNewProgram({...newProgram, critical_reward: e.target.value})}
                        />
                      </div>
                      <div>
                        <span className="text-[10px] text-zinc-600 block mb-1 font-bold">HIGH</span>
                        <input 
                          className="w-full bg-black border border-zinc-800 rounded-xl px-3 py-2 text-orange-500 font-mono text-sm"
                          value={newProgram.high_reward}
                          onChange={e => setNewProgram({...newProgram, high_reward: e.target.value})}
                        />
                      </div>
                      <div>
                        <span className="text-[10px] text-zinc-600 block mb-1 font-bold">MEDIUM</span>
                        <input 
                          className="w-full bg-black border border-zinc-800 rounded-xl px-3 py-2 text-yellow-500 font-mono text-sm"
                          value={newProgram.medium_reward}
                          onChange={e => setNewProgram({...newProgram, medium_reward: e.target.value})}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <label className="text-zinc-500 text-[10px] font-bold uppercase block mb-2">Instruções e Regras (Markdown)</label>
                  <textarea 
                    rows={4}
                    className="w-full bg-black border border-zinc-800 rounded-xl px-4 py-3 focus:border-emerald-500 outline-none text-sm"
                    placeholder="Defina as regras de divulgação e exclusões..."
                    value={newProgram.description}
                    onChange={e => setNewProgram({...newProgram, description: e.target.value})}
                  />
                </div>

                <div className="flex gap-4">
                  <button 
                    type="submit"
                    className="flex-1 bg-emerald-500 text-black py-3 rounded-xl font-bold hover:bg-emerald-400 transition-all shadow-[0_0_20px_rgba(16,185,129,0.2)]"
                  >
                    PUBLICAR PROGRAMA
                  </button>
                  <button 
                    type="button"
                    onClick={() => setIsCreating(false)}
                    className="px-6 border border-zinc-800 rounded-xl hover:bg-zinc-900 transition-all text-zinc-400"
                  >
                    Cancelar
                  </button>
                </div>
              </form>
            </div>
          )}

          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 grayscale opacity-50">
              <Loader2 className="w-8 h-8 text-emerald-500 animate-spin mb-4" />
              <p className="text-sm font-mono text-zinc-500">Acedendo ao Kernel de Bounties...</p>
            </div>
          ) : programs.length > 0 ? (
            <div className="grid grid-cols-1 gap-4">
              {programs.map((program) => (
                <div key={program.id} className="bg-[#121212] border border-zinc-800 rounded-2xl p-6 flex items-center justify-between group hover:border-zinc-500 transition-all">
                  <div className="flex items-center gap-6">
                    <div className="w-14 h-14 bg-zinc-900 rounded-2xl flex items-center justify-center border border-zinc-800 group-hover:border-emerald-500/30 transition-colors shadow-inner">
                      <Target className="w-7 h-7 text-emerald-500" />
                    </div>
                    <div>
                      <h4 className="font-black text-lg text-white mb-1 uppercase tracking-tight">{program.title}</h4>
                      <div className="flex gap-4">
                        <span className="text-zinc-500 text-[10px] font-bold uppercase py-1 px-2 bg-black rounded-lg border border-zinc-800">
                          {program.status}
                        </span>
                        <span className="text-emerald-500 text-[10px] font-bold uppercase py-1 px-2 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                           {program.scope?.length || 0} Assets
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <button className="flex flex-col items-center justify-center w-12 h-12 bg-zinc-900 rounded-xl border border-zinc-800 hover:border-emerald-500/50 text-zinc-500 hover:text-emerald-500 transition-all">
                      <Eye className="w-5 h-5" />
                    </button>
                    <button className="flex flex-col items-center justify-center w-12 h-12 bg-zinc-900 rounded-xl border border-zinc-800 hover:border-red-500/50 text-zinc-500 hover:text-red-500 transition-all">
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-20 bg-zinc-900/10 border border-dashed border-zinc-800 rounded-3xl">
              <Shield className="w-12 h-12 text-zinc-800 mx-auto mb-4" />
              <p className="text-zinc-500 font-mono text-sm">Nenhum programa ativo. Comece criando um novo escopo.</p>
            </div>
          )}
        </>
      ) : (
        <div className="bg-[#121212] border border-zinc-800 rounded-3xl overflow-hidden animate-in fade-in zoom-in-95 duration-300">
          <div className="bg-zinc-900/50 border-b border-zinc-800 px-6 py-4 flex justify-between items-center font-mono text-[10px] uppercase font-black text-zinc-500">
            <div className="flex gap-8">
              <span>Relatório</span>
              <span>Pesquisador</span>
              <span>Domínio</span>
            </div>
            <div className="flex gap-8">
              <span>Severidade</span>
              <span>Status</span>
              <span>Ação</span>
            </div>
          </div>
          
          {loading ? (
            <div className="flex justify-center py-20">
              <Loader2 className="w-8 h-8 text-emerald-500 animate-spin" />
            </div>
          ) : submissions.length > 0 ? (
            <div className="divide-y divide-zinc-800/50">
              {submissions.map((sub) => (
                <div key={sub.id} className="p-6 flex items-center justify-between hover:bg-zinc-900/30 transition-colors">
                  <div className="flex items-center gap-6 flex-1">
                    <div className={cn(
                      "w-10 h-10 rounded-xl flex items-center justify-center border",
                      sub.proof_verified ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-500" : "bg-orange-500/10 border-orange-500/20 text-orange-500"
                    )}>
                      {sub.proof_verified ? <CheckCircle className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
                    </div>
                    <div className="min-w-[200px]">
                      <h4 className="font-bold text-white text-sm line-clamp-1">{sub.title}</h4>
                      <p className="text-zinc-500 text-[10px] flex items-center gap-1 mt-1 font-mono uppercase">
                        <User className="w-3 h-3" /> {sub.researcher_email}
                      </p>
                    </div>
                    <div className="px-3 py-1 bg-black rounded-lg border border-zinc-800 text-zinc-400 font-mono text-[10px]">
                      {sub.target_domain}
                    </div>
                  </div>

                  <div className="flex items-center gap-12">
                    <span className={cn(
                      "text-[10px] font-black uppercase px-2 py-1 rounded",
                      sub.severity === 'CRITICAL' ? 'text-red-500 bg-red-500/10' :
                      sub.severity === 'HIGH' ? 'text-orange-500 bg-orange-500/10' :
                      'text-yellow-500 bg-yellow-500/10'
                    )}>
                      {sub.severity}
                    </span>
                    <span className="text-zinc-400 text-[10px] font-bold uppercase min-w-[80px]">
                      {sub.status.replace('_', ' ')}
                    </span>
                    <button 
                      onClick={() => {
                        setSelectedSubmission(sub);
                        setTriageData({
                          severity: sub.severity,
                          payout_amount: Number(sub.payout_amount) || 0,
                          internal_notes: sub.internal_notes || ''
                        });
                      }}
                      className="flex items-center gap-2 bg-white text-black px-4 py-2 rounded-xl text-xs font-black hover:bg-zinc-200 transition-all uppercase tracking-tighter"
                    >
                      Triar <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-20 grayscale opacity-30">
              <MessageSquare className="w-12 h-12 text-zinc-700 mx-auto mb-4" />
              <p className="text-sm font-mono uppercase font-black tracking-widest">Vazio. Sem vulnerabilidades detectadas.</p>
            </div>
          )}
        </div>
      )}

      {/* Triage Modal */}
      {selectedSubmission && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-[#121212] border border-zinc-800 rounded-3xl w-full max-w-2xl animate-in zoom-in-95 duration-200 flex flex-col max-h-[90vh]">
            <div className="p-8 border-b border-zinc-800 flex justify-between items-start">
              <div>
                <div className="flex items-center gap-2 mb-2 text-zinc-500 uppercase font-black text-[10px] tracking-widest">
                  <Briefcase className="w-3 h-3" /> Triagem de Vulnerabilidade
                </div>
                <h3 className="text-2xl font-black text-white">{selectedSubmission.title}</h3>
                <p className="text-zinc-500 text-xs mt-1">Por: {selectedSubmission.researcher_email} • Enviado em {new Date(selectedSubmission.created_at).toLocaleDateString()}</p>
              </div>
              <button 
                onClick={() => setSelectedSubmission(null)}
                className="p-2 bg-zinc-900 rounded-full text-zinc-500 hover:text-white transition-colors"
              >
                <XSquare className="w-6 h-6" />
              </button>
            </div>

            <div className="p-8 overflow-y-auto flex-1 space-y-8">
              <div className="bg-black/50 border border-zinc-900 rounded-2xl p-6 font-mono text-sm text-zinc-300 whitespace-pre-wrap leading-relaxed">
                <div className="text-emerald-500 font-bold mb-4 uppercase text-xs flex items-center gap-2">
                  <Eye className="w-4 h-4" /> Descrição do Pesquisador
                </div>
                {selectedSubmission.description}
              </div>

              <form onSubmit={handleTriage} className="space-y-6">
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <label className="text-zinc-500 text-[10px] font-bold uppercase block mb-2 tracking-widest">Ajustar Severidade</label>
                    <select 
                      className="w-full bg-black border border-zinc-800 rounded-xl px-4 py-3 focus:border-red-500 outline-none uppercase font-black text-xs appearance-none cursor-pointer"
                      value={triageData.severity}
                      onChange={e => setTriageData({...triageData, severity: e.target.value})}
                    >
                      <option value="CRITICAL">Critical</option>
                      <option value="HIGH">High</option>
                      <option value="MEDIUM">Medium</option>
                      <option value="LOW">Low</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-zinc-500 text-[10px] font-bold uppercase block mb-2 tracking-widest">Recompensa (USD)</label>
                    <div className="relative">
                      <DollarSign className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-emerald-500" />
                      <input 
                        type="number"
                        className="w-full bg-black border border-zinc-800 rounded-xl pl-10 pr-4 py-3 focus:border-emerald-500 outline-none font-mono text-white"
                        value={triageData.payout_amount}
                        onChange={e => setTriageData({...triageData, payout_amount: Number(e.target.value)})}
                      />
                    </div>
                  </div>
                </div>

                <div>
                  <label className="text-zinc-500 text-[10px] font-bold uppercase block mb-2 tracking-widest">Notas Internas (Privado)</label>
                  <textarea 
                    rows={3}
                    className="w-full bg-black border border-zinc-800 rounded-xl px-4 py-3 focus:border-zinc-500 outline-none text-sm text-zinc-300 font-mono"
                    placeholder="Análise da equipe de segurança..."
                    value={triageData.internal_notes}
                    onChange={e => setTriageData({...triageData, internal_notes: e.target.value})}
                  />
                </div>

                <div className="flex gap-4 pt-4 border-t border-zinc-800/50">
                  <button 
                    type="submit"
                    className="flex-1 bg-white text-black py-4 rounded-2xl font-black text-xs uppercase tracking-widest hover:bg-zinc-200 transition-all shadow-[0_5px_15px_rgba(255,255,255,0.1)]"
                  >
                    ATUALIZAR TRIAGEM
                  </button>
                  {selectedSubmission.status !== 'RESOLVED' && (
                    <button 
                      type="button"
                      onClick={() => handleResolve(selectedSubmission.id)}
                      className="px-6 bg-emerald-500 text-black py-4 rounded-2xl font-black text-xs uppercase tracking-widest hover:bg-emerald-400 transition-all flex items-center gap-2"
                    >
                      RESOLVER & PAGAR <ChevronRight className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
