"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { OrderStatusBadge } from "@/components/orders/StatusBadge";
import { ErrorAlert, Loading, PageHeader } from "@/components/ui/feedback";
import { Badge, Button, Card, Field, Input, Select, Textarea } from "@/components/ui/primitives";
import { customerApi } from "@/lib/api/endpoints";
import { formatBDT, formatDateTime, formatPhone } from "@/lib/format";
import { useAction, useApi } from "@/lib/hooks";

const SOURCES = [
  ["in_person", "In person"],
  ["phone_call", "Phone call"],
  ["whatsapp", "WhatsApp"],
  ["facebook", "Facebook / Messenger"],
  ["website", "Website"],
  ["other", "Other"],
];

function ConsentBadge({ status }: { status: string | null }) {
  if (status === "granted") return <Badge tone="green">Opted in</Badge>;
  if (status === "revoked") return <Badge tone="red">Opted out</Badge>;
  return <Badge>Not recorded</Badge>;
}

export default function CustomerDetailPage() {
  const id = Number(useParams<{ id: string }>().id);
  const { data, error, loading, reload } = useApi(() => customerApi.get(id), [id]);
  const [form, setForm] = useState({ name: "", phone: "", address: "", area: "", notes: "" });
  const [consent, setConsent] = useState({ purpose: "transactional", status: "granted", source: "facebook", note: "" });
  const update = useAction(customerApi.update);
  const recordConsent = useAction(customerApi.recordConsent);

  useEffect(() => {
    if (data) {
      const c = data.customer;
      setForm({ name: c.name, phone: c.phone, address: c.address || "", area: c.area || "", notes: c.notes || "" });
    }
  }, [data]);

  if (loading && !data) return <Loading />;
  if (error) return <ErrorAlert error={error} onRetry={reload} />;
  if (!data) return null;
  const c = data.customer;

  return (
    <div className="space-y-6">
      <PageHeader backHref="/customers" title={c.name} description={`${formatPhone(c.phone)} · customer since ${formatDateTime(c.created_at)}`} />
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card title={`Orders (${data.orders.length})`}>
            {data.orders.length === 0 ? (
              <p className="text-sm text-slate-500">No orders yet.</p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {data.orders.map((o) => (
                  <li key={o.id}>
                    <Link href={`/orders/${o.id}`} className="flex items-center justify-between py-2 text-sm hover:underline">
                      <span>
                        <span className="font-medium">{o.order_number}</span>
                        <span className="ml-2 text-slate-500">{formatDateTime(o.created_at)}</span>
                      </span>
                      <span className="flex items-center gap-2">
                        <OrderStatusBadge status={o.status} />
                        <span className="font-medium">{formatBDT(o.total)}</span>
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card title="Profile">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Name"><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
              <Field label="Phone"><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
              <Field label="Area / city"><Input value={form.area} onChange={(e) => setForm({ ...form, area: e.target.value })} /></Field>
              <div className="sm:col-span-2"><Field label="Address"><Textarea value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} /></Field></div>
              <div className="sm:col-span-2"><Field label="Private notes"><Textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></Field></div>
            </div>
            <Button
              className="mt-4"
              loading={update.pending}
              onClick={async () => {
                if (await update.run(c.id, { ...form, address: form.address || null, area: form.area || null, notes: form.notes || null })) void reload();
              }}
            >
              Save
            </Button>
            <div className="mt-3"><ErrorAlert error={update.error} /></div>
          </Card>
        </div>

        <Card title="WhatsApp consent">
          <div className="space-y-2 text-sm">
            <div className="flex items-center justify-between"><span>Order updates</span><ConsentBadge status={data.transactional_consent} /></div>
            <div className="flex items-center justify-between"><span>Marketing</span><ConsentBadge status={data.marketing_consent} /></div>
          </div>
          <p className="mt-3 text-xs text-slate-500">
            Record consent only when the customer agreed to receive WhatsApp messages (e.g. in Messenger chat or by phone). Business-initiated
            templates require an opt-in. Customers who reply STOP are opted out automatically.
          </p>
          <div className="mt-4 space-y-2 border-t border-slate-100 pt-4">
            <Select value={consent.purpose} onChange={(e) => setConsent({ ...consent, purpose: e.target.value })}>
              <option value="transactional">Order updates</option>
              <option value="marketing">Marketing</option>
            </Select>
            <Select value={consent.status} onChange={(e) => setConsent({ ...consent, status: e.target.value })}>
              <option value="granted">Customer opted in</option>
              <option value="revoked">Customer opted out</option>
            </Select>
            <Select value={consent.source} onChange={(e) => setConsent({ ...consent, source: e.target.value })}>
              {SOURCES.map(([value, label]) => <option key={value} value={value}>Source: {label}</option>)}
            </Select>
            <Input placeholder="Note (optional)" maxLength={255} value={consent.note} onChange={(e) => setConsent({ ...consent, note: e.target.value })} />
            <Button
              variant="secondary"
              className="w-full"
              loading={recordConsent.pending}
              onClick={async () => {
                if (await recordConsent.run(c.id, { ...consent, note: consent.note || undefined })) {
                  setConsent({ ...consent, note: "" });
                  void reload();
                }
              }}
            >
              Record consent
            </Button>
            <ErrorAlert error={recordConsent.error} />
          </div>
          {data.consents.length > 0 && (
            <ul className="mt-4 space-y-2 border-t border-slate-100 pt-3 text-xs text-slate-600">
              {data.consents.map((x) => (
                <li key={x.id}>
                  <strong>{x.status}</strong> · {x.purpose} · via {x.source} · {formatDateTime(x.recorded_at)}
                  {x.note && <span className="block text-slate-500">{x.note}</span>}
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
