import * as Sentry from "@sentry/react";
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
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
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

        // Refresh /me data to update onboarding status
        await auth.refreshMe();

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
      Sentry.captureException(err);
      toast.error("Connection failed", {
        description: errorMessage,
        icon: <AlertCircle className="h-5 w-5 text-red-500" />,
      });
      setLoading(false);
    }
  };

  return (
    <div className="h-screen flex justify-center bg-background px-4 overflow-y-auto">
      <Card className="w-full max-w-md my-16 h-max">
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
              <Alert
                variant="destructive"
                className="flex items-center flex-row gap-2 justify-between"
              >
                <div className="flex flex-row gap-2 items-center">
                  <AlertCircle className="size-4" />
                  <AlertDescription>{error}</AlertDescription>
                </div>
                {error === "Invalid Resy login" && (
                  <Button
                    size="sm"
                    className="ml-auto"
                    onClick={() => {
                      window.open(
                        "https://resy.com",
                        "_blank",
                        "noopener,noreferrer"
                      );
                    }}
                  >
                    <p>Go to Resy.com</p>
                    <ChevronRight className="size-4" />
                  </Button>
                )}
              </Alert>
            )}

            <div className="space-y-3">
              <div className="rounded-lg border border-border bg-muted/50 p-4">
                <h3 className="font-semibold text-sm mb-2">How it works:</h3>
                <ol className="text-sm text-muted-foreground space-y-2 list-decimal list-inside">
                  <li>Enter your Resy email and password below</li>
                  <li>
                    Click <strong>Connect Account</strong> to authenticate
                  </li>
                  <li>
                    We <strong>never</strong> store your password—only a secure
                    authorization token from Resy, which allows us to perform
                    reservation checks and snipes on your behalf.
                  </li>
                </ol>

                {/* Learn More Dropdown */}
                <Collapsible className="mt-3">
                  <CollapsibleTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="px-0 text-sm w-full"
                    >
                      <AlertCircle className="size-4" />
                      <p>Why do I need to give you my password?</p>
                      <ChevronDown className="size-4 ml-1 transition-transform data-[state=open]:rotate-180" />
                    </Button>
                  </CollapsibleTrigger>

                  <CollapsibleContent className="text-sm text-muted-foreground mt-2 space-y-2">
                    <p>
                      To make reservations on your behalf, we need permission
                      from your Resy account. The only way Resy allows apps to
                      do this is by signing in once and receiving an
                      authorization token that belongs to your account.
                    </p>

                    <p>
                      This token is what lets us check availability, potentially
                      use your saved payment method, and book the reservation
                      for you the moment it drops.
                    </p>

                    <p>
                      We never store your email or password. They’re only used
                      one time to request your token from Resy—and then they’re
                      immediately thrown away. The only thing we save is the
                      token, which is the minimum needed for your snipes to run
                      automatically.
                    </p>
                  </CollapsibleContent>
                </Collapsible>
              </div>

              {/* Fake fields to suppress autofill */}
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
