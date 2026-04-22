'use client';

import { useEffect, useState } from 'react';
import { getPlans, createCheckoutSession, Plan } from '@/lib/api';
import { useAuthStore } from '@/store/useAuthStore';
import { Check } from 'lucide-react';

export default function PlansPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [billingCycle, setBillingCycle] = useState<'MONTHLY' | 'YEARLY'>('MONTHLY');

  useEffect(() => {
    async function loadPlans() {
      try {
        const data = await getPlans();
        setPlans(data);
      } catch (error) {
        console.error('Failed to load plans:', error);
      } finally {
        setLoading(false);
      }
    }
    loadPlans();
  }, []);

  const handleSubscribe = async (planId: string) => {
    try {
      const { checkout_url } = await createCheckoutSession({
        plan_id: planId,
        billing_cycle: billingCycle,
        success_url: `${window.location.origin}/billing/success`,
        cancel_url: `${window.location.origin}/billing/plans`,
      });
      window.location.href = checkout_url;
    } catch (error) {
      console.error('Failed to start checkout:', error);
      alert('Error starting checkout. Please try again.');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="text-center">
        <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl">
          Choose your Plan
        </h1>
        <p className="mt-4 text-xl text-gray-400">
          Scale your security scanning with our premium tiers.
        </p>

        {/* Billing Toggle */}
        <div className="mt-8 flex justify-center">
          <div className="relative bg-secondary rounded-lg p-0.5 flex">
            <button
              onClick={() => setBillingCycle('MONTHLY')}
              className={`relative py-2 px-6 rounded-md text-sm font-medium transition-all ${
                billingCycle === 'MONTHLY' ? 'bg-background text-white shadow' : 'text-gray-400 hover:text-white'
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setBillingCycle('YEARLY')}
              className={`relative py-2 px-6 rounded-md text-sm font-medium transition-all ${
                billingCycle === 'YEARLY' ? 'bg-background text-white shadow' : 'text-gray-400 hover:text-white'
              }`}
            >
              Yearly (Save 20%)
            </button>
          </div>
        </div>
      </div>

      <div className="mt-16 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {plans.map((plan) => (
          <div
            key={plan.id}
            className={`relative p-8 bg-secondary border border-gray-800 rounded-2xl flex flex-col transition-all hover:border-primary/50 ${
              plan.name === 'Pro' ? 'ring-2 ring-primary border-primary' : ''
            }`}
          >
            {plan.name === 'Pro' && (
              <span className="absolute top-0 right-0 -translate-y-1/2 translate-x-1 px-4 py-1.5 bg-primary text-background text-xs font-bold rounded-full uppercase tracking-wider">
                Most Popular
              </span>
            )}

            <div className="flex-1">
              <h3 className="text-2xl font-bold text-white">{plan.name}</h3>
              <p className="mt-4 text-gray-400 text-sm leading-relaxed">{plan.description}</p>
              
              <div className="mt-6 flex items-baseline">
                <span className="text-4xl font-extrabold text-white">
                  ${billingCycle === 'MONTHLY' ? plan.price_monthly : plan.price_yearly}
                </span>
                <span className="ml-1 text-gray-500">/{billingCycle.toLowerCase().slice(0, -2)}</span>
              </div>

              <ul className="mt-8 space-y-4">
                {Object.entries(plan.features).map(([key, value]) => (
                  <li key={key} className="flex items-start">
                    <Check className="h-5 w-5 text-green-500 shrink-0" />
                    <span className="ml-3 text-sm text-gray-300 capitalize">
                      {key.replace(/_/g, ' ')}: <span className="font-semibold text-white">{value as string}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            <button
              onClick={() => handleSubscribe(plan.id)}
              className={`mt-10 block w-full py-3 px-6 rounded-xl text-center font-bold transition-all ${
                plan.name === 'Free' 
                  ? 'bg-gray-800 text-white cursor-not-allowed' 
                  : 'bg-primary text-background hover:opacity-90 active:scale-[0.98]'
              }`}
              disabled={plan.name === 'Free'}
            >
              {plan.name === 'Free' ? 'Default Plan' : 'Subscribe Now'}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
