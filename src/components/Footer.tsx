import ResbotLogo from "@/assets/ResbotLogoRedWithText.svg";
import { Separator } from "@/components/ui/separator";

export function Footer() {
  return (
    <footer className="hidden sm:block bg-background w-full my-10">
      <div className="container mx-auto px-4 py-3 text-center flex justify-center flex-row items-center gap-4 text-sm text-muted-foreground">
        <div className="flex items-center justify-center gap-2">
          <img src={ResbotLogo} className="h-5 grayscale" />
          <p>All Rights Reserved © 2026</p>
        </div>
        <span className="flex items-center h-4">
          <Separator orientation="vertical" className="h-full" />
        </span>
        <p>
          Built by{" "}
          <a
            href="https://www.linkedin.com/in/alexisdrobles"
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-primary"
          >
            Alexis Robles
          </a>
        </p>
      </div>
    </footer>
  );
}
