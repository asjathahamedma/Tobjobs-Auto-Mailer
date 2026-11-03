import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TopJobs Auto Mailer",
  description: "Private TopJobs search and application workspace",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
