import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

interface ResySessionContextType {
  isSessionExpired: boolean;
  showSessionExpiredModal: () => void;
  hideSessionExpiredModal: () => void;
  resetSession: () => void;
}

const ResySessionContext = createContext<ResySessionContextType | null>(null);

export function ResySessionProvider({ children }: { children: ReactNode }) {
  const [isSessionExpired, setIsSessionExpired] = useState(false);

  const showSessionExpiredModal = useCallback(() => {
    setIsSessionExpired(true);
  }, []);

  const hideSessionExpiredModal = useCallback(() => {
    setIsSessionExpired(false);
  }, []);

  const resetSession = useCallback(() => {
    setIsSessionExpired(false);
  }, []);

  return (
    <ResySessionContext.Provider
      value={{
        isSessionExpired,
        showSessionExpiredModal,
        hideSessionExpiredModal,
        resetSession,
      }}
    >
      {children}
    </ResySessionContext.Provider>
  );
}

export function useResySession() {
  const context = useContext(ResySessionContext);
  if (!context) {
    throw new Error("useResySession must be used within a ResySessionProvider");
  }
  return context;
}

// Global reference for use in non-React code (like api.ts)
let globalShowSessionExpiredModal: (() => void) | null = null;

export function setGlobalSessionExpiredHandler(handler: () => void) {
  globalShowSessionExpiredModal = handler;
}

export function triggerSessionExpiredModal() {
  if (globalShowSessionExpiredModal) {
    globalShowSessionExpiredModal();
  }
}