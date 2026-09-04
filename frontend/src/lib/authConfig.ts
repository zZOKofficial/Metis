/**
 * Firebase config, with no Firebase import.
 *
 * Kept separate from `lib/firebase.ts` so that modules which only need to ask
 * "is auth configured at all?" -- notably the shared API client -- can do so
 * without pulling the Firebase SDK into their bundle. The public storefront
 * imports the API client, and shoppers should not download an auth SDK they
 * will never use.
 *
 * NEXT_PUBLIC_* values are inlined at build time.
 */
export const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
};

export const authEnabled = Boolean(
  firebaseConfig.apiKey && firebaseConfig.authDomain && firebaseConfig.projectId
);
