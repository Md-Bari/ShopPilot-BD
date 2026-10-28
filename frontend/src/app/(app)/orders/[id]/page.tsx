"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { NotificationPanel } from "@/components/orders/NotificationPanel";
import { OrderStatusBadge, PaymentStatusBadge } from "@/components/orders/StatusBadge";
import { ErrorAlert, Loading, PageHeader } from "@/components/ui/feedback";
import { Button, Card, Field, Input, Select } from "@/components/ui/primitives";
import { businessApi, orderApi } from "@/lib/api/endpoints";
import { formatBDT, formatDateTime, formatPhone, toNumber } from "@/lib/format";
import { useAction, useApi } from "@/lib/hooks";
import { useT } from "@/lib/i18n";

export default function OrderDetailPage() {
  const { t } = useT();
  const id = Number(useParams<{ id: string }>().id);
  const { data: order, error, loading, reload, setData } = useApi(() => orderApi.get(id), [id]);
  const methods = useApi(() => businessApi.paymentMethods(true), []);

  const [statusNote, setStatusNote] = useState("");
  const statusAction = useAction(orderApi.changeStatus);
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("");
  const [reference, setReference] = useState("");
  const paymentAction = useAction(orderApi.recordPayment);

  if (loading && !order) return <Loading />;
  if (error) return <ErrorAlert error={error} onRetry={reload} />;
  if (!order) return null;

  const due = toNumber(order.total) - toNumber(order.amount_paid);

  async function changeStatus(status: string) {
    if ((status === "cancelled" || status === "returned") && !window.confirm(`Mark this order as ${status}? Stock will be returned.`)) return;
    const updated = await statusAction.run(order!.id, status, statusNote);
    if (updated) {
      setData(updated);
      setStatusNote("");
    }
  }

  async function recordPayment() {
    const updated = await paymentAction.run(order!.id, { amount, method_code: method || undefined, reference: reference || undefined });
    if (updated) {
      setData(updated);
      setAmount("");
      setReference("");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        backHref="/orders"
        title={`Order ${order.order_number}`}
        description={`Placed ${formatDateTime(order.created_at)}`}
        actions={
          <div className="flex items-center gap-2">
            <OrderStatusBadge status={order.status} />
            <PaymentStatusBadge status={order.payment_status} />
          </div>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card title="Items">
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th className="py-2">Item</th>
                  <th className="py-2 text-right">Qty</th>
                  <th className="py-2 text-right">Unit</th>
                  <th className="py-2 text-right">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {order.items.map((item) => (
                  <tr key={item.id}>
                    <td className="py-2">
                      {item.product_name} <span className="text-slate-500">({item.variant_label})</span>
                      {item.sku && <span className="block text-xs text-slate-400">{item.sku}</span>}
                    </td>
                    <td className="py-2 text-right">{item.quantity}</td>
                    <td className="py-2 text-right">{formatBDT(item.unit_price)}</td>
                    <td className="py-2 text-right">{formatBDT(item.line_total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <dl className="mt-4 ml-auto max-w-xs space-y-1 text-sm">
              <div className="flex justify-between"><dt>{t("Subtotal")}</dt><dd>{formatBDT(order.subtotal)}</dd></div>
              <div className="flex justify-between"><dt>{t("Delivery charge")}</dt><dd>{formatBDT(order.delivery_charge)}</dd></div>
              <div className="flex justify-between"><dt>{t("Discount")}</dt><dd>− {formatBDT(order.discount)}</dd></div>
              <div className="flex justify-between font-semibold"><dt>{t("Total")}</dt><dd>{formatBDT(order.total)}</dd></div>
              <div className="flex justify-between text-emerald-700"><dt>Paid</dt><dd>{formatBDT(order.amount_paid)}</dd></div>
              <div className="flex justify-between font-medium"><dt>Due</dt><dd>{formatBDT(due)}</dd></div>
            </dl>
          </Card>

          <Card title="Update status">
            {order.allowed_next_statuses.length === 0 ? (
              <p className="text-sm text-slate-500">This order is closed ({t(order.status)}).</p>
            ) : (
              <div className="space-y-3">
                <Input placeholder="Optional note (e.g. courier tracking number)" value={statusNote} maxLength={500} onChange={(e) => setStatusNote(e.target.value)} />
                <div className="flex flex-wrap gap-2">
                  {order.allowed_next_statuses.map((s) => (
                    <Button
                      key={s}
                      variant={s === "cancelled" || s === "returned" ? "danger" : "primary"}
                      loading={statusAction.pending}
                      onClick={() => changeStatus(s)}
                    >
                      Mark {t(s)}
                    </Button>
                  ))}
                </div>
                <ErrorAlert error={statusAction.error} />
              </div>
            )}
          </Card>

          <Card title={t("Order history")}>
            <ol className="relative space-y-4 border-l border-slate-200 pl-4">
              {order.status_history.map((h) => (
                <li key={h.id} className="text-sm">
                  <span className="absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full bg-brand-500" />
                  <div className="flex flex-wrap items-center gap-2">
                    <OrderStatusBadge status={h.to_status} />
                    <span className="text-slate-500">
                      {formatDateTime(h.created_at)} · {h.changed_by_name ?? "System"}
                    </span>
                  </div>
                  {h.note && <p className="mt-1 text-slate-600">{h.note}</p>}
                </li>
              ))}
            </ol>
          </Card>
        </div>

        <div className="space-y-6">
          <Card title={t("Customer")}>
            <p className="font-medium">
              <Link href={`/customers/${order.customer.id}`} className="hover:underline">
                {order.customer.name}
              </Link>
            </p>
            <p className="text-sm text-slate-600">{formatPhone(order.customer.phone)}</p>
            {order.shipping_address && <p className="mt-2 whitespace-pre-line text-sm text-slate-600">{order.shipping_address}</p>}
            {order.note && <p className="mt-2 rounded bg-amber-50 p-2 text-sm text-amber-900">{order.note}</p>}
          </Card>

          <NotificationPanel order={order} onSent={reload} />

          <Card title="Payments">
            {order.payments.length > 0 && (
              <ul className="mb-3 divide-y divide-slate-100 text-sm">
                {order.payments.map((p) => (
                  <li key={p.id} className="flex justify-between py-1.5">
                    <span>
                      {p.method_code} {p.reference && <span className="text-xs text-slate-500">· {p.reference}</span>}
                      <span className="block text-xs text-slate-400">{formatDateTime(p.created_at)}</span>
                    </span>
                    <span className="font-medium">{formatBDT(p.amount)}</span>
                  </li>
                ))}
              </ul>
            )}
            {due > 0 && order.status !== "cancelled" ? (
              <div className="space-y-2">
                <Field label={`Record payment (due ${formatBDT(due)})`}>
                  <Input type="number" min={1} step="0.01" max={due} value={amount} onChange={(e) => setAmount(e.target.value)} placeholder={String(due)} />
                </Field>
                <Select value={method} onChange={(e) => setMethod(e.target.value)}>
                  <option value="">Order method ({order.payment_method_code})</option>
                  {methods.data?.map((m) => (
                    <option key={m.code} value={m.code}>
                      {m.label}
                    </option>
                  ))}
                </Select>
                <Input placeholder="Transaction ID (optional)" value={reference} onChange={(e) => setReference(e.target.value)} />
                <Button className="w-full" variant="secondary" onClick={recordPayment} loading={paymentAction.pending} disabled={!amount}>
                  Record payment
                </Button>
                <ErrorAlert error={paymentAction.error} />
              </div>
            ) : (
              <p className="text-sm text-slate-500">{order.status === "cancelled" ? "Order cancelled." : "Fully paid."}</p>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
