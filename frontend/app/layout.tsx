import type { ReactNode } from "react";

import type { Metadata } from "next";
import localFont from "next/font/local";

import "./globals.css";

const beVietnamPro = localFont({
  src: "./fonts/BeVietnamPro-Variable.woff2",
  variable: "--font-be-vietnam-pro",
  display: "swap",
});

export const metadata: Metadata = {
  title: "SimpAgent",
  description: "Private direct chat with protected SimpAgent sessions.",
  icons: {
    icon: "/icon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={beVietnamPro.variable}>{children}</body>
    </html>
  );
}
