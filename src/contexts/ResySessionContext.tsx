import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react";
import { setGlobalSessionExpiredHandler } from "./ResySessionContext.utils";

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

  // Set up global handler for non-React code
  useEffect(() => {
    setGlobalSessionExpiredHandler(showSessionExpiredModal);
  }, [showSessionExpiredModal]);

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

// eslint-disable-next-line react-refresh/only-export-components
export function useResySession() {
  const context = useContext(ResySessionContext);
  if (!context) {
    throw new Error("useResySession must be used within a ResySessionProvider");
  }
  return context;
}