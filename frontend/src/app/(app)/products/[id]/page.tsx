"use client";

import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ErrorAlert, Loading, PageHeader } from "@/components/ui/feedback";
import { Badge, Button, Card, Field, Input, Textarea } from "@/components/ui/primitives";
import { productApi } from "@/lib/api/endpoints";
import { formatBDT } from "@/lib/format";
import { useAction, useApi } from "@/lib/hooks";
import type { Product, Variant } from "@/lib/types";

function VariantRow({ product, variant, onChange }: { product: Product; variant: Variant; onChange: () => void }) {
  const [stock, setStock] = useState(String(variant.stock));
  const [threshold, setThreshold] = useState(String(variant.low_stock_threshold));
  const save = useAction(() => productApi.updateVariant(product.id, variant.id, { stock: Number(stock), low_stock_threshold: Number(threshold) }));
  const remove = useAction(() => productApi.deleteVariant(product.id, variant.id));
  const dirty = stock !== String(variant.stock) || threshold !== String(variant.low_stock_threshold);

  return (
    <tr>
      <td className="py-2">{variant.label}</td>
      <td className="py-2">{formatBDT(variant.effective_price)}</td>
      <td className="w-24 py-2"><Input type="number" min={0} value={stock} onChange={(e) => setStock(e.target.value)} /></td>
      <td className="w-24 py-2"><Input type="number" min={0} value={threshold} onChange={(e) => setThreshold(e.target.value)} /></td>
      <td className="py-2 text-right">
        <div className="flex justify-end gap-1">
          {dirty && <Button variant="secondary" loading={save.pending} onClick={async () => { if (await save.run()) onChange(); }}>Save</Button>}
          {product.variants.length > 1 && (
            <Button variant="ghost" loading={remove.pending} onClick={async () => { if (window.confirm("Remove this variant?") && (await remove.run())) onChange(); }}>✕</Button>
          )}
        </div>
        {(save.error || remove.error) && <p className="text-xs text-rose-600">{(save.error || remove.error)?.message}</p>}
      </td>
    </tr>
  );
}

export default function ProductDetailPage() {
  const id = Number(useParams<{ id: string }>().id);
  const { data: product, error, loading, reload, setData } = useApi(() => productApi.get(id), [id]);
  const [form, setForm] = useState({ name: "", sku: "", description: "", price: "", cost_price: "" });
  const [saved, setSaved] = useState(false);
  const [newVariant, setNewVariant] = useState({ size: "", color: "", stock: "0" });
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (product)
      setForm({
        name: product.name,
        sku: product.sku,
        description: product.description || "",
        price: String(product.price),
        cost_price: product.cost_price ? String(product.cost_price) : "",
      });
  }, [product]);

  const update = useAction(productApi.update);
  const archive = useAction((p: Product) => (p.status === "active" ? productApi.archive(p.id) : productApi.unarchive(p.id)));
  const upload = useAction(productApi.uploadImage);
  const addVariant = useAction(productApi.addVariant);

  if (loading && !product) return <Loading />;
  if (error) return <ErrorAlert error={error} onRetry={reload} />;
  if (!product) return null;

  async function save() {
    setSaved(false);
    const result = await update.run(product!.id, {
      name: form.name,
      sku: form.sku,
      description: form.description || null,
      price: form.price,
      cost_price: form.cost_price || null,
    });
    if (result) {
      setData(result);
      setSaved(true);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        backHref="/products"
        title={product.name}
        description={`SKU ${product.sku}`}
        actions={
          <>
            {product.status === "archived" && <Badge tone="red">archived</Badge>}
            <Button variant={product.status === "active" ? "danger" : "secondary"} loading={archive.pending} onClick={async () => { const p = await archive.run(product); if (p) setData(p); }}>
              {product.status === "active" ? "Archive" : "Restore"}
            </Button>
          </>
        }
      />
      <ErrorAlert error={archive.error} />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Details" className="lg:col-span-2">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Name"><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
            <Field label="SKU"><Input value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} /></Field>
            <Field label="Selling price (৳)"><Input type="number" min={0} step="0.01" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} /></Field>
            <Field label="Cost price (৳)"><Input type="number" min={0} step="0.01" value={form.cost_price} onChange={(e) => setForm({ ...form, cost_price: e.target.value })} /></Field>
            <div className="sm:col-span-2">
              <Field label="Description"><Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></Field>
            </div>
          </div>
          <div className="mt-4 flex items-center gap-3">
            <Button onClick={save} loading={update.pending}>Save changes</Button>
            {saved && <span className="text-sm text-emerald-700">Saved.</span>}
          </div>
          <div className="mt-3"><ErrorAlert error={update.error} /></div>
        </Card>

        <Card title="Image">
          <div className="aspect-square overflow-hidden rounded-lg bg-slate-100">
            {product.image_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={product.image_url} alt={product.name} className="h-full w-full object-cover" />
            ) : (
              <div className="flex h-full items-center justify-center text-5xl text-slate-300">👗</div>
            )}
          </div>
          <input
            ref={fileInput}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (file) {
                const p = await upload.run(product.id, file);
                if (p) setData(p);
              }
              e.target.value = "";
            }}
          />
          <Button variant="secondary" className="mt-3 w-full" loading={upload.pending} onClick={() => fileInput.current?.click()}>
            Upload image
          </Button>
          <p className="mt-1 text-xs text-slate-500">JPEG, PNG or WebP, up to 3 MB.</p>
          <div className="mt-2"><ErrorAlert error={upload.error} /></div>
        </Card>
      </div>

      <Card title="Variants & stock">
        <table className="w-full text-sm">
          <thead>
            <tr>
              <th className="py-2">Variant</th>
              <th className="py-2">Price</th>
              <th className="py-2">Stock</th>
              <th className="py-2">Low-stock alert at</th>
              <th />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {product.variants.map((v) => (
              <VariantRow key={`${v.id}-${v.stock}-${v.low_stock_threshold}`} product={product} variant={v} onChange={reload} />
            ))}
          </tbody>
        </table>
        <div className="mt-4 grid grid-cols-2 gap-2 border-t border-slate-100 pt-4 sm:grid-cols-4">
          <Input placeholder="Size" value={newVariant.size} onChange={(e) => setNewVariant({ ...newVariant, size: e.target.value })} />
          <Input placeholder="Colour" value={newVariant.color} onChange={(e) => setNewVariant({ ...newVariant, color: e.target.value })} />
          <Input type="number" min={0} placeholder="Stock" value={newVariant.stock} onChange={(e) => setNewVariant({ ...newVariant, stock: e.target.value })} />
          <Button
            variant="secondary"
            loading={addVariant.pending}
            onClick={async () => {
              if (await addVariant.run(product.id, { size: newVariant.size, color: newVariant.color, stock: Number(newVariant.stock) || 0 })) {
                setNewVariant({ size: "", color: "", stock: "0" });
                void reload();
              }
            }}
          >
            + Add variant
          </Button>
        </div>
        <div className="mt-2"><ErrorAlert error={addVariant.error} /></div>
      </Card>
    </div>
  );
}
