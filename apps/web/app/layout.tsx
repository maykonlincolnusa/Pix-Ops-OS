import type { Metadata, Viewport } from "next";

import { Providers } from "@/app/providers";
import { PwaRegistration } from "@/components/pwa-registration";

import "./globals.css";

export const metadata: Metadata = {
  title: "PixOps OS",
  description:
    "Sistema operacional financeiro para rastrear, auditar e conciliar pagamentos em tempo real.",
  manifest: "/manifest.webmanifest",
};

export const viewport: Viewport = {
  themeColor: "#0b1325",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body className="font-sans antialiased">
        <PwaRegistration />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
