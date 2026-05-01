import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";

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
      <body className="font-sans antialiased">
        {children}
        {process.env.NEXT_PUBLIC_UMAMI_WEBSITE_ID && (
          <Script
            defer
            src="https://analytics.batchivo.com/script.js"
            data-website-id={process.env.NEXT_PUBLIC_UMAMI_WEBSITE_ID}
          />
        )}
      </body>
    </html>
  );
}
