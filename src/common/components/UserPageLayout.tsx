import type { ReactNode } from "react";

interface UserPageLayoutProps {
    title: string;
    description?: string;
    children: ReactNode;
}

export function UserPageLayout({
    title,
    description,
    children,
}: UserPageLayoutProps) {
    return (
        <div className="h-screen bg-background overflow-auto">
            <main className="container mx-auto px-4 py-8 max-w-240">
                {(title || description) && (
                    <div className="mb-8">
                        {title && (
                            <h1 className="text-3xl font-bold tracking-tight mb-2">
                                {title}
                            </h1>
                        )}
                        {description && (
                            <p className="text-muted-foreground">{description}</p>
                        )}
                    </div>
                )}
                {children}
            </main>
        </div>
    );
}
