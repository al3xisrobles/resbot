import { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { updateProfile } from "firebase/auth";
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
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

export function ProfileTab() {
    const { currentUser } = useAuth();
    const [displayName, setDisplayName] = useState("");
    const [email, setEmail] = useState("");
    const [loading, setLoading] = useState(false);
    const [accountCreated, setAccountCreated] = useState<string | null>(null);

    useEffect(() => {
        if (currentUser) {
            setDisplayName(currentUser.displayName || "");
            setEmail(currentUser.email || "");
            // Get account creation date from metadata
            if (currentUser.metadata.creationTime) {
                const created = new Date(currentUser.metadata.creationTime);
                setAccountCreated(created.toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                }));
            }
        }
    }, [currentUser]);

    const handleSave = async () => {
        if (!currentUser) return;

        setLoading(true);
        try {
            await updateProfile(currentUser, {
                displayName: displayName.trim() || null,
            });
            toast.success("Profile updated successfully");
        } catch (error) {
            console.error("Error updating profile:", error);
            toast.error("Failed to update profile");
        } finally {
            setLoading(false);
        }
    };

    const getInitials = () => {
        if (displayName) {
            return displayName
                .split(" ")
                .map((n) => n[0])
                .join("")
                .toUpperCase()
                .slice(0, 2);
        }
        if (email) {
            return email[0].toUpperCase();
        }
        return "U";
    };

    if (!currentUser) {
        return <div>Please log in to view your profile.</div>;
    }

    return (
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle>Profile Information</CardTitle>
                    <CardDescription>
                        View and update your profile details here.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    {/* Avatar */}
                    <div className="flex items-center gap-4">
                        <div className="flex h-20 w-20 items-center justify-center rounded-full bg-muted text-2xl font-semibold">
                            {currentUser.photoURL ? (
                                <img
                                    src={currentUser.photoURL}
                                    alt="Profile"
                                    className="h-full w-full rounded-full object-cover"
                                />
                            ) : (
                                getInitials()
                            )}
                        </div>
                        <div>
                            <p className="text-sm font-medium">Profile Picture</p>
                        </div>
                    </div>

                    {/* Display Name */}
                    <div className="space-y-2">
                        <Label htmlFor="displayName">Display Name</Label>
                        <Input
                            id="displayName"
                            value={displayName}
                            onChange={(e) => setDisplayName(e.target.value)}
                            placeholder="Enter your name"
                        />
                    </div>

                    {/* Email */}
                    <div className="space-y-2">
                        <Label htmlFor="email">Email</Label>
                        <Input
                            id="email"
                            type="email"
                            value={email}
                            disabled
                            className="bg-muted/50"
                        />
                    </div>

                    {/* Account Created */}
                    {accountCreated && (
                        <div className="space-y-2">
                            <Label>Account Created</Label>
                            <p className="text-sm text-muted-foreground">{accountCreated}</p>
                        </div>
                    )}

                    <div className="flex justify-end">
                        <Button onClick={handleSave} disabled={loading}>
                            {loading ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Saving...
                                </>
                            ) : (
                                "Save"
                            )}
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
