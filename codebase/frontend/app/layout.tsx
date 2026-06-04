import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Vinmec AI Booking Agent",
  description: "Checkpoint MVP for a Vinmec-style AI appointment booking agent"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
