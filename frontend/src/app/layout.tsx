import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { MswProvider } from "@/mocks/msw-provider";
import { Providers } from "@/shared/components/providers";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Project Memory",
  description: "Capture, organize, and maintain contextual knowledge for your projects",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
          <MswProvider>
            <Providers>{children}</Providers>
          </MswProvider>
        </body>
    </html>
  );
}
