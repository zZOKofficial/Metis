'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import {
  User,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  sendPasswordResetEmail,
  signOut as firebaseSignOut,
} from 'firebase/auth';
import { getFirebaseAuth, authEnabled } from '@/lib/firebase';

interface AuthContextType {
  user: User | null;
  /** True until the initial auth state has been resolved. */
  loading: boolean;
  /** False when the app is not configured for auth — everything stays open. */
  enabled: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  // With auth disabled there is nothing to wait for, so never start in a
  // loading state — otherwise a local install would hang on a spinner.
  const [loading, setLoading] = useState(authEnabled);

  useEffect(() => {
    const auth = getFirebaseAuth();
    if (!auth) return;
    return onAuthStateChanged(auth, (next) => {
      setUser(next);
      setLoading(false);
    });
  }, []);

  const requireAuth = () => {
    const auth = getFirebaseAuth();
    if (!auth) throw new Error('Authentication is not configured for this deployment.');
    return auth;
  };

  const value: AuthContextType = {
    user,
    loading,
    enabled: authEnabled,
    signIn: async (email, password) => {
      await signInWithEmailAndPassword(requireAuth(), email, password);
    },
    signUp: async (email, password) => {
      await createUserWithEmailAndPassword(requireAuth(), email, password);
    },
    resetPassword: async (email) => {
      await sendPasswordResetEmail(requireAuth(), email);
    },
    signOut: async () => {
      await firebaseSignOut(requireAuth());
    },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
