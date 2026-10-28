import Link from "next/link";
import { MenuIcon } from "./Icons";

const LINKS = [
  { href: "#features", label: "Features" },
  { href: "#whatsapp", label: "WhatsApp" },
  { href: "#how-it-works", label: "How it works" },
  { href: "#pricing", label: "Pricing" },
  { href: "#faq", label: "FAQ" },
];

export function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2 text-lg font-bold text-brand-700" aria-label="ShopPilot BD home">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/icon.svg" alt="" width={30} height={30} className="h-[30px] w-[30px]" />
      <span>
        ShopPilot <span className="text-slate-900">BD</span>
      </span>
    </Link>
  );
}

export function LandingNav() {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/80 backdrop-blur-lg">
      <nav aria-label="Main" className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Logo />
        <ul className="hidden items-center gap-7 text-sm font-medium text-slate-600 md:flex">
          {LINKS.map((l) => (
            <li key={l.href}>
              <a href={l.href} className="transition-colors hover:text-brand-700">
                {l.label}
              </a>
            </li>
          ))}
        </ul>
        <div className="hidden items-center gap-2 md:flex">
          <Link href="/login" className="rounded-lg px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:text-brand-700">
            Sign in
          </Link>
          <Link
            href="/register"
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-sm shadow-brand-600/30 transition-all hover:-translate-y-0.5 hover:bg-brand-700 hover:shadow-md"
          >
            Start free trial
          </Link>
        </div>

        {/* Mobile menu without client JavaScript */}
        <details className="group relative md:hidden">
          <summary className="flex cursor-pointer list-none items-center rounded-lg p-2 text-slate-700 hover:bg-slate-100 [&::-webkit-details-marker]:hidden">
            <MenuIcon className="h-6 w-6" />
            <span className="sr-only">Open menu</span>
          </summary>
          <div className="absolute right-0 mt-2 w-60 origin-top-right rounded-xl border border-slate-200 bg-white p-2 shadow-xl">
            {LINKS.map((l) => (
              <a key={l.href} href={l.href} className="block rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-brand-50">
                {l.label}
              </a>
            ))}
            <div className="my-2 border-t border-slate-100" />
            <Link href="/login" className="block rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-brand-50">
              Sign in
            </Link>
            <Link href="/register" className="mt-1 block rounded-lg bg-brand-600 px-3 py-2 text-center text-sm font-semibold text-white">
              Start free trial
            </Link>
          </div>
        </details>
      </nav>
    </header>
  );
}
