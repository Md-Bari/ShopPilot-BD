import Link from "next/link";
import type { ReactNode } from "react";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-brand-50 to-slate-100 px-4 py-10">
      <Link href="/" className="mb-6 text-2xl font-bold text-brand-700">
        ShopPilot <span className="text-slate-900">BD</span>
      </Link>
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">{children}</div>
      <p className="mt-6 text-center text-xs text-slate-500">Orders, customers and WhatsApp — in one place.</p>
    </div>
  );
}
