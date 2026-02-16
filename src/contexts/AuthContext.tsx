import {
  createContext,
  useContext,
  useEffect,
  useRef,
  type ReactNode,
} from "react";
import * as Sentry from "@sentry/react";
import type { User } from "firebase/auth";
import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
  onAuthStateChanged,
  updateProfile,
} from "firebase/auth";
import { useAtomValue, useSetAtom } from "jotai";
import { auth, googleProvider } from "@/services/firebase";
import { getMe } from "@/lib/api";
import {
  userAtom,
  accessTokenAtom,
  isAuthenticatedAtom,
  isAuthLoadingAtom,
  meAtom,
  authErrorAtom,
  clearAuthStateAtom,
  clearAuthErrorAtom,
} from "@/atoms/authAtoms";

interface AuthContextType {
  currentUser: User | null;
  loading: boolean;
  signup: (
    email: string,
    password: string,
    displayName: string
  ) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  logout: () => Promise<void>;
  refreshMe: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    // Provide a more helpful error message with debugging information
    const error = new Error(
      "useAuth must be used within an AuthProvider. " +
      "This error can occur if: 1) The component is rendered outside the AuthProvider, " +
      "2) During hot module reload, or 3) The AuthProvider hasn't mounted yet."
    );
    Sentry.captureException(error);
    throw error;
  }
  return context;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const setUser = useSetAtom(userAtom);
  const setAccessToken = useSetAtom(accessTokenAtom);
  const setIsAuthenticated = useSetAtom(isAuthenticatedAtom);
  const setMe = useSetAtom(meAtom);
  const setLoading = useSetAtom(isAuthLoadingAtom);
  const setError = useSetAtom(authErrorAtom);
  const clearAuthState = useSetAtom(clearAuthStateAtom);
  const clearAuthError = useSetAtom(clearAuthErrorAtom);

  // Track if we're handling a 401 to prevent redirect loops
  const isHandling401Ref = useRef(false);

  // Watch Firebase Auth state and call /me when user exists
  useEffect(() => {
    setLoading(true);
    clearAuthError();

    const unsubscribe = onAuthStateChanged(auth, async (user: User | null) => {
      if (user) {
        try {
          const token = await user.getIdToken();
          setUser(user);
          setAccessToken(token);
          setIsAuthenticated(true);
          setError(null);

          // Set Sentry user context
          Sentry.setUser({
            id: user.uid,
            email: user.email || undefined,
            username: user.displayName || undefined,
          });

          // Call /me endpoint to get session data
          try {
            const meData = await getMe(user.uid);
            if (meData.success) {
              setMe(meData);
              setError(null);
            } else {
              // If /me returns an error, don't clear auth state
              // Just log it and continue
              console.error("[Auth] /me endpoint returned error:", meData.error);
            }
          } catch (meError) {
            // Check if it's a 401 (unauthorized)
            const axiosError = meError as { response?: { status?: number } };
            const status = axiosError.response?.status;

            if (status === 401) {
              if (!isHandling401Ref.current) {
                isHandling401Ref.current = true;
                // 401 means the token is invalid - sign out
                clearAuthState();
                await signOut(auth);
                Sentry.setUser(null);
                setTimeout(() => {
                  isHandling401Ref.current = false;
                }, 1000);
              }
              return;
            }

            // Other errors - log but don't clear auth state
            console.error("[Auth] Error fetching /me:", meError);
            Sentry.captureException(meError);
          }

          setLoading(false);
        } catch (error) {
          console.error("Failed to get user token:", error);
          Sentry.captureException(error);
          clearAuthState();
          setLoading(false);
        }
      } else {
        // User is signed out
        clearAuthState();
        Sentry.setUser(null);
        setLoading(false);
      }
    });

    return unsubscribe;
  }, [
    setUser,
    setAccessToken,
    setIsAuthenticated,
    setError,
    clearAuthState,
    clearAuthError,
    setLoading,
    setMe,
  ]);

  // Get current state from atoms
  const currentUser = useAtomValue(userAtom);
  const loading = useAtomValue(isAuthLoadingAtom);

  async function signup(email: string, password: string, displayName: string) {
    const userCredential = await createUserWithEmailAndPassword(
      auth,
      email,
      password
    );
    // Update display name
    if (userCredential.user) {
      await updateProfile(userCredential.user, { displayName });
    }
  }

  async function login(email: string, password: string) {
    await signInWithEmailAndPassword(auth, email, password);
  }

  async function loginWithGoogle() {
    await signInWithPopup(auth, googleProvider);
  }

  async function logout() {
    await signOut(auth);
  }

  async function refreshMe() {
    if (!currentUser) {
      return;
    }

    try {
      const meData = await getMe(currentUser.uid);
      if (meData.success) {
        setMe(meData);
        setError(null);
      }
    } catch (error) {
      console.error("[Auth] Error refreshing /me:", error);
      Sentry.captureException(error);
    }
  }

  const value: AuthContextType = {
    currentUser,
    loading,
    signup,
    login,
    loginWithGoogle,
    logout,
    refreshMe,
  };

  return (
    <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  );
}
