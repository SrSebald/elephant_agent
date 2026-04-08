import type { ReactNode } from "react";
import type { Metadata } from "next";
import { Fraunces, IBM_Plex_Mono, Space_Grotesk } from "next/font/google";

import "./globals.css";

const headingFont = Fraunces({
  subsets: ["latin"],
  variable: "--font-heading",
  weight: ["600", "700"],
});

const bodyFont = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-body",
  weight: ["400", "500", "700"],
});

const monoFont = IBM_Plex_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Elephant Agent",
  description: "Incident intake dashboard for the Elephant Agent MVP.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${headingFont.variable} ${bodyFont.variable} ${monoFont.variable}`}>
        {children}
      </body>
    </html>
  );
}
