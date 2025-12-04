import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { connectResyAccount } from "@/lib/api";
import ResyLogo from "../assets/ResyLogo.png";

export function OnboardingPage() {
  const navigate = useNavigate();
  const auth = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleConnectResy = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!auth.currentUser) {
      setError("You must be logged in to connect your Resy account");
      return;
    }

    if (!email || !password) {
      setError("Please enter your Resy email and password");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await connectResyAccount(
        auth.currentUser.uid,
        email,
        password
      );

      if (result.success) {
        const paymentMessage = result.hasPaymentMethod
          ? "Payment method found!"
          : "No payment method found. You may need to add one in Resy.";

        toast.success("Resy account connected successfully!", {
          description: paymentMessage,
          icon: <CheckCircle2 className="h-5 w-5 text-green-600" />,
        });

        // Redirect to home page after successful connection
        setTimeout(() => {
          navigate("/");
        }, 1500);
      } else {
        throw new Error(result.error || "Failed to connect Resy account");
      }
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to connect Resy account";
      setError(errorMessage);
      toast.error("Connection failed", {
        description: errorMessage,
        icon: <AlertCircle className="h-5 w-5 text-red-500" />,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <img src={ResyLogo} alt="Resy Logo" className="h-12 mb-4" />
          <CardTitle>Connect Your Resy Account</CardTitle>
          <CardDescription>
            Enter your Resy credentials to connect your account
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleConnectResy} className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="size-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-3">
              <div className="rounded-lg border border-border bg-muted/50 p-4">
                <h3 className="font-semibold text-sm mb-2">How it works:</h3>
                <ol className="text-sm text-muted-foreground space-y-2 list-decimal list-inside">
                  <li>Enter your Resy email and password below</li>
                  <li>Click "Connect Account" to authenticate</li>
                  <li>Your credentials are securely stored</li>
                  <li>
                    Your password is never saved - only an auth token is kept
                  </li>
                </ol>
              </div>

              {/* Fake fields to soak up autofill */}
              <input
                type="text"
                name="fake-username"
                autoComplete="username"
                className="hidden"
              />
              <input
                type="password"
                name="fake-password"
                autoComplete="current-password"
                className="hidden"
              />

              <div className="space-y-2 pt-2">
                <Label htmlFor="email">Resy Email</Label>
                <Input
                  id="email"
                  type="email"
                  name="resy-email"
                  autoComplete="off"
                  placeholder="yourresy@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={loading}
                  required
                />
              </div>

              <div className="space-y-2 pb-2">
                <Label htmlFor="password">Resy Password</Label>
                <Input
                  id="password"
                  type="password"
                  name="resy-password"
                  autoComplete="off"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                  required
                />
              </div>

              <Button
                type="submit"
                disabled={loading || !email || !password}
                className="w-full bg-resy"
                size="lg"
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 size-4 animate-spin" />
                    Connecting...
                  </>
                ) : (
                  <div className="flex flex-row items-center gap-3">
                    <p>Connect Account</p>
                  </div>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
