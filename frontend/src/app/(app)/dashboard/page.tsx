"use client";

import Link from "next/link";
import { OrderStatusBadge } from "@/components/orders/StatusBadge";
import { EmptyState, ErrorAlert, Loading, PageHeader, StatCard } from "@/components/ui/feedback";
import { Button, Card } from "@/components/ui/primitives";
import { reportApi } from "@/lib/api/endpoints";
import { formatBDT, formatDate, formatDateTime } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import { useT } from "@/lib/i18n";

export default function DashboardPage() {
  const { t } = useT();
  const { data, error, loading, reload } = useApi(reportApi.dashboard);

  if (loading && !data) return <Loading />;
  if (error) return <ErrorAlert error={error} onRetry={reload} />;
  if (!data) return null;

  const counts = data.last_30_days_status_counts;
  const wa = data.whatsapp;

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("Dashboard")}
        description={`Today, ${formatDate(data.date)} (Asia/Dhaka)`}
        actions={
          <Link href="/orders/new">
            <Button>+ {t("New order")}</Button>
          </Link>
        }
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label={t("Today's orders")} value={data.today.orders} hint={`${formatBDT(data.today.gross_order_value)} placed`} />
        <StatCard
          label={t("Pending confirmations")}
          value={data.pending_confirmations}
          tone={data.pending_confirmations > 0 ? "warn" : "default"}
          hint="Orders waiting for you to confirm"
        />
        <StatCard label={t("Collected revenue")} value={formatBDT(data.today.collected_revenue)} hint="Payments recorded today" />
        <StatCard label="WhatsApp delivery" value={wa.delivery_rate === null ? "—" : `${Math.round(wa.delivery_rate * 100)}%`} hint={`${wa.outbound_total} sent · ${wa.inbound_total} received (30d)`} />
      </div>

      <Card title="This month">
        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <p className="text-xs uppercase text-slate-500">{t("Gross order value")}</p>
            <p className="text-xl font-semibold">{formatBDT(data.month_to_date.gross_order_value)}</p>
            <p className="text-xs text-slate-500">{data.month_to_date.orders} orders placed, excluding cancelled. Not all of this is sold yet.</p>
          </div>
          <div>
            <p className="text-xs uppercase text-slate-500">{t("Collected revenue")}</p>
            <p className="text-xl font-semibold text-emerald-700">{formatBDT(data.month_to_date.collected_revenue)}</p>
            <p className="text-xs text-slate-500">Money actually received (COD collected, bKash, etc.).</p>
          </div>
          <div>
            <p className="text-xs uppercase text-slate-500">{t("Estimated profit")}</p>
            <p className="text-xl font-semibold">{formatBDT(data.month_to_date.estimated_profit)}</p>
            <p className="text-xs text-slate-500">Delivered orders: sale price − discount − product cost.</p>
          </div>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Orders by status (30 days)" className="lg:col-span-1">
          <ul className="space-y-2">
            {Object.entries(counts).map(([status, count]) => (
              <li key={status} className="flex items-center justify-between text-sm">
                <Link href={`/orders?status=${status}`}>
                  <OrderStatusBadge status={status} />
                </Link>
                <span className="font-medium">{count}</span>
              </li>
            ))}
          </ul>
        </Card>

        <Card title={t("Low stock")}>
          {data.low_stock.length === 0 ? (
            <p className="text-sm text-slate-500">All products are well stocked.</p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {data.low_stock.map((item) => (
                <li key={item.variant_id} className="flex items-center justify-between py-2 text-sm">
                  <Link href={`/products/${item.product_id}`} className="hover:underline">
                    {item.product_name} <span className="text-slate-500">({item.variant_label})</span>
                  </Link>
                  <span className={item.stock === 0 ? "font-semibold text-rose-600" : "font-semibold text-amber-600"}>{item.stock} left</span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title={t("Recent activity")}>
          {data.recent_activity.length === 0 ? (
            <EmptyState title="No activity yet" description="Create your first order to get started." />
          ) : (
            <ul className="divide-y divide-slate-100">
              {data.recent_activity.map((a, i) => (
                <li key={i} className="py-2 text-sm">
                  <Link
                    href={a.type === "order" ? `/orders/${a.order_id}` : `/inbox?c=${a.conversation_id}`}
                    className="flex items-start justify-between gap-2 hover:underline"
                  >
                    <span>
                      <span className="mr-1">{a.type === "order" ? "🧾" : "💬"}</span>
                      <span className="font-medium">{a.title}</span>
                      <span className="block truncate text-xs text-slate-500">{a.subtitle}</span>
                    </span>
                    <span className="shrink-0 text-xs text-slate-400">{formatDateTime(a.at)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card title={t("WhatsApp messages") + " (30 days)"}>
        <div className="flex flex-wrap gap-4 text-sm">
          {Object.keys(wa.by_status).length === 0 ? (
            <p className="text-slate-500">No messages sent yet.</p>
          ) : (
            Object.entries(wa.by_status).map(([status, count]) => (
              <span key={status} className="rounded-lg bg-slate-100 px-3 py-1.5">
                {status}: <strong>{count}</strong>
              </span>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}
