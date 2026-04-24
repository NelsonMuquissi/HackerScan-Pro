'use client';

import React, { useEffect, useState } from 'react';
import { 
  Cpu, 
  Zap, 
  Check, 
  ShoppingCart, 
  Loader2,
  Sparkles,
  ArrowRight
} from 'lucide-react';
import { listAIPackages, createAICheckoutSession } from '@/lib/api';
import { motion } from 'framer-motion';
import { toast } from 'sonner';

interface Package {
  id: string;
  name: string;
  credits: number;
  price: string;
  description: string;
}

export const CreditPackagesList: React.FC<{ workspaceId: string }> = ({ workspaceId }) => {
  const [packages, setPackages] = useState<Package[]>([]);
  const [loading, setLoading] = useState(true);
  const [buyingId, setBuyingId] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await listAIPackages();
        const pkgList = Array.isArray(data) ? data : (data as any)?.results ?? [];
        setPackages(pkgList);
      } catch (err) {
        toast.error('Erro ao carregar pacotes de créditos');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const handleBuy = async (pkgId: string) => {
    try {
      setBuyingId(pkgId);
      const { checkout_url } = await createAICheckoutSession(pkgId, workspaceId);
      window.location.href = checkout_url;
    } catch (err: any) {
      toast.error(err.message || 'Erro ao iniciar checkout');
      setBuyingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-4">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <p className="text-muted-foreground animate-pulse">Carregando ofertas de créditos...</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
      {packages.map((pkg, idx) => {
        const isBestSeller = pkg.credits === 10000; // Power package
        
        return (
          <motion.div
            key={pkg.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1 }}
            className={`relative flex flex-col p-6 rounded-3xl border bg-card/50 transition-all hover:shadow-xl hover:-translate-y-1 ${
              isBestSeller 
                ? 'border-primary ring-1 ring-primary/50 shadow-lg shadow-primary/10' 
                : 'border-border hover:border-primary/50'
            }`}
          >
            {isBestSeller && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary text-primary-foreground text-[10px] font-black uppercase tracking-tighter px-3 py-1 rounded-full flex items-center gap-1 shadow-lg">
                <Sparkles className="w-3 h-3" />
                Mais Popular
              </div>
            )}

            <div className="flex items-center gap-3 mb-4">
              <div className={`p-2 rounded-xl ${isBestSeller ? 'bg-primary/20 text-primary' : 'bg-muted text-foreground'}`}>
                <Cpu className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-lg">{pkg.name}</h3>
            </div>

            <div className="mb-4">
              <div className="flex items-baseline gap-1">
                <span className="text-3xl font-black">{pkg.credits.toLocaleString()}</span>
                <span className="text-muted-foreground text-sm font-medium">créditos</span>
              </div>
              <p className="text-2xl font-bold mt-2 text-primary">
                ${pkg.price}
              </p>
            </div>

            <div className="space-y-3 mb-8 flex-grow">
              <div className="flex items-start gap-2 text-xs text-muted-foreground">
                <Check className="w-3.5 h-3.5 text-primary shrink-0 mt-0.5" />
                <span>Sem expiração</span>
              </div>
              <div className="flex items-start gap-2 text-xs text-muted-foreground">
                <Check className="w-3.5 h-3.5 text-primary shrink-0 mt-0.5" />
                <span>Claude 3.5 Sonnet & Gemini Flash</span>
              </div>
              <div className="flex items-start gap-2 text-xs text-muted-foreground">
                <Check className="w-3.5 h-3.5 text-primary shrink-0 mt-0.5" />
                <span>Explicações, Remediação e Análise</span>
              </div>
            </div>

            <button
              onClick={() => handleBuy(pkg.id)}
              disabled={buyingId !== null}
              className={`w-full py-3 rounded-2xl font-bold flex items-center justify-center gap-2 transition-all ${
                isBestSeller
                  ? 'bg-primary text-primary-foreground hover:opacity-90 shadow-lg shadow-primary/20'
                  : 'bg-muted text-foreground hover:bg-muted/80'
              }`}
            >
              {buyingId === pkg.id ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  Comprar Agora
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </motion.div>
        );
      })}
    </div>
  );
};
