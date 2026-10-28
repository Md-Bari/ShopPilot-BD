"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { Loading } from "@/components/ui/feedback";
import { cx } from "@/components/ui/primitives";
import { useT } from "@/lib/i18n";
import { useSession } from "@/lib/session";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: "▦" },
  { href: "/orders", label: "Orders", icon: "🧾" },
  { href: "/products", label: "Products", icon: "👗" },
  { href: "/customers", label: "Customers", icon: "👥" },
  { href: "/inbox", label: "WhatsApp Inbox", icon: "💬" },
  { href: "/whatsapp/settings", label: "WhatsApp Settings", icon: "⚙" },
  { href: "/reports", label: "Reports", icon: "📈" },
  { href: "/subscription", label: "Subscription", icon: "💳" },
  { href: "/settings", label: "Business Settings", icon: "🏪" },
];

export function AppShell({ children }: { children: ReactNode }) {
  const { me, loading, membership, selectBusiness, signOut } = useSession();
  const { t, lang, setLang } = useT();
  const router = useRouter();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (loading) return;
    if (!me) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    else if (me.memberships.length === 0) router.replace("/onboarding");
  }, [loading, me, pathname, router]);

  useEffect(() => setOpen(false), [pathname]);

  if (loading || !me || !membership) return <Loading />;

  const sidebar = (
    <nav className="flex h-full flex-col">
      <div className="px-4 py-5">
        <Link href="/dashboard" className="text-lg font-bold text-brand-700">
          ShopPilot <span className="text-slate-900">BD</span>
        </Link>
        {me.memberships.length > 1 ? (
          <select
            className="mt-3 w-full rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm"
            value={membership.business_id}
            onChange={(e) => {
              selectBusiness(Number(e.target.value));
              window.location.reload(); // drop data cached for the previous business
            }}
          >
            {me.memberships.map((m) => (
              <option key={m.business_id} value={m.business_id}>
                {m.business_name}
              </option>
            ))}
          </select>
        ) : (
          <p className="mt-2 truncate text-sm text-slate-600">{membership.business_name}</p>
        )}
      </div>
      <ul className="flex-1 space-y-1 px-2">
        {NAV.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                className={cx(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium",
                  active ? "bg-brand-50 text-brand-800" : "text-slate-600 hover:bg-slate-100",
                )}
              >
                <span aria-hidden className="w-5 text-center">
                  {item.icon}
                </span>
                {t(item.label)}
              </Link>
            </li>
          );
        })}
      </ul>
      <div className="space-y-2 border-t border-slate-200 p-4 text-sm">
        <p className="truncate font-medium text-slate-800">{me.user.full_name}</p>
        <p className="truncate text-xs text-slate-500">
          {me.user.email} · {membership.role}
        </p>
        <div className="flex items-center justify-between">
          <button className="text-xs font-medium text-brand-700" onClick={() => setLang(lang === "en" ? "bn" : "en")}>
            {lang === "en" ? "বাংলা" : "English"}
          </button>
          <button
            className="text-xs font-medium text-slate-600 hover:text-rose-600"
            onClick={async () => {
              await signOut();
              router.replace("/login");
            }}
          >
            {t("Sign out")}
          </button>
        </div>
      </div>
    </nav>
  );

  return (
    <div className="min-h-screen bg-slate-50">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-slate-200 bg-white lg:block">{sidebar}</aside>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" onClick={() => setOpen(false)}>
          <div className="absolute inset-0 bg-slate-900/40" />
          <aside className="absolute inset-y-0 left-0 w-72 bg-white shadow-xl" onClick={(e) => e.stopPropagation()}>
            {sidebar}
          </aside>
        </div>
      )}
      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur lg:hidden">
          <button onClick={() => setOpen(true)} className="rounded-lg p-2 hover:bg-slate-100" aria-label="Open menu">
            ☰
          </button>
          <span className="font-semibold text-slate-800">{membership.business_name}</span>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
