import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Batchivo - 3D Printing Business Management",
  description:
    "Complete self-hosted platform for managing your 3D printing business. Track inventory, products, production runs, and costs.",
  keywords: [
    "3D printing",
    "business management",
    "inventory tracking",
    "filament management",
    "self-hosted",
    "open source",
  ],
  openGraph: {
    title: "Batchivo - 3D Printing Business Management",
    description:
      "Complete self-hosted platform for managing your 3D printing business.",
    url: "https://batchivo.io",
    siteName: "Batchivo",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Batchivo - 3D Printing Business Management",
    description:
      "Complete self-hosted platform for managing your 3D printing business.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="scroll-smooth">
      <body className={`${inter.variable} font-sans antialiased`}>
        {children}
      </body>
    </html>
  );
}
