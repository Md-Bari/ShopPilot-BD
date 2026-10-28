import type { Metadata } from "next";
import { LandingNav } from "@/components/landing/LandingNav";
import {
  Faq,
  Features,
  FinalCta,
  Footer,
  Hero,
  Highlights,
  HowItWorks,
  Pricing,
  ProblemSolution,
  WhatsAppSection,
} from "@/components/landing/Sections";
import { FAQS, PLANS, SITE, SITE_URL } from "@/lib/site";

export const metadata: Metadata = {
  title: { absolute: SITE.title },
  alternates: { canonical: "/" },
};

/** Structured data so search engines can show price, FAQ and app details in results. */
const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": `${SITE_URL}/#organization`,
      name: SITE.name,
      url: SITE_URL,
      logo: `${SITE_URL}/icon.svg`,
      areaServed: "BD",
    },
    {
      "@type": "WebSite",
      "@id": `${SITE_URL}/#website`,
      url: SITE_URL,
      name: SITE.name,
      inLanguage: ["en", "bn"],
      publisher: { "@id": `${SITE_URL}/#organization` },
    },
    {
      "@type": "SoftwareApplication",
      name: SITE.name,
      applicationCategory: "BusinessApplication",
      operatingSystem: "Web",
      description: SITE.description,
      url: SITE_URL,
      offers: PLANS.map((p) => ({
        "@type": "Offer",
        name: p.name,
        price: p.priceBdt.toFixed(2),
        priceCurrency: "BDT",
      })),
      publisher: { "@id": `${SITE_URL}/#organization` },
    },
    {
      "@type": "FAQPage",
      mainEntity: FAQS.map((f) => ({
        "@type": "Question",
        name: f.q,
        acceptedAnswer: { "@type": "Answer", text: f.a },
      })),
    },
  ],
};

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c") }}
      />
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:shadow"
      >
        Skip to content
      </a>
      <LandingNav />
      <main id="main">
        <Hero />
        <Highlights />
        <ProblemSolution />
        <Features />
        <WhatsAppSection />
        <HowItWorks />
        <Pricing />
        <Faq />
        <FinalCta />
      </main>
      <Footer />
    </div>
  );
}
