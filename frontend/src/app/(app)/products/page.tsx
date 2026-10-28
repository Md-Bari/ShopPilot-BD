"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { EmptyState, ErrorAlert, Loading, PageHeader, Pagination, SuccessAlert } from "@/components/ui/feedback";
import { Badge, Button, Input, Select } from "@/components/ui/primitives";
import { productApi } from "@/lib/api/endpoints";
import { formatBDT } from "@/lib/format";
import { useAction, useApi, useDebounced } from "@/lib/hooks";
import { useT } from "@/lib/i18n";
import type { ImportSummary } from "@/lib/types";

export default function ProductsPage() {
  const { t } = useT();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("active");
  const [page, setPage] = useState(1);
  const search = useDebounced(q);
  const { data, error, loading, reload } = useApi(() => productApi.list({ q: search, status, page, page_size: 20 }), [search, status, page]);

  const fileInput = useRef<HTMLInputElement>(null);
  const [summary, setSummary] = useState<ImportSummary | null>(null);
  const importAction = useAction(productApi.importCsv);

  async function onImport(file: File | undefined) {
    if (!file) return;
    const result = await importAction.run(file);
    if (result) {
      setSummary(result);
      void reload();
    }
    if (fileInput.current) fileInput.current.value = "";
  }

  return (
    <div>
      <PageHeader
        title={t("Products")}
        actions={
          <>
            <a href={productApi.exportUrl} download>
              <Button variant="secondary">Export CSV</Button>
            </a>
            <Button variant="secondary" loading={importAction.pending} onClick={() => fileInput.current?.click()}>
              Import CSV
            </Button>
            <input ref={fileInput} type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => onImport(e.target.files?.[0])} />
            <Link href="/products/new">
              <Button>+ {t("New product")}</Button>
            </Link>
          </>
        }
      />

      <ErrorAlert error={importAction.error} />
      {summary && (
        <div className="mb-4">
          <SuccessAlert>
            Imported: {summary.products_created} new products, {summary.products_updated} updated, {summary.variants_created} new variants,{" "}
            {summary.variants_updated} variants updated.
            {summary.errors.length > 0 && (
              <ul className="mt-2 list-disc pl-5 text-rose-700">
                {summary.errors.slice(0, 10).map((e) => (
                  <li key={e.row}>
                    Row {e.row}: {e.message}
                  </li>
                ))}
              </ul>
            )}
          </SuccessAlert>
        </div>
      )}

      <div className="mb-4 grid gap-2 sm:grid-cols-3">
        <Input className="sm:col-span-2" placeholder="Search by name or SKU" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
        <Select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
          <option value="active">Active</option>
          <option value="archived">Archived</option>
          <option value="">All</option>
        </Select>
      </div>

      {error && <ErrorAlert error={error} onRetry={reload} />}
      {loading && !data ? (
        <Loading />
      ) : data && data.items.length === 0 ? (
        <EmptyState
          title="No products yet"
          description="Add products manually or import a CSV with columns: name, sku, price, size, color, stock."
          action={<Link href="/products/new"><Button>{t("New product")}</Button></Link>}
        />
      ) : data ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {data.items.map((p) => {
              const low = p.variants.some((v) => v.is_active && v.stock <= v.low_stock_threshold);
              return (
                <Link key={p.id} href={`/products/${p.id}`} className="flex gap-3 rounded-xl border border-slate-200 bg-white p-3 hover:border-brand-500">
                  <div className="h-20 w-20 shrink-0 overflow-hidden rounded-lg bg-slate-100">
                    {p.image_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={p.image_url} alt={p.name} className="h-full w-full object-cover" />
                    ) : (
                      <div className="flex h-full items-center justify-center text-2xl text-slate-300">👗</div>
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{p.name}</p>
                    <p className="text-xs text-slate-500">{p.sku}</p>
                    <p className="mt-1 font-semibold">{formatBDT(p.price)}</p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      <Badge tone={low ? "amber" : "gray"}>{p.total_stock} in stock</Badge>
                      {p.variants.length > 1 && <Badge>{p.variants.length} variants</Badge>}
                      {p.status === "archived" && <Badge tone="red">archived</Badge>}
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
          <Pagination page={data.page} pageSize={data.page_size} total={data.total} onChange={setPage} />
        </>
      ) : null}
    </div>
  );
}
