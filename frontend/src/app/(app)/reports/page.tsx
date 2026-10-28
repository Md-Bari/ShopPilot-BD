"use client";

import { useState } from "react";
import { OrderStatusBadge } from "@/components/orders/StatusBadge";
import { ErrorAlert, Loading, PageHeader, StatCard } from "@/components/ui/feedback";
import { Card, Field, Input } from "@/components/ui/primitives";
import { reportApi } from "@/lib/api/endpoints";
import { dhakaToday, formatBDT, formatDate, toNumber } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import { useT } from "@/lib/i18n";

export default function ReportsPage() {
  const { t } = useT();
  const [from, setFrom] = useState(dhakaToday(-29));
  const [to, setTo] = useState(dhakaToday());
  const { data, error, loading, reload } = useApi(() => reportApi.sales(from, to), [from, to]);
  const maxDaily = Math.max(1, ...(data?.daily.map((d) => toNumber(d.gross_order_value)) ?? [1]));

  return (
    <div className="space-y-6">
      <PageHeader title={t("Reports")} description="All dates use Asia/Dhaka time." />
      <div className="grid max-w-md grid-cols-2 gap-3">
        <Field label="From"><Input type="date" value={from} max={to} onChange={(e) => setFrom(e.target.value)} /></Field>
        <Field label="To"><Input type="date" value={to} min={from} onChange={(e) => setTo(e.target.value)} /></Field>
      </div>
      {error && <ErrorAlert error={error} onRetry={reload} />}
      {loading && !data ? (
        <Loading />
      ) : data ? (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatCard label="Orders placed" value={data.orders} />
            <StatCard label={t("Gross order value")} value={formatBDT(data.gross_order_value)} hint="Placed orders, excluding cancelled" />
            <StatCard label={t("Collected revenue")} value={formatBDT(data.collected_revenue)} hint="Payments actually received" />
            <StatCard label={t("Estimated profit")} value={formatBDT(data.estimated_profit)} hint="Delivered orders, after product cost" />
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <Card title="Daily gross order value" className="lg:col-span-2">
              <div className="flex h-48 items-end gap-1 overflow-x-auto">
                {data.daily.map((d) => (
                  <div key={d.date} className="group flex min-w-[10px] flex-1 flex-col items-center justify-end" title={`${formatDate(d.date)}: ${d.orders} orders, ${formatBDT(d.gross_order_value)}`}>
                    <div className="w-full rounded-t bg-brand-500 group-hover:bg-brand-700" style={{ height: `${(toNumber(d.gross_order_value) / maxDaily) * 100}%`, minHeight: d.orders ? 2 : 0 }} />
                  </div>
                ))}
              </div>
              <div className="mt-2 flex justify-between text-xs text-slate-500">
                <span>{formatDate(data.date_from)}</span>
                <span>{formatDate(data.date_to)}</span>
              </div>
            </Card>
            <Card title="By status">
              <ul className="space-y-2 text-sm">
                {Object.entries(data.by_status).map(([status, v]) => (
                  <li key={status} className="flex items-center justify-between">
                    <OrderStatusBadge status={status} />
                    <span>
                      {v.count} · {formatBDT(v.value)}
                    </span>
                  </li>
                ))}
              </ul>
            </Card>
          </div>

          <Card title="Top products (by quantity, excluding cancelled)">
            {data.top_products.length === 0 ? (
              <p className="text-sm text-slate-500">No sales in this period.</p>
            ) : (
              <table className="w-full text-sm">
                <thead><tr><th className="py-2">Product</th><th className="py-2 text-right">Qty</th><th className="py-2 text-right">Value</th></tr></thead>
                <tbody className="divide-y divide-slate-100">
                  {data.top_products.map((p) => (
                    <tr key={p.product_name}><td className="py-2">{p.product_name}</td><td className="py-2 text-right">{p.quantity}</td><td className="py-2 text-right">{formatBDT(p.value)}</td></tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </>
      ) : null}
    </div>
  );
}
