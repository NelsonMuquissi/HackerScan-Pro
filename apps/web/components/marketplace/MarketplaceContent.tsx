'use client';

import { useState, useEffect } from 'react';
import { 
  ShoppingBag, 
  Zap, 
  ShieldCheck, 
  Globe, 
  UserCheck, 
  Cpu, 
  BarChart3,
  Sparkles,
  Lock,
  ArrowRight,
  Server,
  Database,
  Cloud,
  Loader2
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';
import { listMarketplaceModules, createModuleCheckout } from '@/lib/api';
import { useParams } from 'next/navigation';

interface SecurityModule {
  id: string;
  slug: string;
  name: string;
  description: string;
  category: string;
  price_monthly: string;
  price_yearly: string;
  stripe_price_id: string;
  icon: string;
  badge: string;
  unlocked_strategies: string[];
  is_purchased: boolean;
}

const CATEGORY_ICONS: Record<string, any> = {
  'AD_AUDIT': Server,
  'K8S_SECURITY': Cloud,
  'SAP_AUDIT': Database,
  'INFRA': Cpu,
  'SERVICES': UserCheck,
  'COMPLIANCE': ShieldCheck,
};

export function MarketplaceContent() {
  const [modules, setModules] = useState<SecurityModule[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [purchasingId, setPurchasingId] = useState<string | null>(null);
  const params = useParams();
  const workspaceId = params.workspaceId as string;

  useEffect(() => {
    fetchModules();
  }, [workspaceId]);

  const fetchModules = async () => {
    try {
      const data = await listMarketplaceModules(workspaceId);
      // Handle both plain arrays and paginated responses { results: [...] }
      let list: any[] = [];
      if (Array.isArray(data)) {
        list = data;
      } else if (data && typeof data === 'object' && 'results' in data) {
        list = (data as any).results;
      }
      setModules(list);
    } catch (error) {
      console.error('Failed to fetch modules:', error);
      alert('Failed to load marketplace modules');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePurchase = async (module: SecurityModule) => {
    if (module.is_purchased) {
      alert('You already own this module!');
      return;
    }

    try {
      setPurchasingId(module.id);
      const response = await createModuleCheckout(module.slug, workspaceId, {
        success_url: window.location.href + '?success=true',
        cancel_url: window.location.href + '?canceled=true',
      });
      
      if (response.checkout_url) {
        window.location.href = response.checkout_url;
      }
    } catch (error: any) {
      console.error('Purchase failed:', error);
      alert(error.response?.data?.detail || 'Failed to initiate purchase');
    } finally {
      setPurchasingId(null);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
        <Loader2 className="w-10 h-10 text-neon-green animate-spin" />
        <p className="text-gray-500 font-mono text-xs uppercase tracking-widest animate-pulse">
          Synchronizing Marketplace...
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-12 pb-20">
      {/* Hero Section */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#0c0c0c] to-[#151515] border border-white/5 p-12 text-center">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-neon-green/5 blur-[120px] rounded-full" />
        <motion.div
           initial={{ opacity: 0, y: 20 }}
           animate={{ opacity: 1, y: 0 }}
           className="relative z-10 space-y-4"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-neon-green/10 border border-neon-green/20 text-neon-green text-[10px] font-bold font-mono tracking-widest uppercase">
            <Sparkles className="w-3 h-3" />
            Security Marketplace
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight">
            MODULAR <span className="text-neon-green italic">DEFENSE</span>
          </h1>
          <p className="text-gray-400 max-w-xl mx-auto text-sm leading-relaxed font-mono uppercase tracking-tighter">
            Extend your infrastructure's analytical surface with specialized security primitives and tactical modules.
          </p>
        </motion.div>
      </div>

      {/* Grid */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        <AnimatePresence>
          {modules.map((module, i) => {
            const Icon = CATEGORY_ICONS[module.category] || Cpu;
            const isPurchasing = purchasingId === module.id;

            return (
              <motion.div
                key={module.id}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.1 }}
                className={cn(
                  "group relative bg-card-bg border rounded-2xl p-6 flex flex-col justify-between transition-all hover:border-white/20 hover:bg-[#121212]",
                  module.is_purchased ? "border-neon-green/20 bg-neon-green/[0.02]" : "border-card-border"
                )}
              >
                {module.badge && (
                  <div className="absolute -top-3 left-6 px-2 py-0.5 bg-neon-green text-black text-[9px] font-bold font-mono rounded-sm">
                    {module.badge.toUpperCase()}
                  </div>
                )}
                
                <div className="space-y-4">
                  <div className={cn(
                    "w-12 h-12 rounded-xl bg-black border border-white/5 flex items-center justify-center transition-transform group-hover:scale-110",
                    module.is_purchased ? "text-neon-green" : "text-gray-400"
                  )}>
                    <Icon className="w-6 h-6" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                       <span className="text-[10px] font-bold text-gray-500 font-mono tracking-widest uppercase">{module.category}</span>
                       {module.is_purchased && (
                         <span className="px-1.5 py-0.5 rounded text-[8px] font-bold bg-neon-green/10 text-neon-green border border-neon-green/20 font-mono uppercase">Unlocked</span>
                       )}
                    </div>
                    <h3 className="text-lg font-bold text-foreground mt-1">{module.name}</h3>
                    <p className="text-xs text-gray-500 mt-2 leading-relaxed">{module.description}</p>
                  </div>
                </div>

                <div className="mt-8 space-y-4">
                  {!module.is_purchased ? (
                    <>
                      <div className="flex items-baseline gap-1">
                        <span className="text-2xl font-bold text-foreground">${module.price_monthly}</span>
                        <span className="text-[10px] text-gray-500 font-mono font-bold">/mo</span>
                      </div>
                      <button 
                        onClick={() => handlePurchase(module)}
                        disabled={isPurchasing}
                        className={cn(
                          "w-full py-3 rounded-lg font-bold text-xs flex items-center justify-center gap-2 transition-all",
                          "bg-neon-green text-black hover:opacity-90 disabled:opacity-50"
                        )}
                      >
                        {isPurchasing ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <>
                            ACTIVATE MODULE
                            <ArrowRight className="w-3 h-3" />
                          </>
                        )}
                      </button>
                    </>
                  ) : (
                    <button 
                       className="w-full py-3 rounded-lg font-bold text-[10px] flex items-center justify-center gap-2 border border-white/5 bg-white/5 text-gray-400 font-mono uppercase tracking-widest"
                       disabled
                    >
                      ACTIVE LIFETIME
                    </button>
                  )}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {/* Placeholder for "Coming Soon" */}
        <div className="border border-dashed border-white/5 rounded-2xl p-6 flex flex-col items-center justify-center text-center gap-4 group hover:border-white/10 transition-colors">
           <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center text-gray-600">
             <Zap className="w-6 h-6" />
           </div>
           <div>
             <h4 className="text-sm font-bold text-gray-500 uppercase tracking-widest">More Modules Coming</h4>
             <p className="text-[10px] text-gray-700 mt-1 font-mono uppercase tracking-tighter">New tactical capabilities added every week.</p>
           </div>
        </div>
      </div>

      {/* Partner Banner */}
      <div className="bg-[#0a0a0a] border border-card-border rounded-2xl p-8 flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-blue-500/10 flex items-center justify-center">
            <BarChart3 className="w-6 h-6 text-blue-400" />
          </div>
          <div>
            <h4 className="font-bold">Partner Ecosystem</h4>
            <p className="text-xs text-gray-500 font-mono italic">Looking to build your own security extension?</p>
          </div>
        </div>
        <button className="flex items-center gap-2 text-[10px] font-bold text-gray-500 hover:text-neon-green transition-colors font-mono tracking-widest uppercase">
          <Lock className="w-3 h-3" />
          Marketplace SDK
        </button>
      </div>
    </div>
  );
}
