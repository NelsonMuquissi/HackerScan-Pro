import { useState, useCallback } from 'react';
import type { ConfirmVariant } from '@/components/ui/ConfirmModal';

interface ConfirmOptions {
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: ConfirmVariant;
}

interface ConfirmState extends ConfirmOptions {
  open: boolean;
  resolve: ((value: boolean) => void) | null;
}

/**
 * useConfirm — replaces window.confirm() with a beautiful modal.
 *
 * Usage:
 *   const { confirm, ConfirmUI } = useConfirm();
 *   // In JSX: {ConfirmUI}
 *   // To trigger: const ok = await confirm({ title: '...', description: '...' });
 */
export function useConfirm() {
  const [state, setState] = useState<ConfirmState>({
    open: false,
    title: '',
    description: '',
    resolve: null,
  });

  const confirm = useCallback((options: ConfirmOptions): Promise<boolean> => {
    return new Promise((resolve) => {
      setState({
        open: true,
        resolve,
        ...options,
      });
    });
  }, []);

  const handleConfirm = useCallback(() => {
    state.resolve?.(true);
    setState((s) => ({ ...s, open: false, resolve: null }));
  }, [state]);

  const handleCancel = useCallback(() => {
    state.resolve?.(false);
    setState((s) => ({ ...s, open: false, resolve: null }));
  }, [state]);

  return { confirm, state, handleConfirm, handleCancel };
}
