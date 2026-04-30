'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import Link from 'next/link';
import { loginUser, getMe } from '@/lib/api';
import { useAuthStore } from '@/store/useAuthStore';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

const loginSchema = z.object({
  email: z.string().email({ message: "Invalid email format" }),
  password: z.string().min(1, { message: "Password is required" }),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const login = useAuthStore((state) => state.login);
  const [apiError, setApiError] = useState<string | null>(null);

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema)
  });

  const onSubmit = async (data: LoginForm) => {
    setApiError(null);
    try {
      const tokens = await loginUser(data);
      // Temporarily store token in auth store to allow getMe to work 
      // (fetchApi uses token from store)
      useAuthStore.setState({ token: tokens.access });
      
      const userData = await getMe();
      
      login({
        id: userData.id,
        email: userData.email,
        name: userData.full_name || userData.email,
        plan: userData.subscription_plan || 'Free',
        role: userData.role,
        workspace_id: userData.workspace_id
      }, tokens.access);
      
      router.push('/dashboard');
    } catch (error: any) {
      setApiError(error.message || "Invalid credentials or system error.");
    }
  };

  return (
    <div className="w-full max-w-md">
      <div className="mb-8">
        <h2 className="text-3xl font-bold font-mono text-foreground mb-2">Initialize Session</h2>
        <p className="text-gray-400 font-mono text-sm">Enter your credentials to access the system.</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {apiError && (
          <div className="bg-neon-red/10 border border-neon-red px-4 py-3 rounded text-neon-red text-sm font-mono mb-4">
            {apiError}
          </div>
        )}
        <div className="space-y-2">
          <label className="text-sm font-mono text-gray-300">Email Address</label>
          <input 
            {...register('email')}
            type="email" 
            className="w-full bg-card-bg border border-card-border rounded-md px-4 py-3 text-foreground font-mono focus:outline-none focus:border-neon-green focus:ring-1 focus:ring-neon-green transition-all"
            placeholder="admin@hackerscan.pro"
          />
          {errors.email && <p className="text-xs text-neon-red font-mono mt-1">{errors.email.message}</p>}
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-sm font-mono text-gray-300">Password</label>
            <Link href="#" className="text-xs font-mono text-neon-green hover:underline">Forgot sequence?</Link>
          </div>
          <input 
            {...register('password')}
            type="password" 
            className="w-full bg-card-bg border border-card-border rounded-md px-4 py-3 text-foreground font-mono focus:outline-none focus:border-neon-green focus:ring-1 focus:ring-neon-green transition-all"
            placeholder="••••••••"
          />
          {errors.password && <p className="text-xs text-neon-red font-mono mt-1">{errors.password.message}</p>}
        </div>

        <button 
          type="submit" 
          disabled={isSubmitting}
          className="w-full bg-neon-green text-black font-mono font-bold rounded-md px-4 py-3 hover:bg-[#00cc00] transition-colors disabled:opacity-50"
        >
          {isSubmitting ? 'Authenticating...' : 'Execute Login'}
        </button>
      </form>

      <div className="mt-8 text-center border-t border-card-border pt-6">
        <p className="text-sm text-gray-400 font-mono">
          Don't have clearance? <Link href="/register" className="text-neon-green hover:underline">Request access</Link>
        </p>
      </div>
    </div>
  );
}
