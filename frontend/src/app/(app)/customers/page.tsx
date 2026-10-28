"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { EmptyState, ErrorAlert, Loading, Modal, PageHeader, Pagination } from "@/components/ui/feedback";
import { Button, Field, Input, Textarea } from "@/components/ui/primitives";
import { customerApi } from "@/lib/api/endpoints";
import { formatDateTime, formatPhone } from "@/lib/format";
import { useAction, useApi, useDebounced } from "@/lib/hooks";
import { useT } from "@/lib/i18n";

export default function CustomersPage() {
  const { t } = useT();
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const search = useDebounced(q);
  const { data, error, loading, reload } = useApi(() => customerApi.list({ q: search, page, page_size: 20 }), [search, page]);

  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", phone: "", address: "" });
  const create = useAction(customerApi.create);
  const duplicateId = create.error?.code === "duplicate_customer" ? Number(create.error.details.existing_customer_id) : null;

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    if (await create.run({ name: form.name, phone: form.phone, address: form.address || null })) {
      setOpen(false);
      setForm({ name: "", phone: "", address: "" });
      void reload();
    }
  }

  return (
    <div>
      <PageHeader title={t("Customers")} actions={<Button onClick={() => setOpen(true)}>+ {t("New customer")}</Button>} />
      <Input className="mb-4" placeholder="Search by name or phone" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />

      {error && <ErrorAlert error={error} onRetry={reload} />}
      {loading && !data ? (
        <Loading />
      ) : data && data.items.length === 0 ? (
        <EmptyState title="No customers found" description="Customers are created automatically when you place an order." />
      ) : data ? (
        <>
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">{t("Phone")}</th>
                  <th className="hidden px-4 py-3 sm:table-cell">Orders</th>
                  <th className="hidden px-4 py-3 md:table-cell">Last order</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <Link href={`/customers/${c.id}`} className="font-medium text-brand-700 hover:underline">
                        {c.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3">{formatPhone(c.phone)}</td>
                    <td className="hidden px-4 py-3 sm:table-cell">{c.order_count}</td>
                    <td className="hidden px-4 py-3 text-slate-500 md:table-cell">{formatDateTime(c.last_order_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={data.page} pageSize={data.page_size} total={data.total} onChange={setPage} />
        </>
      ) : null}

      <Modal
        open={open}
        title={t("New customer")}
        onClose={() => setOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>{t("Cancel")}</Button>
            <Button form="new-customer" type="submit" loading={create.pending}>{t("Save")}</Button>
          </>
        }
      >
        <form id="new-customer" onSubmit={onCreate} className="space-y-3">
          <ErrorAlert error={create.error} />
          {duplicateId && (
            <Link href={`/customers/${duplicateId}`} className="text-sm font-medium text-brand-700 underline">
              Open the existing customer
            </Link>
          )}
          <Field label="Name"><Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
          <Field label={t("Phone")} hint="Saved in international format (+880…)."><Input required value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
          <Field label={t("Address")}><Textarea value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} /></Field>
        </form>
      </Modal>
    </div>
  );
}
