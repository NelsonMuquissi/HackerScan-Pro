'use client';

import React from 'react';
import { 
  Cpu, 
  Zap, 
  History, 
  Trophy, 
  Sparkles,
  ShieldCheck,
  TrendingUp,
  CreditCard
} from 'lucide-react';
import { useAICredits } from '@/hooks/useAICredits';
import { CreditPackagesList } from '@/components/ai/CreditPackagesList';
import { CreditHistoryTable } from '@/components/ai/CreditHistoryTable';
import { motion } from 'framer-motion';

export default function AICreditsPage() {
  const { wallet, transactions, achievements, loading } = useAICredits();

  return (
    <div className="space-y-12 pb-20">
      {/* Hero / Overview */}
      <section className="relative overflow-hidden rounded-[2.5rem] border border-border bg-card/30 p-8 md:p-12">
        <div className="absolute top-0 right-0 -m-12 w-64 h-64 bg-primary/10 blur-[100px] rounded-full" />
        <div className="absolute bottom-0 left-0 -m-12 w-64 h-64 bg-blue-500/10 blur-[100px] rounded-full" />
        
        <div className="relative grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div>
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20 text-primary mb-6">
              <Sparkles className="w-4 h-4" />
              <span className="text-xs font-black uppercase tracking-widest">IA Inteligência</span>
            </div>
            
            <h1 className="text-4xl md:text-5xl font-black tracking-tight mb-4 leading-tight">
              Acelere sua Segurança com <span className="text-primary">IA Generativa</span>
            </h1>
            <p className="text-muted-foreground text-lg mb-8 max-w-lg leading-relaxed">
              Utilize o poder do Claude 3.5 e Gemini para explicar vulnerabilidades, 
              gerar código de remediação e prever cadeias de ataque em segundos.
            </p>

            <div className="flex flex-wrap gap-4">
              <div className="flex items-center gap-3 bg-card p-4 rounded-2xl border border-border">
                <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary">
                  <Cpu className="w-6 h-6" />
                </div>
                <div>
                  <div className="text-[10px] uppercase font-bold text-muted-foreground">Saldo Total</div>
                  <div className="text-2xl font-black tracking-tight">
                    {wallet?.balance_total.toLocaleString() || '0'}
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-3 bg-card p-4 rounded-2xl border border-border">
                <div className="w-10 h-10 rounded-xl bg-yellow-400/10 flex items-center justify-center text-yellow-400">
                  <Zap className="w-6 h-6" />
                </div>
                <div>
                  <div className="text-[10px] uppercase font-bold text-muted-foreground">Mensal (Sub)</div>
                  <div className="text-2xl font-black tracking-tight">
                    {wallet?.balance_subscription.toLocaleString() || '0'}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-6 rounded-3xl bg-card border border-border hover:border-primary/50 transition-all group">
              <ShieldCheck className="w-8 h-8 text-primary mb-4 group-hover:scale-110 transition-transform" />
              <h3 className="font-bold mb-2">Segurança Pura</h3>
              <p className="text-xs text-muted-foreground">Seus dados nunca são usados para treinamento de modelos públicos.</p>
            </div>
            <div className="p-6 rounded-3xl bg-card border border-border hover:border-primary/50 transition-all group">
              <TrendingUp className="w-8 h-8 text-green-500 mb-4 group-hover:scale-110 transition-transform" />
              <h3 className="font-bold mb-2">Previsão Ativa</h3>
              <p className="text-xs text-muted-foreground">Antecipe ataques antes que eles aconteçam com IA preditiva.</p>
            </div>
            <div className="p-6 rounded-3xl bg-card border border-border hover:border-primary/50 transition-all group">
              <Trophy className="w-8 h-8 text-yellow-400 mb-4 group-hover:scale-110 transition-transform" />
              <h3 className="font-bold mb-2">Gamificação</h3>
              <p className="text-xs text-muted-foreground">Ganhe créditos bônus completando objetivos de segurança.</p>
            </div>
            <div className="p-6 rounded-3xl bg-card border border-border hover:border-primary/50 transition-all group">
              <CreditCard className="w-8 h-8 text-blue-500 mb-4 group-hover:scale-110 transition-transform" />
              <h3 className="font-bold mb-2">Sem Assinatura</h3>
              <p className="text-xs text-muted-foreground">Compre apenas o que precisar. Créditos adquiridos não expiram.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Packages Section */}
      <section className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-black tracking-tight">Adquirir Créditos</h2>
            <p className="text-muted-foreground text-sm">Escolha o pacote ideal para suas necessidades de auditoria.</p>
          </div>
        </div>
        <CreditPackagesList workspaceId={wallet?.workspace || ''} />
      </section>

      {/* History and Achievements */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-12">
        <div className="xl:col-span-2 space-y-6">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-primary" />
            <h2 className="text-xl font-bold">Histórico de Uso</h2>
          </div>
          <CreditHistoryTable transactions={transactions} loading={loading} />
        </div>

        <div className="space-y-6">
          <div className="flex items-center gap-2">
            <Trophy className="w-5 h-5 text-yellow-400" />
            <h2 className="text-xl font-bold">Conquistas</h2>
          </div>
          <div className="space-y-4">
            {achievements.length === 0 ? (
              <div className="p-8 border border-dashed rounded-3xl text-center">
                <p className="text-sm text-muted-foreground italic">Nenhuma conquista desbloqueada ainda.</p>
              </div>
            ) : (
              achievements.map((ach) => (
                <div key={ach.id} className="p-4 rounded-2xl border border-border bg-card/50 flex items-center gap-4">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center border ${
                    ach.is_unlocked ? 'bg-yellow-400/10 border-yellow-400/20 text-yellow-500' : 'bg-muted border-border text-muted-foreground grayscale opacity-50'
                  }`}>
                    <Trophy className="w-6 h-6" />
                  </div>
                  <div>
                    <div className="font-bold text-sm">{ach.name}</div>
                    <div className="text-[10px] text-muted-foreground">{ach.description}</div>
                    {ach.is_unlocked ? (
                      <div className="text-[10px] text-green-500 font-bold mt-1">GANHOU {ach.credits} CRÉDITOS</div>
                    ) : (
                      <div className="text-[10px] text-muted-foreground font-bold mt-1">RECOMPENSA: {ach.credits} CRÉDITOS</div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
