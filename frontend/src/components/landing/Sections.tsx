import Link from "next/link";
import type { ComponentType, SVGProps } from "react";
import { FAQS, PLANS } from "@/lib/site";
import {
  ArrowRightIcon,
  BoxIcon,
  ChartIcon,
  ChatIcon,
  CheckIcon,
  ClipboardIcon,
  GlobeIcon,
  ShieldIcon,
  UsersIcon,
  WalletIcon,
} from "./Icons";
import { Logo } from "./LandingNav";
import { Reveal } from "./Reveal";

function SectionHeading({ id, eyebrow, title, intro }: { id: string; eyebrow: string; title: string; intro?: string }) {
  return (
    <Reveal className="mx-auto max-w-2xl text-center">
      <p className="text-sm font-semibold uppercase tracking-widest text-brand-600">{eyebrow}</p>
      <h2 id={id} className="mt-3 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">{title}</h2>
      {intro && <p className="mt-4 text-base leading-relaxed text-slate-600">{intro}</p>}
    </Reveal>
  );
}

/* ---------------- Hero ---------------- */

export function Hero() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-brand-50 via-white to-white">
      <div aria-hidden="true" className="pointer-events-none absolute inset-0">
        <div className="animate-blob absolute -left-24 top-10 h-72 w-72 rounded-full bg-brand-200/50 blur-3xl" />
        <div className="animate-blob absolute right-0 top-40 h-80 w-80 rounded-full bg-emerald-300/30 blur-3xl [animation-delay:-5s]" />
        <div className="absolute inset-0 bg-[radial-gradient(#d1fae5_1px,transparent_1px)] [background-size:22px_22px] [mask-image:linear-gradient(to_bottom,black,transparent_70%)]" />
      </div>

      <div className="relative mx-auto max-w-7xl px-4 pb-20 pt-16 sm:px-6 sm:pt-24 lg:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <p className="animate-fade-up inline-flex items-center gap-2 rounded-full border border-brand-200 bg-white/70 px-4 py-1.5 text-xs font-medium text-brand-700 shadow-sm">
            <span className="h-2 w-2 animate-pulse rounded-full bg-brand-500" />
            Official WhatsApp Cloud API · Made for Bangladesh
          </p>
          <h1 className="animate-fade-up mt-6 text-4xl font-extrabold leading-tight tracking-tight text-slate-900 [animation-delay:100ms] sm:text-5xl lg:text-6xl">
            Run your Facebook shop <span className="text-shine">without the chaos</span>
          </h1>
          <p className="animate-fade-up mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-slate-600 [animation-delay:200ms]">
            ShopPilot BD keeps every order, customer, product and cash-on-delivery payment in one simple dashboard, and
            sends WhatsApp order updates your customers actually read.
          </p>
          <div className="animate-fade-up mt-9 flex flex-col items-center justify-center gap-3 [animation-delay:300ms] sm:flex-row">
            <Link
              href="/register"
              className="group inline-flex items-center gap-2 rounded-xl bg-brand-600 px-6 py-3.5 text-base font-semibold text-white shadow-lg shadow-brand-600/30 transition-all duration-300 hover:-translate-y-0.5 hover:bg-brand-700 hover:shadow-xl hover:shadow-brand-600/40"
            >
              Start your 14-day free trial
              <ArrowRightIcon className="h-5 w-5 transition-transform duration-300 group-hover:translate-x-1" />
            </Link>
            <a
              href="#features"
              className="inline-flex items-center rounded-xl border border-slate-300 bg-white px-6 py-3.5 text-base font-semibold text-slate-700 transition-all duration-300 hover:-translate-y-0.5 hover:border-brand-300 hover:text-brand-700"
            >
              See how it works
            </a>
          </div>
          <p className="animate-fade-up mt-5 text-sm text-slate-500 [animation-delay:400ms]">
            No credit card · Bangla &amp; English · Plans from ৳499/month
          </p>
        </div>

        <div className="animate-fade-up relative mx-auto mt-16 max-w-5xl [animation-delay:500ms]">
          <div className="rounded-2xl border border-slate-200 bg-white/60 p-2 shadow-2xl shadow-brand-900/10 ring-1 ring-slate-900/5 backdrop-blur">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/images/dashboard-preview.svg"
              alt="ShopPilot BD seller dashboard showing today's orders, revenue, COD due, low stock and a weekly sales chart"
              width={960}
              height={600}
              fetchPriority="high"
              className="h-auto w-full rounded-xl"
            />
          </div>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/images/whatsapp-phone.svg"
            alt="Customer receiving a WhatsApp order confirmation from the shop"
            width={320}
            height={620}
            loading="lazy"
            className="animate-float absolute -bottom-10 -right-4 hidden w-44 drop-shadow-2xl sm:block lg:-right-16 lg:w-56"
          />
        </div>
      </div>
    </section>
  );
}

/* ---------------- Highlights strip ---------------- */

const HIGHLIGHTS = [
  { value: "14 days", label: "free trial, all features" },
  { value: "৳499", label: "per month after the trial" },
  { value: "2 languages", label: "Bangla and English" },
  { value: "0 spam", label: "every message sent by you" },
];

export function Highlights() {
  return (
    <section aria-label="Highlights" className="border-y border-slate-200 bg-white">
      <dl className="mx-auto grid max-w-7xl grid-cols-2 gap-px bg-slate-100 lg:grid-cols-4">
        {HIGHLIGHTS.map((h, i) => (
          <Reveal key={h.label} delay={i * 80} className="flex flex-col-reverse bg-white px-6 py-8 text-center">
            <dt className="mt-1 text-sm text-slate-500">{h.label}</dt>
            <dd className="text-2xl font-bold text-brand-700 sm:text-3xl">{h.value}</dd>
          </Reveal>
        ))}
      </dl>
    </section>
  );
}

/* ---------------- Problem → solution ---------------- */

const PAINS = [
  { before: "Orders buried in Messenger chats and screenshots", after: "Every order in one searchable list with a clear status" },
  { before: "Overselling because stock lives in a notebook", after: "Stock is reserved per size and colour the moment you take an order" },
  { before: "Forgetting which COD orders are still unpaid", after: "Paid, partly paid and due amounts tracked for every order" },
];

export function ProblemSolution() {
  return (
    <section className="landing-section bg-white py-24" aria-labelledby="problem-title">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading
          id="problem-title" eyebrow="Why ShopPilot"
          title="Still running your shop from Messenger and a notebook?"
          intro="Most Facebook sellers lose orders, oversell stock and chase payments by hand. ShopPilot BD fixes the boring parts so you can focus on selling."
        />
        <ul className="mt-14 grid gap-6 md:grid-cols-3">
          {PAINS.map((p, i) => (
            <Reveal as="li" key={p.before} delay={i * 120} className="rounded-2xl border border-slate-200 bg-slate-50 p-6">
              <p className="flex items-start gap-3 text-sm text-slate-500 line-through decoration-rose-300">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-rose-100 text-xs text-rose-600 no-underline">
                  ✕
                </span>
                {p.before}
              </p>
              <p className="mt-4 flex items-start gap-3 font-medium text-slate-900">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-100 text-brand-700">
                  <CheckIcon className="h-3.5 w-3.5" />
                </span>
                {p.after}
              </p>
            </Reveal>
          ))}
        </ul>
      </div>
    </section>
  );
}

/* ---------------- Features ---------------- */

type Feature = { icon: ComponentType<SVGProps<SVGSVGElement>>; title: string; text: string };

const FEATURES: Feature[] = [
  { icon: ClipboardIcon, title: "Order management", text: "Create orders in seconds, move them from pending to delivered, and keep a full history of who changed what." },
  { icon: UsersIcon, title: "Customer book", text: "Phone numbers are normalised and duplicates are caught automatically. See every customer's orders and address." },
  { icon: BoxIcon, title: "Products & stock", text: "Sizes, colours, SKUs and photos. Low-stock alerts, and CSV import and export for big catalogues." },
  { icon: WalletIcon, title: "COD, bKash & Nagad", text: "Record full or partial payments with transaction IDs, and always know how much cash is still due." },
  { icon: ChatIcon, title: "WhatsApp updates", text: "Send confirmed, shipped and delivered messages with one click, and reply to customers from a shared inbox." },
  { icon: ChartIcon, title: "Dashboard & reports", text: "Today's orders, revenue, due COD and best sellers at a glance, all in Bangladesh time." },
  { icon: ShieldIcon, title: "Private & secure", text: "Each shop's data is fully separated. Team members get owner, admin or staff roles." },
  { icon: GlobeIcon, title: "Bangla & English", text: "Switch the interface to বাংলা any time. Built for the way sellers in Bangladesh actually work." },
];

export function Features() {
  return (
    <section id="features" className="landing-section bg-slate-50 py-24" aria-labelledby="features-title">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading
          id="features-title" eyebrow="Features"
          title="Everything a growing online shop needs"
          intro="No spreadsheets, no complicated ERP. Just the tools Facebook and Instagram sellers use every day."
        />
        <ul className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((f, i) => (
            <Reveal
              as="li"
              key={f.title}
              delay={(i % 4) * 90}
              className="group rounded-2xl border border-slate-200 bg-white p-6 transition-all duration-300 hover:-translate-y-1 hover:border-brand-200 hover:shadow-xl hover:shadow-brand-900/5"
            >
              <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-600 transition-colors duration-300 group-hover:bg-brand-600 group-hover:text-white">
                <f.icon className="h-6 w-6" />
              </span>
              <h3 className="mt-5 text-base font-semibold text-slate-900">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">{f.text}</p>
            </Reveal>
          ))}
        </ul>
      </div>
    </section>
  );
}

/* ---------------- WhatsApp ---------------- */

const WA_POINTS = [
  "Uses Meta's official WhatsApp Cloud API, so your number is never at risk from unofficial tools",
  "Preview every message and press send yourself. Nothing goes out automatically",
  "Customer opt-in and STOP replies are respected automatically",
  "Delivered and read ticks are tracked for every message",
];

export function WhatsAppSection() {
  return (
    <section id="whatsapp" className="landing-section overflow-hidden bg-white py-24" aria-labelledby="wa-title">
      <div className="mx-auto grid max-w-7xl items-center gap-16 px-4 sm:px-6 lg:grid-cols-2 lg:px-8">
        <Reveal>
          <p className="text-sm font-semibold uppercase tracking-widest text-brand-600">WhatsApp</p>
          <h2 id="wa-title" className="mt-3 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
            Order updates your customers actually read
          </h2>
          <p className="mt-4 leading-relaxed text-slate-600">
            Customers in Bangladesh live on WhatsApp. Confirm orders, share shipping updates and answer questions from
            the same place you manage the order.
          </p>
          <ul className="mt-8 space-y-4">
            {WA_POINTS.map((p) => (
              <li key={p} className="flex gap-3 text-slate-700">
                <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-100 text-brand-700">
                  <CheckIcon className="h-4 w-4" />
                </span>
                <span className="text-sm leading-relaxed sm:text-base">{p}</span>
              </li>
            ))}
          </ul>
        </Reveal>
        <Reveal delay={150} className="relative flex justify-center">
          <div aria-hidden="true" className="absolute inset-0 m-auto h-80 w-80 rounded-full bg-gradient-to-tr from-brand-200 to-emerald-100 blur-2xl" />
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/images/whatsapp-phone.svg"
            alt="WhatsApp conversation: order confirmed, order shipped, and the customer replying thank you"
            width={320}
            height={620}
            loading="lazy"
            className="animate-float relative w-64 sm:w-72"
          />
        </Reveal>
      </div>
    </section>
  );
}

/* ---------------- How it works ---------------- */

const STEPS = [
  { title: "Create your shop", text: "Sign up with your email, add your shop name and payment methods. It takes about two minutes." },
  { title: "Add your products", text: "Add products with sizes, colours, prices and stock, or import your whole catalogue from a CSV file." },
  { title: "Take orders & notify", text: "Create an order from any Facebook chat, confirm it and send a WhatsApp update in one click." },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="landing-section bg-slate-50 py-24" aria-labelledby="how-title">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading id="how-title" eyebrow="How it works" title="Up and running in three steps" />
        <div className="relative mt-14">
          <div aria-hidden="true" className="absolute left-[16%] right-[16%] top-7 hidden h-0.5 bg-gradient-to-r from-brand-100 via-brand-300 to-brand-100 md:block" />
          <ol className="relative grid gap-8 md:grid-cols-3">
          {STEPS.map((s, i) => (
            <Reveal as="li" key={s.title} delay={i * 150} className="relative text-center">
              <span className="relative mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-brand-600 text-xl font-bold text-white shadow-lg shadow-brand-600/30 ring-8 ring-slate-50">
                {i + 1}
              </span>
              <h3 className="mt-6 text-lg font-semibold text-slate-900">{s.title}</h3>
              <p className="mx-auto mt-2 max-w-xs text-sm leading-relaxed text-slate-600">{s.text}</p>
            </Reveal>
          ))}
          </ol>
        </div>
      </div>
    </section>
  );
}

/* ---------------- Pricing ---------------- */

export function Pricing() {
  return (
    <section id="pricing" className="landing-section bg-white py-24" aria-labelledby="pricing-title">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading
          id="pricing-title" eyebrow="Pricing"
          title="Simple pricing in Taka"
          intro="Start free for 14 days. Pay monthly with bKash or Nagad. No contracts, cancel any time."
        />
        <div className="mx-auto mt-14 grid max-w-5xl gap-6 lg:grid-cols-3">
          {PLANS.map((plan, i) => (
            <Reveal
              as="article"
              key={plan.code}
              delay={i * 120}
              className={`relative flex flex-col rounded-2xl border p-8 transition-all duration-300 hover:-translate-y-1 ${
                plan.highlight
                  ? "border-brand-600 bg-gradient-to-b from-brand-50 to-white shadow-2xl shadow-brand-600/15"
                  : "border-slate-200 bg-white hover:shadow-xl"
              }`}
            >
              {plan.highlight && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-brand-600 px-3 py-1 text-xs font-semibold text-white">
                  Most popular
                </span>
              )}
              <h3 className="text-lg font-semibold text-slate-900">{plan.name}</h3>
              <p className="mt-4 flex items-baseline gap-1">
                <span className="text-4xl font-extrabold text-slate-900">৳{plan.priceBdt.toLocaleString("en-US")}</span>
                <span className="text-sm text-slate-500">{plan.priceBdt ? "/ month" : "for 14 days"}</span>
              </p>
              <ul className="mt-6 flex-1 space-y-3 text-sm text-slate-700">
                {[plan.orders, plan.messages, ...plan.features].map((f) => (
                  <li key={f} className="flex gap-2">
                    <CheckIcon className="h-5 w-5 shrink-0 text-brand-600" />
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href="/register"
                className={`mt-8 block rounded-xl px-4 py-3 text-center text-sm font-semibold transition-all duration-300 ${
                  plan.highlight
                    ? "bg-brand-600 text-white shadow-md hover:bg-brand-700"
                    : "border border-slate-300 text-slate-700 hover:border-brand-400 hover:text-brand-700"
                }`}
              >
                {plan.priceBdt ? `Choose ${plan.name}` : "Start free trial"}
              </Link>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------------- FAQ ---------------- */

export function Faq() {
  return (
    <section id="faq" className="landing-section bg-slate-50 py-24" aria-labelledby="faq-title">
      <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
        <SectionHeading id="faq-title" eyebrow="FAQ" title="Questions sellers ask us" />
        <div className="mt-12 space-y-3">
          {FAQS.map((f, i) => (
            <Reveal key={f.q} delay={i * 60}>
              <details className="group rounded-xl border border-slate-200 bg-white p-5 transition-shadow open:shadow-md">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-medium text-slate-900 [&::-webkit-details-marker]:hidden">
                  {f.q}
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-500 transition-transform duration-300 group-open:rotate-45 group-open:bg-brand-100 group-open:text-brand-700">
                    +
                  </span>
                </summary>
                <p className="mt-3 text-sm leading-relaxed text-slate-600">{f.a}</p>
              </details>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------------- Call to action ---------------- */

export function FinalCta() {
  return (
    <section className="bg-white px-4 py-24 sm:px-6 lg:px-8">
      <Reveal className="relative mx-auto max-w-5xl overflow-hidden rounded-3xl bg-gradient-to-br from-brand-800 via-brand-700 to-brand-500 px-8 py-16 text-center shadow-2xl shadow-brand-900/20 sm:px-16">
        <div aria-hidden="true" className="animate-blob absolute -right-16 -top-16 h-64 w-64 rounded-full bg-white/10 blur-2xl" />
        <div aria-hidden="true" className="animate-blob absolute -bottom-20 -left-10 h-64 w-64 rounded-full bg-emerald-300/20 blur-2xl [animation-delay:-7s]" />
        <h2 className="relative text-3xl font-bold tracking-tight text-white sm:text-4xl">Spend less time on admin, more time selling</h2>
        <p className="relative mx-auto mt-4 max-w-xl text-brand-50">
          Set up your shop today and send your first WhatsApp order confirmation in minutes.
        </p>
        <Link
          href="/register"
          className="group relative mt-8 inline-flex items-center gap-2 rounded-xl bg-white px-7 py-3.5 font-semibold text-brand-700 shadow-lg transition-all duration-300 hover:-translate-y-0.5 hover:shadow-xl"
        >
          Start free, no card needed
          <ArrowRightIcon className="h-5 w-5 transition-transform duration-300 group-hover:translate-x-1" />
        </Link>
      </Reveal>
    </section>
  );
}

/* ---------------- Footer ---------------- */

export function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl flex-col gap-8 px-4 py-12 sm:px-6 md:flex-row md:items-start md:justify-between lg:px-8">
        <div className="max-w-sm">
          <Logo />
          <p className="mt-3 text-sm leading-relaxed text-slate-500">
            Order management and WhatsApp updates for Facebook and Instagram sellers in Bangladesh.
          </p>
        </div>
        <nav aria-label="Footer" className="grid grid-cols-2 gap-x-12 gap-y-2 text-sm">
          <a href="#features" className="text-slate-600 hover:text-brand-700">Features</a>
          <Link href="/register" className="text-slate-600 hover:text-brand-700">Create account</Link>
          <a href="#pricing" className="text-slate-600 hover:text-brand-700">Pricing</a>
          <Link href="/login" className="text-slate-600 hover:text-brand-700">Sign in</Link>
          <a href="#faq" className="text-slate-600 hover:text-brand-700">FAQ</a>
        </nav>
      </div>
      <p className="border-t border-slate-100 py-6 text-center text-xs text-slate-400">
        © {new Date().getFullYear()} ShopPilot BD. WhatsApp is a trademark of Meta Platforms, Inc.
      </p>
    </footer>
  );
}
