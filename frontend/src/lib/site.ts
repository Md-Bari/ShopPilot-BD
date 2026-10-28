/** Public site facts shared by the landing page, metadata, sitemap and structured data.
 *  Plan numbers mirror the seeded plans in backend/app/application/subscriptions.py. */

export const SITE_URL = (process.env.SITE_URL || "http://localhost:3000").replace(/\/$/, "");

export const SITE = {
  name: "ShopPilot BD",
  title: "ShopPilot BD — Order management & WhatsApp for Facebook sellers in Bangladesh",
  description:
    "Manage Facebook and Instagram orders, customers, stock, COD payments and WhatsApp order updates in one simple dashboard. Built for Bangladeshi online sellers. 14-day free trial.",
  keywords: [
    "order management Bangladesh",
    "Facebook seller software",
    "f-commerce Bangladesh",
    "WhatsApp order confirmation",
    "WhatsApp Cloud API Bangladesh",
    "online shop inventory Bangladesh",
    "cash on delivery tracking",
    "bKash Nagad order tracking",
    "অনলাইন শপ অর্ডার ম্যানেজমেন্ট",
  ],
  locale: "en_BD",
} as const;

export type Plan = {
  code: string;
  name: string;
  priceBdt: number;
  orders: string;
  messages: string;
  highlight?: boolean;
  features: string[];
};

export const PLANS: Plan[] = [
  {
    code: "trial",
    name: "Free Trial",
    priceBdt: 0,
    orders: "50 orders",
    messages: "100 WhatsApp messages",
    features: ["14 days, no card needed", "All features included", "Bangla & English interface"],
  },
  {
    code: "starter",
    name: "Starter",
    priceBdt: 499,
    orders: "300 orders / month",
    messages: "500 WhatsApp messages / month",
    highlight: true,
    features: ["All features included", "Products, variants & stock", "Sales reports & dashboard"],
  },
  {
    code: "growth",
    name: "Growth",
    priceBdt: 999,
    orders: "Unlimited orders",
    messages: "2,000 WhatsApp messages / month",
    features: ["Everything in Starter", "No monthly order limit", "4× the WhatsApp messages"],
  },
];

export const FAQS: { q: string; a: string }[] = [
  {
    q: "Who is ShopPilot BD for?",
    a: "Small and growing online sellers in Bangladesh who take orders through Facebook pages, Instagram or Messenger and deliver with cash on delivery, bKash or Nagad.",
  },
  {
    q: "Does it use the official WhatsApp API?",
    a: "Yes. ShopPilot BD connects to Meta's official WhatsApp Cloud API. It never uses unofficial tools that can get your number banned.",
  },
  {
    q: "Will it send messages to my customers automatically?",
    a: "No. You always preview a message and press send yourself. The app also blocks messages to customers who have not opted in or have replied STOP.",
  },
  {
    q: "How do I pay for a plan?",
    a: "Pay with bKash or Nagad and request the plan from the Subscription page. The ShopPilot team confirms the payment and activates your plan.",
  },
  {
    q: "Can my staff use the same shop?",
    a: "Yes. Add team members by email and give them the owner, admin or staff role. Each shop's data is kept completely separate.",
  },
  {
    q: "Is there a Bangla version?",
    a: "Yes. Switch between English and বাংলা at any time from the sidebar.",
  },
];
