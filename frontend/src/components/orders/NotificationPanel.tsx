"use client";

import Link from "next/link";
import { useState } from "react";
import { ErrorAlert, Modal, SuccessAlert } from "@/components/ui/feedback";
import { Badge, Button, Card, Select, Textarea } from "@/components/ui/primitives";
import { ApiError, newIdempotencyKey } from "@/lib/api/client";
import { orderApi } from "@/lib/api/endpoints";
import { formatDateTime, formatPhone } from "@/lib/format";
import { useAction } from "@/lib/hooks";
import type { NotificationKind, NotificationPreview, OrderDetail } from "@/lib/types";
import { MessageStatusBadge } from "./StatusBadge";

const KINDS: { kind: NotificationKind; label: string }[] = [
  { kind: "order_confirmed", label: "Order confirmation" },
  { kind: "order_shipped", label: "Shipped notification" },
  { kind: "order_delivered", label: "Delivered notification" },
  { kind: "custom", label: "Custom message (24h window only)" },
];

/** Seller-initiated WhatsApp notifications: always preview first, then an explicit confirm. */
export function NotificationPanel({ order, onSent }: { order: OrderDetail; onSent: () => void }) {
  const [kind, setKind] = useState<NotificationKind>("order_confirmed");
  const [customText, setCustomText] = useState("");
  const [preview, setPreview] = useState<NotificationPreview | null>(null);
  const [idempotencyKey, setIdempotencyKey] = useState(newIdempotencyKey());
  const [sentMessage, setSentMessage] = useState<string | null>(null);

  const previewAction = useAction(orderApi.previewNotification);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<ApiError | null>(null);

  async function openPreview() {
    setSentMessage(null);
    setSendError(null);
    const result = await previewAction.run(order.id, kind, kind === "custom" ? customText : undefined);
    if (result) {
      setPreview(result);
      setIdempotencyKey(newIdempotencyKey()); // one key per confirmed send attempt
    }
  }

  async function confirmSend() {
    if (!preview) return;
    setSending(true);
    setSendError(null);
    try {
      const result = await orderApi.sendNotification(order.id, kind, idempotencyKey, kind === "custom" ? customText : undefined);
      setPreview(null);
      setSentMessage(result.replayed ? "This message was already sent — not sent again." : "Message accepted by WhatsApp.");
    } catch (err) {
      const apiError = err instanceof ApiError ? err : new ApiError(0, "unknown", "Unexpected error");
      setSendError(apiError);
      if (apiError.code === "delivery_unknown") {
        // Meta may have sent it: never offer an immediate resend.
        setPreview({ ...preview, can_send: false, blockers: ["Delivery could not be confirmed. Wait for the status below to update before sending again."] });
      } else {
        setIdempotencyKey(newIdempotencyKey()); // the failed attempt is final; a retry is a new message
      }
    } finally {
      setSending(false);
      onSent(); // refresh the order so the attempt and its status are visible
    }
  }

  return (
    <Card title="WhatsApp notifications">
      <div className="space-y-3">
        <Select value={kind} onChange={(e) => setKind(e.target.value as NotificationKind)}>
          {KINDS.map((k) => (
            <option key={k.kind} value={k.kind}>
              {k.label}
            </option>
          ))}
        </Select>
        {kind === "custom" && (
          <Textarea placeholder="Type your message to the customer" maxLength={4096} value={customText} onChange={(e) => setCustomText(e.target.value)} />
        )}
        <Button variant="secondary" className="w-full" onClick={openPreview} loading={previewAction.pending}>
          Preview message
        </Button>
        <ErrorAlert error={previewAction.error} />
        {sentMessage && <SuccessAlert>{sentMessage}</SuccessAlert>}

        {order.messages.length > 0 && (
          <ul className="divide-y divide-slate-100 border-t border-slate-100 pt-2 text-sm">
            {order.messages.map((m) => (
              <li key={m.id} className="py-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium">{m.notification_kind?.replace("order_", "").replace("_", " ") || m.message_type}</span>
                  <MessageStatusBadge status={m.status} />
                </div>
                <p className="text-xs text-slate-500">{formatDateTime(m.created_at)}</p>
                {m.error_detail && <p className="mt-1 text-xs text-rose-600">{m.error_detail}</p>}
              </li>
            ))}
          </ul>
        )}
      </div>

      <Modal
        open={!!preview}
        title="Confirm WhatsApp message"
        onClose={() => setPreview(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setPreview(null)}>
              Cancel
            </Button>
            <Button onClick={confirmSend} loading={sending} disabled={!preview?.can_send}>
              Send now
            </Button>
          </>
        }
      >
        {preview && (
          <>
            <dl className="grid grid-cols-3 gap-2 text-sm">
              <dt className="text-slate-500">To</dt>
              <dd className="col-span-2 font-medium">
                {preview.recipient_name} · {formatPhone(preview.recipient_phone)}
              </dd>
              <dt className="text-slate-500">Sent as</dt>
              <dd className="col-span-2">
                {preview.channel === "template" ? (
                  <Badge tone="blue">Template: {preview.template_name}</Badge>
                ) : (
                  <Badge tone="purple">Free-form text</Badge>
                )}
              </dd>
              <dt className="text-slate-500">Mode</dt>
              <dd className="col-span-2">{preview.mode === "test" ? <Badge tone="amber">Test number</Badge> : <Badge tone="green">Production</Badge>}</dd>
              <dt className="text-slate-500">24h window</dt>
              <dd className="col-span-2">
                {preview.service_window_open ? `Open until ${formatDateTime(preview.service_window_expires_at)}` : "Closed"}
              </dd>
              <dt className="text-slate-500">Consent</dt>
              <dd className="col-span-2">{preview.transactional_consent ?? "Not recorded"}</dd>
            </dl>
            <div className="rounded-xl bg-[#e7fbe6] p-3 text-sm text-slate-800 shadow-inner whitespace-pre-wrap">{preview.text || "—"}</div>
            {preview.blockers.length > 0 && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                <p className="font-medium">This message cannot be sent yet:</p>
                <ul className="mt-1 list-disc space-y-1 pl-5">
                  {preview.blockers.map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
                {preview.transactional_consent !== "granted" && (
                  <Link href={`/customers/${order.customer.id}`} className="mt-2 inline-block font-medium underline">
                    Record customer consent
                  </Link>
                )}
              </div>
            )}
            <ErrorAlert error={sendError} />
          </>
        )}
      </Modal>
    </Card>
  );
}
