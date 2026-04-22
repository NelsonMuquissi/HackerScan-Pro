'use client';

import { useState, useEffect } from 'react';
import { 
  Shield, 
  Search, 
  Terminal, 
  ExternalLink, 
  Zap, 
  Target, 
  DollarSign,
  Filter,
  ArrowRight,
  Loader2,
  LayoutGrid,
  Settings
} from 'lucide-react';
import Link from 'next/link';
import { getPublicBountyPrograms, getMe } from '@/lib/api';
import { cn } from '@/lib/utils';
import { BountyManagement } from '@/components/workspaces/BountyManagement';

export default function BountyDashboardPage() {
  const [view, setView] = useState<'directory' | 'manage'>('directory');
  const [programs, setPrograms] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [isWorkspaceAdmin, setIsWorkspaceAdmin] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [programsData, user] = await Promise.all([
        getPublicBountyPrograms(),
        getMe()
      ]);
      
      // Handle programs
      let list: any[] = [];
      if (Array.isArray(programsData)) list = programsData;
      else if (programsData?.results) list = (programsData as any).results;
      setPrograms(list);
      
      // Check if admin
      if (user.role === 'ADMIN' || user.role === 'OWNER' || user.workspace_id) {
        setIsWorkspaceAdmin(true);
      }
    } catch (error) {
      console.error('Failed to load bounty data:', error);
    } finally {
      setLoading(false);
    }
  }

  const filteredPrograms = programs.filter(p => 
    p.title.toLowerCase().includes(search.toLowerCase()) ||
    p.workspace_name?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white p-8">
      <div className="max-w-6xl mx-auto">
        {/* Navigation Overlays */}
        <div className="flex items-center justify-between mb-12">
          <div>
            <h1 className="text-4xl font-black mb-2 flex items-center gap-3">
              <Shield className="text-emerald-500 w-10 h-10" />
              HACKER HUB
            </h1>
            <p className="text-zinc-500 text-lg">
              {view === 'directory' 
                ? 'Descubra programas de vulnerabilidade e colabore com a segurança da rede.' 
                : 'Gerencie seus programas de recompensas e triagem de vulnerabilidades.'}
            </p>
          </div>
          
          <div className="flex gap-3">
            {isWorkspaceAdmin && (
              <div className="bg-zinc-900/50 border border-zinc-800 p-1 rounded-2xl flex">
                <button 
                  onClick={() => setView('directory')}
                  className={cn(
                    "px-4 py-2 rounded-xl text-sm font-bold transition-all flex items-center gap-2",
                    view === 'directory' ? "bg-zinc-800 text-white" : "text-zinc-500 hover:text-zinc-300"
                  )}
                >
                  <LayoutGrid className="w-4 h-4" /> Diretório
                </button>
                <button 
                  onClick={() => setView('manage')}
                  className={cn(
                    "px-4 py-2 rounded-xl text-sm font-bold transition-all flex items-center gap-2",
                    view === 'manage' ? "bg-zinc-800 text-white" : "text-zinc-500 hover:text-zinc-300"
                  )}
                >
                  <Settings className="w-4 h-4" /> Gestão
                </button>
              </div>
            )}
            {view === 'directory' && (
              <Link 
                href="/dashboard/bounty/submissions"
                className="flex items-center gap-2 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 px-6 py-3 rounded-xl border border-emerald-500/20 transition-all font-bold"
              >
                Minhas Submissões
                <ArrowRight className="w-4 h-4" />
              </Link>
            )}
          </div>
        </div>

        {view === 'directory' ? (
          <>
            {/* Search */}
            <div className="relative group mb-12">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-zinc-500 group-focus-within:text-emerald-500 transition-colors">
                <Search className="w-5 h-5" />
              </div>
              <input
                type="text"
                placeholder="Pesquisar por alvo, empresa ou tecnologia..."
                className="w-full bg-zinc-900/50 border border-zinc-800 rounded-2xl py-4 pl-12 pr-4 focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 outline-none transition-all text-lg placeholder:text-zinc-600 shadow-2xl"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>

            {loading ? (
              <div className="flex flex-col items-center justify-center py-20 bg-zinc-900/20 border border-zinc-800 rounded-3xl">
                <Loader2 className="w-12 h-12 text-emerald-500 animate-spin mb-4" />
                <p className="text-zinc-500 font-mono tracking-widest uppercase">Escaneando Diretórios...</p>
              </div>
            ) : filteredPrograms.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredPrograms.map((program) => (
                  <Link 
                    key={program.id}
                    href={`/dashboard/bounty/${program.id}`}
                    className="group relative bg-[#121212] border border-zinc-800 rounded-2xl p-6 hover:border-emerald-500/50 transition-all hover:translate-y-[-4px] shadow-lg overflow-hidden"
                  >
                    <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 blur-3xl rounded-full translate-x-1/2 -translate-y-1/2" />
                    
                    <div className="flex items-center gap-4 mb-6">
                      <div className="w-12 h-12 bg-zinc-900 rounded-xl flex items-center justify-center border border-zinc-800 group-hover:border-emerald-500/30 transition-colors">
                        <Target className="w-6 h-6 text-emerald-500" />
                      </div>
                      <div>
                        <h3 className="font-bold text-lg group-hover:text-emerald-400 transition-colors leading-tight">
                          {program.title}
                        </h3>
                        <p className="text-zinc-500 text-sm">{program.workspace_name}</p>
                      </div>
                    </div>

                    <div className="space-y-4 mb-6">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-zinc-500 flex items-center gap-2">
                          <Target className="w-4 h-4" /> Alvos
                        </span>
                        <span className="font-mono text-zinc-300">{program.scope?.length || 0} Assets</span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-zinc-500 flex items-center gap-2">
                          <DollarSign className="w-4 h-4" /> Recompensa Máx.
                        </span>
                        <span className="font-mono text-white font-bold">$ {program.rewards.CRITICAL || '0'}</span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-4 border-t border-zinc-800">
                      <div className="flex gap-2">
                        <span className="px-2 py-1 bg-zinc-900 text-zinc-400 text-[10px] font-bold rounded uppercase tracking-tighter border border-zinc-800">
                          Verificado
                        </span>
                        <span className="px-2 py-1 bg-emerald-500/10 text-emerald-500 text-[10px] font-bold rounded uppercase tracking-tighter border border-emerald-500/20">
                          Público
                        </span>
                      </div>
                      <Zap className="w-4 h-4 text-emerald-500 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="text-center py-20 bg-zinc-900/20 border border-dashed border-zinc-800 rounded-3xl">
                <Search className="w-12 h-12 text-zinc-800 mx-auto mb-4" />
                <h2 className="text-xl font-bold mb-2">Nenhum programa encontrado</h2>
                <p className="text-zinc-500">Tente uma busca diferente ou aguarde novas publicações.</p>
              </div>
            )}
          </>
        ) : (
          <BountyManagement />
        )}
      </div>

      {/* Stats Footer (Only for Directory) */}
      {view === 'directory' && (
        <div className="max-w-6xl mx-auto mt-20 grid grid-cols-1 md:grid-cols-3 gap-8 py-10 border-t border-zinc-900 opacity-50">
          <div className="text-center">
            <div className="text-3xl font-black text-white mb-2">99.9%</div>
            <div className="text-emerald-500 font-mono text-xs uppercase tracking-widest">Uptime de Verificação</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-black text-white mb-2">Instantâneo</div>
            <div className="text-emerald-500 font-mono text-xs uppercase tracking-widest">Triage AI Assistida</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-black text-white mb-2">Global</div>
            <div className="text-emerald-500 font-mono text-xs uppercase tracking-widest">Moeda Nexus Privada</div>
          </div>
        </div>
      )}
    </div>
  );
}
