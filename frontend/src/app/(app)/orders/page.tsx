"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { ORDER_STATUSES, OrderStatusBadge, PaymentStatusBadge } from "@/components/orders/StatusBadge";
import { EmptyState, ErrorAlert, Loading, PageHeader, Pagination } from "@/components/ui/feedback";
import { Button, Input, Select } from "@/components/ui/primitives";
import { orderApi } from "@/lib/api/endpoints";
import { formatBDT, formatDateTime, formatPhone } from "@/lib/format";
import { useApi, useDebounced } from "@/lib/hooks";
import { useT } from "@/lib/i18n";

function OrdersList() {
  const { t } = useT();
  const router = useRouter();
  const params = useSearchParams();
  const [q, setQ] = useState(params.get("q") || "");
  const [status, setStatus] = useState(params.get("status") || "");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);
  const search = useDebounced(q);

  const { data, error, loading, reload } = useApi(
    () => orderApi.list({ q: search, status, date_from: dateFrom, date_to: dateTo, page, page_size: 20 }),
    [search, status, dateFrom, dateTo, page],
  );

  return (
    <div>
      <PageHeader
        title={t("Orders")}
        actions={
          <Link href="/orders/new">
            <Button>+ {t("New order")}</Button>
          </Link>
        }
      />
      <div className="mb-4 grid gap-2 sm:grid-cols-4">
        <Input placeholder="Order #, customer name or phone" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
        <Select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
          <option value="">All statuses</option>
          {ORDER_STATUSES.map((s) => (
            <option key={s} value={s}>
              {t(s)}
            </option>
          ))}
        </Select>
        <Input type="date" aria-label="From date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setPage(1); }} />
        <Input type="date" aria-label="To date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setPage(1); }} />
      </div>

      {error && <ErrorAlert error={error} onRetry={reload} />}
      {loading && !data ? (
        <Loading />
      ) : data && data.items.length === 0 ? (
        <EmptyState
          title="No orders found"
          description={q || status ? "Try a different search or filter." : "Orders you create will appear here."}
          action={<Link href="/orders/new"><Button>{t("New order")}</Button></Link>}
        />
      ) : data ? (
        <>
          <div className="hidden overflow-hidden rounded-xl border border-slate-200 bg-white md:block">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3">Order</th>
                  <th className="px-4 py-3">{t("Customer")}</th>
                  <th className="px-4 py-3">{t("Status")}</th>
                  <th className="px-4 py-3">Payment</th>
                  <th className="px-4 py-3 text-right">{t("Total")}</th>
                  <th className="px-4 py-3">Placed</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.map((o) => (
                  <tr key={o.id} className="cursor-pointer hover:bg-slate-50" onClick={() => router.push(`/orders/${o.id}`)}>
                    <td className="px-4 py-3 font-medium text-brand-700">{o.order_number}</td>
                    <td className="px-4 py-3">
                      {o.customer.name}
                      <span className="block text-xs text-slate-500">{formatPhone(o.customer.phone)}</span>
                    </td>
                    <td className="px-4 py-3"><OrderStatusBadge status={o.status} /></td>
                    <td className="px-4 py-3"><PaymentStatusBadge status={o.payment_status} /></td>
                    <td className="px-4 py-3 text-right font-medium">{formatBDT(o.total)}</td>
                    <td className="px-4 py-3 text-slate-500">{formatDateTime(o.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ul className="space-y-2 md:hidden">
            {data.items.map((o) => (
              <li key={o.id}>
                <Link href={`/orders/${o.id}`} className="block rounded-xl border border-slate-200 bg-white p-3">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-brand-700">{o.order_number}</span>
                    <OrderStatusBadge status={o.status} />
                  </div>
                  <div className="mt-1 flex items-center justify-between text-sm">
                    <span>{o.customer.name}</span>
                    <span className="font-semibold">{formatBDT(o.total)}</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">{formatDateTime(o.created_at)}</p>
                </Link>
              </li>
            ))}
          </ul>
          <Pagination page={data.page} pageSize={data.page_size} total={data.total} onChange={setPage} />
        </>
      ) : null}
    </div>
  );
}

export default function OrdersPage() {
  return (
    <Suspense fallback={<Loading />}>
      <OrdersList />
    </Suspense>
  );
}
