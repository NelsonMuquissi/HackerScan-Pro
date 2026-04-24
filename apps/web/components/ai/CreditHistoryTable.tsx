'use client';

import React from 'react';
import { 
  Cpu, 
  ArrowUpRight, 
  ArrowDownLeft, 
  Clock,
  ExternalLink,
  ChevronRight,
  Sparkles
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { ptBR } from 'date-fns/locale';

interface Transaction {
  id: string;
  type: 'debit' | 'credit';
  amount: number;
  action_display: string;
  created_at: string;
  balance_after: number;
}

interface CreditHistoryTableProps {
  transactions: Transaction[];
  loading?: boolean;
}

export const CreditHistoryTable: React.FC<CreditHistoryTableProps> = ({ 
  transactions, 
  loading 
}) => {
  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-16 w-full bg-muted animate-pulse rounded-2xl" />
        ))}
      </div>
    );
  }

  if (transactions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center bg-card/30 rounded-3xl border border-dashed border-border">
        <Clock className="w-12 h-12 text-muted-foreground/30 mb-4" />
        <h3 className="text-xl font-bold">Nenhum histórico encontrado</h3>
        <p className="text-muted-foreground mt-1 max-w-xs">
          Suas transações de créditos de IA aparecerão aqui conforme você utiliza os serviços.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-3xl border border-border bg-card/30">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-border bg-muted/50">
              <th className="px-6 py-4 text-xs font-black uppercase tracking-wider text-muted-foreground">Transação</th>
              <th className="px-6 py-4 text-xs font-black uppercase tracking-wider text-muted-foreground">Tipo</th>
              <th className="px-6 py-4 text-xs font-black uppercase tracking-wider text-muted-foreground">Quantidade</th>
              <th className="px-6 py-4 text-xs font-black uppercase tracking-wider text-muted-foreground">Data</th>
              <th className="px-6 py-4 text-xs font-black uppercase tracking-wider text-muted-foreground">Saldo</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">
            {transactions.map((tx) => {
              const isDebit = tx.type === 'debit';
              
              return (
                <tr key={tx.id} className="group hover:bg-muted/30 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-xl border ${
                        isDebit ? 'bg-red-500/10 border-red-500/20 text-red-500' : 'bg-green-500/10 border-green-500/20 text-green-500'
                      }`}>
                        {isDebit ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownLeft className="w-4 h-4" />}
                      </div>
                      <div>
                        <div className="font-bold text-sm">{tx.action_display}</div>
                        <div className="text-[10px] text-muted-foreground uppercase font-medium tracking-tight">ID: {tx.id.split('-')[0]}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-tighter border ${
                      isDebit 
                        ? 'bg-red-500/10 text-red-500 border-red-500/20' 
                        : 'bg-green-500/10 text-green-500 border-green-500/20'
                    }`}>
                      {isDebit ? 'Consumo' : 'Recarga'}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className={`flex items-center gap-1.5 font-black ${isDebit ? 'text-foreground' : 'text-green-500'}`}>
                      {isDebit ? '-' : '+'}
                      {tx.amount.toLocaleString()}
                      <Cpu className="w-3 h-3 opacity-50" />
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-muted-foreground">
                      {formatDistanceToNow(new Date(tx.created_at), { addSuffix: true, locale: ptBR })}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm font-bold text-muted-foreground/80">
                      {tx.balance_after.toLocaleString()}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
