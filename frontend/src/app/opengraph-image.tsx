import { ImageResponse } from "next/og";
import { SITE } from "@/lib/site";

export const alt = SITE.title;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

/** Social share card (Facebook, WhatsApp, X, LinkedIn), rendered to PNG at build time. */
export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: 72,
          background: "linear-gradient(135deg, #064e3b 0%, #047857 55%, #10b981 100%)",
          color: "white",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <div
            style={{
              width: 72,
              height: 72,
              borderRadius: 18,
              background: "white",
              color: "#047857",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 40,
              fontWeight: 800,
            }}
          >
            SP
          </div>
          <div style={{ fontSize: 40, fontWeight: 800 }}>ShopPilot BD</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{ fontSize: 68, fontWeight: 800, lineHeight: 1.1, maxWidth: 980 }}>
            Orders, customers & WhatsApp updates in one dashboard
          </div>
          <div style={{ fontSize: 30, color: "#d1fae5" }}>
            Built for Facebook & Instagram sellers in Bangladesh · 14-day free trial
          </div>
        </div>
      </div>
    ),
    size,
  );
}
