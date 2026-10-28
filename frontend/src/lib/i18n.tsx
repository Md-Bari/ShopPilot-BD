"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type Lang = "en" | "bn";

const bn: Record<string, string> = {
  Dashboard: "ড্যাশবোর্ড",
  Orders: "অর্ডার",
  Products: "পণ্য",
  Customers: "গ্রাহক",
  "WhatsApp Inbox": "হোয়াটসঅ্যাপ ইনবক্স",
  "WhatsApp Settings": "হোয়াটসঅ্যাপ সেটিংস",
  Reports: "রিপোর্ট",
  Subscription: "সাবস্ক্রিপশন",
  "Business Settings": "ব্যবসার সেটিংস",
  "Sign out": "সাইন আউট",
  Back: "ফিরে যান",
  "Sign in": "সাইন ইন",
  "Create account": "অ্যাকাউন্ট খুলুন",
  Email: "ইমেইল",
  Password: "পাসওয়ার্ড",
  "Full name": "পূর্ণ নাম",
  "Forgot password?": "পাসওয়ার্ড ভুলে গেছেন?",
  Search: "খুঁজুন",
  Save: "সংরক্ষণ",
  Cancel: "বাতিল",
  Loading: "লোড হচ্ছে…",
  "New order": "নতুন অর্ডার",
  "New product": "নতুন পণ্য",
  "New customer": "নতুন গ্রাহক",
  "Today's orders": "আজকের অর্ডার",
  "Gross order value": "মোট অর্ডার মূল্য",
  "Collected revenue": "সংগৃহীত আয়",
  "Estimated profit": "আনুমানিক লাভ",
  "Pending confirmations": "নিশ্চিতকরণের অপেক্ষায়",
  "Low stock": "স্টক কম",
  "Recent activity": "সাম্প্রতিক কার্যক্রম",
  "WhatsApp messages": "হোয়াটসঅ্যাপ বার্তা",
  Status: "অবস্থা",
  Total: "মোট",
  Customer: "গ্রাহক",
  Phone: "ফোন",
  Address: "ঠিকানা",
  Price: "দাম",
  Stock: "স্টক",
  Quantity: "পরিমাণ",
  "Delivery charge": "ডেলিভারি চার্জ",
  Discount: "ছাড়",
  Subtotal: "সাবটোটাল",
  "Payment method": "পেমেন্ট পদ্ধতি",
  Note: "নোট",
  "Order history": "অর্ডারের ইতিহাস",
  "Send WhatsApp": "হোয়াটসঅ্যাপ পাঠান",
  pending: "অপেক্ষমাণ",
  confirmed: "নিশ্চিত",
  processing: "প্রস্তুত হচ্ছে",
  shipped: "পাঠানো হয়েছে",
  delivered: "ডেলিভারি সম্পন্ন",
  cancelled: "বাতিল",
  returned: "ফেরত",
  unpaid: "অপরিশোধিত",
  partial: "আংশিক",
  paid: "পরিশোধিত",
};

const dictionaries: Record<Lang, Record<string, string>> = { en: {}, bn };

interface I18nValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: string) => string;
}

const I18nContext = createContext<I18nValue>({ lang: "en", setLang: () => {}, t: (k) => k });

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem("sp.lang");
      if (saved === "bn" || saved === "en") setLangState(saved);
    } catch {
      // ignore
    }
  }, []);

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    try {
      window.localStorage.setItem("sp.lang", next);
    } catch {
      // ignore
    }
  }, []);

  const value = useMemo<I18nValue>(
    () => ({ lang, setLang, t: (key: string) => dictionaries[lang][key] ?? key }),
    [lang, setLang],
  );

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useT() {
  return useContext(I18nContext);
}
