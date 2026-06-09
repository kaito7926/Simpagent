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
  title: "Đăng nhập | SimpAgent",
  description: "Truy cập an toàn cho tài khoản và phiên SimpAgent.",
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
    <html lang="vi">
      <body className={beVietnamPro.variable}>{children}</body>
    </html>
  );
}
