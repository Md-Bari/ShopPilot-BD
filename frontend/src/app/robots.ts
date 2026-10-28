import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

/** Only the public pages are crawlable; the seller app and API stay out of search results. */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: [
        "/api/",
        "/media/",
        "/dashboard",
        "/orders",
        "/products",
        "/customers",
        "/inbox",
        "/reports",
        "/subscription",
        "/settings",
        "/whatsapp",
        "/onboarding",
        "/reset-password",
      ],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
