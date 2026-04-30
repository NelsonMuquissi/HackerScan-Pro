import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  email: string;
  name: string;
  plan?: string;
  role: string;
  workspace_id?: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  workspaceId: string | null;
  isAuthenticated: boolean;
  login: (user: User, token: string, workspaceId?: string) => void;
  logout: () => void;
  updateUser: (user: Partial<User>) => void;
  setWorkspaceId: (id: string | null) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      workspaceId: null,
      isAuthenticated: false,
      login: (user, token, workspaceId) => set({ 
        user, 
        token, 
        workspaceId: workspaceId || user.workspace_id || null,
        isAuthenticated: true 
      }),
      logout: () => {
        set({ user: null, token: null, workspaceId: null, isAuthenticated: false });
      },
      updateUser: (userData) => set((state) => ({
        user: state.user ? { ...state.user, ...userData } : null
      })),
      setWorkspaceId: (id) => set({ workspaceId: id }),
    }),
    {
      name: 'hacker-scan-auth',
      skipHydration: true,
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        workspaceId: state.workspaceId,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
