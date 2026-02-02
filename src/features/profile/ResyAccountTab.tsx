import * as Sentry from "@sentry/react";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import {
    getResyCredentials,
    updateResyPaymentMethod,
    disconnectResyAccount,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Loader2, CreditCard, LogOut, RefreshCw } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";


interface PaymentMethod {
    id: number;
    display?: string;
    type?: string;
    exp_month?: number;
    exp_year?: number;
    is_default?: boolean;
    [key: string]: unknown;
}

interface ResyAccountTabProps {
    onLoadingChange?: (loading: boolean) => void;
}

export function ResyAccountTab({ onLoadingChange }: ResyAccountTabProps = {}) {
    const { currentUser } = useAuth();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [connected, setConnected] = useState(false);
    const [resyEmail, setResyEmail] = useState<string>("");
    const [resyName, setResyName] = useState<string>("");
    const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
    const [selectedPaymentMethodId, setSelectedPaymentMethodId] = useState<
        number | null
    >(null);
    const [currentPaymentMethodId, setCurrentPaymentMethodId] = useState<
        number | null
    >(null);

    useEffect(() => {
        if (currentUser) {
            loadResyCredentials();
        } else {
            setLoading(false);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [currentUser]);

    useEffect(() => {
        onLoadingChange?.(loading);
    }, [loading, onLoadingChange]);

    const loadResyCredentials = async () => {
        if (!currentUser) return;

        setLoading(true);
        try {
            const result = await getResyCredentials(currentUser.uid);
            setConnected(result.connected);
            if (result.connected) {
                setResyEmail(result.email || "");
                setResyName(result.name || "");
                const methods = result.paymentMethods || [];
                console.log("Loaded payment methods:", methods);
                setPaymentMethods(methods);
                setSelectedPaymentMethodId(result.paymentMethodId || null);
                setCurrentPaymentMethodId(result.paymentMethodId || null);
            }
        } catch (error) {
            console.error("Error loading Resy credentials:", error);
            Sentry.captureException(error);
            toast.error("Failed to load Resy account information");
        } finally {
            setLoading(false);
        }
    };

    const handleUpdatePaymentMethod = async () => {
        if (!currentUser || selectedPaymentMethodId === null) return;

        if (selectedPaymentMethodId === currentPaymentMethodId) {
            toast.info("This payment method is already selected");
            return;
        }

        setSaving(true);
        try {
            await updateResyPaymentMethod(currentUser.uid, selectedPaymentMethodId);
            setCurrentPaymentMethodId(selectedPaymentMethodId);
            toast.success("Payment method updated successfully");
        } catch (error) {
            console.error("Error updating payment method:", error);
            Sentry.captureException(error);
            toast.error("Failed to update payment method");
        } finally {
            setSaving(false);
        }
    };

    const handleDisconnect = async () => {
        if (!currentUser) return;

        setSaving(true);
        try {
            await disconnectResyAccount(currentUser.uid);
            setConnected(false);
            setResyEmail("");
            setResyName("");
            setPaymentMethods([]);
            setSelectedPaymentMethodId(null);
            setCurrentPaymentMethodId(null);
            toast.success("Resy account disconnected");
        } catch (error) {
            console.error("Error disconnecting Resy account:", error);
            Sentry.captureException(error);
            toast.error("Failed to disconnect Resy account");
        } finally {
            setSaving(false);
        }
    };

    const handleSwitchAccount = () => {
        navigate("/connect-resy");
    };

    const formatPaymentMethod = (pm: PaymentMethod) => {
        // Access all possible fields from the payment method object
        const pmAny = pm as Record<string, unknown>;

        // Get the display field (last 4 digits)
        const display = pmAny.display as string | undefined;
        const last4 = display || null;

        // Get card type
        const type = (pmAny.type as string) || null;

        // Get expiration date
        const expMonth = pmAny.exp_month as number | undefined;
        const expYear = pmAny.exp_year as number | undefined;

        // Format expiration date
        let expDate = "";
        if (expMonth && expYear) {
            const month = String(expMonth).padStart(2, "0");
            expDate = `${month}/${String(expYear).slice(-2)}`;
        }

        // Capitalize the first letter of card type
        const formattedType = type
            ? type.charAt(0).toUpperCase() + type.slice(1).toLowerCase()
            : "Card";

        // Build the display string
        if (last4) {
            return `${formattedType} •••• ${last4}`;
        } else if (expDate) {
            return `${formattedType} (Expires ${expDate})`;
        } else {
            return `${formattedType} (ID: ${pm.id})`;
        }
    };


    if (!connected) {
        return (
            <div className="space-y-6">
                <Card>
                    <CardHeader>
                        <CardTitle>Resy Account</CardTitle>
                        <CardDescription>
                            Connect your Resy account to enable reservation features
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <Alert>
                            <AlertDescription>
                                You haven't connected your Resy account yet. Connect it to start
                                making reservations.
                            </AlertDescription>
                        </Alert>
                        <div className="mt-6">
                            <Button onClick={() => navigate("/connect-resy")}>
                                Connect Resy Account
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Connection Status Card */}
            <Card>
                <CardHeader>
                    <CardTitle>Connection Status</CardTitle>
                    <CardDescription>
                        Manage your Resy account connection
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="space-y-2">
                        <Label>Resy Account</Label>
                        <div className="rounded-md border bg-muted/50 p-3">
                            <p className="font-medium">{resyName || "N/A"}</p>
                            <p className="text-sm text-muted-foreground">{resyEmail}</p>
                        </div>
                    </div>

                    <div className="flex gap-3">
                        <Button
                            variant="outline"
                            onClick={handleSwitchAccount}
                            disabled={saving}
                        >
                            <RefreshCw className="mr-2 h-4 w-4" />
                            Switch Account
                        </Button>
                        <Button
                            variant="destructive"
                            onClick={handleDisconnect}
                            disabled={saving}
                        >
                            <LogOut className="mr-2 h-4 w-4" />
                            Disconnect
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* Payment Methods Card */}
            <Card>
                <CardHeader>
                    <CardTitle>Payment Methods</CardTitle>
                    <CardDescription>
                        Select which payment method to use for reservations
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    {paymentMethods.length === 0 ? (
                        <Alert>
                            <AlertDescription>
                                No payment methods found. Please add a payment method in your
                                Resy account.
                            </AlertDescription>
                        </Alert>
                    ) : (
                        <>
                            <div className="space-y-2">
                                <Label htmlFor="paymentMethod">Default Payment Method</Label>
                                <Select
                                    value={
                                        selectedPaymentMethodId?.toString() || undefined
                                    }
                                    onValueChange={(value) =>
                                        setSelectedPaymentMethodId(parseInt(value, 10))
                                    }
                                >
                                    <SelectTrigger id="paymentMethod">
                                        <SelectValue placeholder="Select a payment method">
                                            {selectedPaymentMethodId && (
                                                <div className="flex items-center gap-2">
                                                    <CreditCard className="h-4 w-4" />
                                                    {formatPaymentMethod(
                                                        paymentMethods.find(
                                                            (pm) => pm.id === selectedPaymentMethodId
                                                        ) || { id: selectedPaymentMethodId }
                                                    )}
                                                </div>
                                            )}
                                        </SelectValue>
                                    </SelectTrigger>
                                    <SelectContent>
                                        {paymentMethods.map((pm) => {
                                            const isSelected = pm.id === currentPaymentMethodId;
                                            const pmAny = pm as Record<string, unknown>;
                                            const isDefault = pmAny.is_default === true;
                                            return (
                                                <SelectItem
                                                    key={pm.id}
                                                    value={pm.id.toString()}
                                                >
                                                    <div className="flex items-center gap-2">
                                                        <CreditCard className="h-4 w-4" />
                                                        <span>{formatPaymentMethod(pm)}</span>
                                                        {isDefault && !isSelected && (
                                                            <span className="ml-auto text-xs text-muted-foreground">
                                                                (Default)
                                                            </span>
                                                        )}
                                                    </div>
                                                </SelectItem>
                                            );
                                        })}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="flex justify-end">
                                <Button
                                    onClick={handleUpdatePaymentMethod}
                                    disabled={
                                        saving ||
                                        selectedPaymentMethodId === null ||
                                        selectedPaymentMethodId === currentPaymentMethodId
                                    }
                                >
                                    {saving ? (
                                        <>
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                            Saving...
                                        </>
                                    ) : (
                                        "Save"
                                    )}
                                </Button>
                            </div>
                        </>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
