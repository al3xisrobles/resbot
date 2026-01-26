import { useNavigate } from "react-router-dom";
import { useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { AlertCircle } from "lucide-react";
import {
  useResySession,
  setGlobalSessionExpiredHandler,
} from "@/contexts/ResySessionContext";

export function ResySessionExpiredModal() {
  const navigate = useNavigate();
  const { isSessionExpired, hideSessionExpiredModal, showSessionExpiredModal } =
    useResySession();

  // Register the global handler so api.ts can trigger the modal
  useEffect(() => {
    setGlobalSessionExpiredHandler(showSessionExpiredModal);
  }, [showSessionExpiredModal]);

  const handleReconnect = () => {
    hideSessionExpiredModal();
    navigate("/onboarding");
  };

  const handleDismiss = () => {
    hideSessionExpiredModal();
  };

  return (
    <Dialog open={isSessionExpired} onOpenChange={handleDismiss}>
      <DialogContent showCloseButton={false} className="z-99999!">
        <DialogHeader>
          <div className="flex items-center gap-3 mb-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-100">
              <AlertCircle className="h-5 w-5 text-red-600" />
            </div>
            <DialogTitle>Resy Session Expired</DialogTitle>
          </div>
          <DialogDescription className="text-left">
            Your Resy authentication has expired. This happens periodically for
            security reasons. Please reconnect your Resy account to continue
            searching and making reservations.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={handleDismiss}>
            Dismiss
          </Button>
          <Button onClick={handleReconnect} className="bg-resy">
            Reconnect Resy
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
