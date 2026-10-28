import type { Metadata, Viewport } from "next";
import { Fira_Code } from "next/font/google";
import type { ReactNode } from "react";
import { I18nProvider } from "@/lib/i18n";
import { SessionProvider } from "@/lib/session";
import { SITE, SITE_URL } from "@/lib/site";
import "./globals.css";

const firaCode = Fira_Code({ subsets: ["latin"], variable: "--font-fira-code", display: "swap" });

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: SITE.title, template: `%s · ${SITE.name}` },
  description: SITE.description,
  keywords: [...SITE.keywords],
  applicationName: SITE.name,
  openGraph: {
    type: "website",
    siteName: SITE.name,
    title: SITE.title,
    description: SITE.description,
    url: "/",
    locale: SITE.locale,
  },
  twitter: { card: "summary_large_image", title: SITE.title, description: SITE.description },
  formatDetection: { telephone: false },
};

export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#059669" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={firaCode.variable}>
      <body>
        <I18nProvider>
          <SessionProvider>{children}</SessionProvider>
        </I18nProvider>
      </body>
    </html>
  );
}
