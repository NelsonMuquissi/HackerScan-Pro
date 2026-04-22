'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import Link from 'next/link';
import { registerUser, loginUser, getMe } from '@/lib/api';
import { useAuthStore } from '@/store/useAuthStore';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

const registerSchema = z.object({
  name: z.string().min(2, { message: "Name must be at least 2 characters" }),
  email: z.string().email({ message: "Invalid email format" }),
  password: z.string()
    .min(12, { message: "Password must be at least 12 characters" })
    .regex(/[A-Z]/, { message: "Must include 1 uppercase letter" })
    .regex(/[0-9]/, { message: "Must include 1 number" })
    .regex(/[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/, { message: "Must include 1 special character" }),
  confirmPassword: z.string()
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"]
});

type RegisterForm = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();
  const login = useAuthStore((state) => state.login);
  const [apiError, setApiError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema)
  });

  const onSubmit = async (data: RegisterForm) => {
    setApiError(null);
    try {
      await registerUser({
        email: data.email,
        password: data.password,
        full_name: data.name,
      });
      setSuccess(true);

      // Auto-login after registration (works in dev where email is auto-verified)
      try {
        const tokens = await loginUser({ email: data.email, password: data.password });
        useAuthStore.setState({ token: tokens.access });
        const userData = await getMe();
        login({
          id: userData.id,
          email: userData.email,
          name: userData.full_name || userData.email,
          plan: userData.subscription_plan || 'Free'
        }, tokens.access);
        router.push('/dashboard');
      } catch {
        // If auto-login fails (e.g. email not verified in prod), redirect to login
        setTimeout(() => { router.push('/login'); }, 2000);
      }
    } catch (error: any) {
      setApiError(error.message || "An unexpected error occurred during registration.");
    }
  };

  return (
    <div className="w-full max-w-md">
      <div className="mb-8">
        <h2 className="text-3xl font-bold font-mono text-foreground mb-2">Request Access</h2>
        <p className="text-gray-400 font-mono text-sm">Create a new operator account.</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {apiError && (
          <div className="bg-neon-red/10 border border-neon-red px-4 py-3 rounded text-neon-red text-sm font-mono mb-4">
            {apiError}
          </div>
        )}
        
        {success && (
          <div className="bg-neon-green/10 border border-neon-green px-4 py-3 rounded text-neon-green text-sm font-mono mb-4">
            Identity generated successfully. Redirecting to login...
          </div>
        )}

        <div className="space-y-2">
          <label className="text-sm font-mono text-gray-300">Operator Designation</label>
          <input 
            {...register('name')}
            type="text" 
            className="w-full bg-card-bg border border-card-border rounded-md px-4 py-3 text-foreground font-mono focus:outline-none focus:border-neon-green focus:ring-1 focus:ring-neon-green transition-all"
            placeholder="John Doe"
          />
          {errors.name && <p className="text-xs text-neon-red font-mono mt-1">{errors.name.message}</p>}
        </div>

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
          <label className="text-sm font-mono text-gray-300">Password</label>
          <input 
            {...register('password')}
            type="password" 
            className="w-full bg-card-bg border border-card-border rounded-md px-4 py-3 text-foreground font-mono focus:outline-none focus:border-neon-green focus:ring-1 focus:ring-neon-green transition-all"
            placeholder="••••••••"
          />
          {errors.password && <p className="text-xs text-neon-red font-mono mt-1">{errors.password.message}</p>}
        </div>

        <div className="space-y-2">
          <label className="text-sm font-mono text-gray-300">Confirm Password</label>
          <input 
            {...register('confirmPassword')}
            type="password" 
            className="w-full bg-card-bg border border-card-border rounded-md px-4 py-3 text-foreground font-mono focus:outline-none focus:border-neon-green focus:ring-1 focus:ring-neon-green transition-all"
            placeholder="••••••••"
          />
          {errors.confirmPassword && <p className="text-xs text-neon-red font-mono mt-1">{errors.confirmPassword.message}</p>}
        </div>

        <button 
          type="submit" 
          disabled={isSubmitting}
          className="w-full bg-neon-green text-black font-mono font-bold rounded-md px-4 py-3 mt-4 hover:bg-[#00cc00] transition-colors disabled:opacity-50"
        >
          {isSubmitting ? 'Processing...' : 'Generate Identity'}
        </button>
      </form>

      <div className="mt-8 text-center border-t border-card-border pt-6">
        <p className="text-sm text-gray-400 font-mono">
          Already have clearance? <Link href="/login" className="text-neon-green hover:underline">Execute login</Link>
        </p>
      </div>
    </div>
  );
}
