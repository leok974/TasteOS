import "./globals.css";
import type { Metadata } from "next";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "TasteOS",
  description: "Agentic cooking app",
};

import { AppHeader } from "@/components/AppHeader";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-base text-stone-900 font-sans min-h-screen flex flex-col">
        <Providers>
          <AppHeader />
          <div className="flex-1">
            {children}
          </div>
        </Providers>
      </body>
    </html>
  );
}
