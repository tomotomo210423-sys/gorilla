import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Gorilla AI - Advanced AI Assistant",
  description: "Personal AI with memory, roleplay, and knowledge capabilities",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja" className="dark h-full">
      <body className={`${inter.className} h-full`}>{children}</body>
    </html>
  );
}
