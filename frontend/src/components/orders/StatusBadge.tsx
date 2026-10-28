"use client";

import { Badge, type Tone } from "@/components/ui/primitives";
import { useT } from "@/lib/i18n";

const ORDER_TONES: Record<string, Tone> = {
  pending: "amber",
  confirmed: "blue",
  processing: "purple",
  shipped: "blue",
  delivered: "green",
  cancelled: "red",
  returned: "gray",
};

const PAYMENT_TONES: Record<string, Tone> = { unpaid: "gray", partial: "amber", paid: "green" };

const MESSAGE_TONES: Record<string, Tone> = {
  pending: "gray",
  accepted: "blue",
  sent: "blue",
  delivered: "green",
  read: "green",
  failed: "red",
  unknown: "amber",
  received: "purple",
};

export function OrderStatusBadge({ status }: { status: string }) {
  const { t } = useT();
  return <Badge tone={ORDER_TONES[status] ?? "gray"}>{t(status)}</Badge>;
}

export function PaymentStatusBadge({ status }: { status: string }) {
  const { t } = useT();
  return <Badge tone={PAYMENT_TONES[status] ?? "gray"}>{t(status)}</Badge>;
}

export function MessageStatusBadge({ status }: { status: string }) {
  return <Badge tone={MESSAGE_TONES[status] ?? "gray"}>{status === "unknown" ? "delivery unknown" : status}</Badge>;
}

export const ORDER_STATUSES = ["pending", "confirmed", "processing", "shipped", "delivered", "cancelled", "returned"] as const;
