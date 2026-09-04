import { initializeApp, getApps, getApp, FirebaseOptions } from 'firebase/app';
import { getAuth, Auth } from 'firebase/auth';
import { firebaseConfig, authEnabled } from '@/lib/authConfig';

/**
 * Firebase client initialisation.
 *
 * Config comes from NEXT_PUBLIC_FIREBASE_* env vars, which are inlined at build
 * time. When they are absent — the normal case for local development, where
 * METIS_AUTH_ENABLED is off on the backend — `auth` is null and the app runs
 * unauthenticated rather than crashing on a missing key.
 */
const config: FirebaseOptions = firebaseConfig;

export { authEnabled };

let cachedAuth: Auth | null = null;

export function getFirebaseAuth(): Auth | null {
  if (!authEnabled) return null;
  if (!cachedAuth) {
    const app = getApps().length ? getApp() : initializeApp(config);
    cachedAuth = getAuth(app);
  }
  return cachedAuth;
}

/**
 * The current user's ID token, or null when signed out or auth is off.
 *
 * Firebase ID tokens expire after an hour; getIdToken() serves a cached token
 * and only performs a network refresh when it is close to expiry, so calling
 * this on every request is both correct and cheap.
 */
export async function getIdToken(): Promise<string | null> {
  const auth = getFirebaseAuth();
  if (!auth?.currentUser) return null;
  try {
    return await auth.currentUser.getIdToken();
  } catch {
    return null;
  }
}
