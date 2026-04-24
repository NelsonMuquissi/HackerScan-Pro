import { useState, useEffect, useCallback } from 'react';
import { getAIWallet, listAITransactions, listAIAchievements } from '@/lib/api';
import { useAuthStore } from '@/store/useAuthStore';

export interface AIWallet {
  id: string;
  workspace: string;
  balance_total: number;
  balance_subscription: number;
  balance_purchased: number;
  balance_bonus: number;
  is_low_balance: boolean;
  can_use_express: boolean;
}

export function useAICredits(workspaceId?: string) {
  const [wallet, setWallet] = useState<AIWallet | null>(null);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [achievements, setAchievements] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshCredits = useCallback(async () => {
    if (!workspaceId) {
      setLoading(false);
      return;
    }
    
    try {
      setLoading(true);
      const data = await getAIWallet(workspaceId);
      setWallet(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar créditos');
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  const fetchHistory = useCallback(async () => {
    if (!workspaceId) return;
    try {
      const data = await listAITransactions(workspaceId);
      // Handle paginated response if applicable
      setTransactions(Array.isArray(data) ? data : (data as any).results || []);
    } catch (err) {
      console.error('Erro ao carregar histórico de transações', err);
    }
  }, [workspaceId]);

  const fetchAchievements = useCallback(async () => {
    if (!workspaceId) return;
    try {
      const data = await listAIAchievements(workspaceId);
      setAchievements(data);
    } catch (err) {
      console.error('Erro ao carregar conquistas', err);
    }
  }, [workspaceId]);

  useEffect(() => {
    if (workspaceId) {
      refreshCredits();
      fetchHistory();
      fetchAchievements();
    }
  }, [workspaceId, refreshCredits, fetchHistory, fetchAchievements]);

  return {
    wallet,
    transactions,
    achievements,
    loading,
    error,
    refreshCredits,
    fetchHistory,
    fetchAchievements
  };
}
