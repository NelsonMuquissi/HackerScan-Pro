'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/useAuthStore';
import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { user, isAuthenticated } = useAuthStore();
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const unsub = useAuthStore.persist.onFinishHydration(() => {
      setHydrated(true);
    });
    if (useAuthStore.persist.hasHydrated()) {
      setHydrated(true);
    }
    return unsub;
  }, []);

  useEffect(() => {
    if (hydrated) {
      if (!isAuthenticated) {
        router.replace('/login');
      } else if (user?.role !== 'superadmin') {
        router.replace('/dashboard');
      }
    }
  }, [hydrated, isAuthenticated, user, router]);

  if (!hydrated || !isAuthenticated || user?.role !== 'superadmin') {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-background">
        <div className="text-neon-green font-mono text-sm animate-pulse">
          Verifying administrative clearance...
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
