'use client';

import { useEffect } from 'react';
import { useAuthStore } from '@/store/useAuthStore';

export function StoreHydrator() {
  useEffect(() => {
    useAuthStore.persist.rehydrate();
  }, []);

  return null;
}
