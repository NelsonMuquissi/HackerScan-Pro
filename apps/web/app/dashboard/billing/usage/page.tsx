'use client';

import { useEffect, useState } from 'react';
import { getUsage, getSubscription } from '@/lib/api';
import { 
  BarChart3, 
  ShieldCheck, 
  Cpu,
  AlertTriangle
} from 'lucide-react';

interface UsageData {
  scans_count: number;
  api_calls_count: number;
  findings_count: number;
  period_start: string;
  period_end: string;
}

export default function UsagePage() {
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [subscription, setSubscription] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [usageData, subData] = await Promise.all([
          getUsage(),
          getSubscription()
        ]);
        setUsage(usageData);
        setSubscription(subData);
      } catch (error) {
        console.error('Failed to load usage data:', error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  const planName = subscription?.plan?.name || 'Free';
  const limits = subscription?.plan?.limits || {
    scans_per_month: 5,
    targets: 3,
    api_calls_per_month: 100
  };

  const usageMetrics = [
    {
      name: 'Monthly Scans',
      current: usage?.scans_count || 0,
      limit: limits.scans_per_month,
      icon: BarChart3,
      color: 'bg-blue-500',
    },
    {
      name: 'Targets Inventory',
      current: usage?.api_calls_count || 0, // In this context, we track target creation attempts
      limit: limits.targets,
      icon: ShieldCheck,
      color: 'bg-green-500',
    },
    {
      name: 'Nexus API Operations',
      current: usage?.api_calls_count || 0,
      limit: limits.api_calls_per_month,
      icon: Cpu,
      color: 'bg-purple-500',
    },
  ];

  return (
    <div className="max-w-4xl mx-auto py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Resource Usage</h1>
        <p className="text-gray-400 mt-2">
          Monitoring your {planName} plan quotas for the current period.
        </p>
      </div>

      <div className="grid gap-6">
        {usageMetrics.map((metric) => {
          const percentage = Math.min((metric.current / metric.limit) * 100, 100);
          const isOverLimit = metric.current >= metric.limit;

          return (
            <div key={metric.name} className="bg-secondary border border-gray-800 rounded-xl p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <div className={`p-2 rounded-lg ${metric.color} bg-opacity-10 text-white`}>
                    <metric.icon className="h-6 w-6" />
                  </div>
                  <h3 className="font-semibold text-lg text-white">{metric.name}</h3>
                </div>
                <div className="text-right">
                  <span className={`text-sm font-bold ${isOverLimit ? 'text-red-400' : 'text-gray-300'}`}>
                    {metric.current} / {metric.limit}
                  </span>
                </div>
              </div>

              <div className="relative h-4 w-full bg-gray-800 rounded-full overflow-hidden">
                <div 
                  className={`absolute h-full transition-all duration-500 rounded-full ${isOverLimit ? 'bg-red-500' : metric.color}`}
                  style={{ width: `${percentage}%` }}
                />
              </div>

              {isOverLimit && (
                <div className="mt-3 flex items-center text-xs text-red-400">
                  <AlertTriangle className="h-4 w-4 mr-1" />
                  Limit reached. Upgrade to increase capacity.
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-10 p-6 bg-primary bg-opacity-5 border border-primary border-opacity-20 rounded-xl flex items-center justify-between">
        <div>
          <h4 className="text-white font-semibold">Need more resources?</h4>
          <p className="text-sm text-gray-400 mt-1">
            Upgrade your plan for unlimited scans and advanced reporting.
          </p>
        </div>
        <a 
          href="/billing/plans" 
          className="px-6 py-2 bg-primary text-background font-bold rounded-lg hover:opacity-90 transition-all"
        >
          View Plans
        </a>
      </div>
    </div>
  );
}
