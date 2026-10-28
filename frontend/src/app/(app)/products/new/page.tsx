"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { ErrorAlert, PageHeader } from "@/components/ui/feedback";
import { Button, Card, Field, Input, Textarea } from "@/components/ui/primitives";
import { productApi } from "@/lib/api/endpoints";
import { useAction } from "@/lib/hooks";

interface VariantRow {
  size: string;
  color: string;
  stock: string;
  price: string;
}

export default function NewProductPage() {
  const router = useRouter();
  const [form, setForm] = useState({ name: "", sku: "", description: "", price: "", cost_price: "", stock: "0" });
  const [variants, setVariants] = useState<VariantRow[]>([]);
  const { run, pending, error } = useAction(productApi.create);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const product = await run({
      name: form.name,
      sku: form.sku,
      description: form.description || null,
      price: form.price,
      cost_price: form.cost_price || null,
      stock: Number(form.stock) || 0,
      variants: variants.map((v) => ({ size: v.size, color: v.color, stock: Number(v.stock) || 0, price: v.price || null })),
    });
    if (product) router.push(`/products/${product.id}`);
  }

  return (
    <form onSubmit={onSubmit} className="space-y-6">
      <PageHeader backHref="/products" title="New product" />
      <ErrorAlert error={error} />
      <Card title="Details">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Name">
            <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </Field>
          <Field label="SKU" hint="Your own unique code, e.g. KURTI-RED-01">
            <Input required value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} />
          </Field>
          <Field label="Selling price (৳)">
            <Input required type="number" min={0} step="0.01" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} />
          </Field>
          <Field label="Cost price (৳, optional)" hint="Used for estimated profit. Never shown to customers.">
            <Input type="number" min={0} step="0.01" value={form.cost_price} onChange={(e) => setForm({ ...form, cost_price: e.target.value })} />
          </Field>
          <div className="sm:col-span-2">
            <Field label="Description">
              <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </Field>
          </div>
        </div>
      </Card>

      <Card
        title="Sizes & colours"
        actions={
          <Button type="button" variant="secondary" onClick={() => setVariants([...variants, { size: "", color: "", stock: "0", price: "" }])}>
            + Add variant
          </Button>
        }
      >
        {variants.length === 0 ? (
          <Field label="Stock" hint="No sizes or colours? Just enter the stock. Add variants for size/colour tracking.">
            <Input type="number" min={0} value={form.stock} onChange={(e) => setForm({ ...form, stock: e.target.value })} />
          </Field>
        ) : (
          <div className="space-y-2">
            {variants.map((v, i) => (
              <div key={i} className="grid grid-cols-2 gap-2 sm:grid-cols-5">
                <Input placeholder="Size (M, L, 38…)" value={v.size} onChange={(e) => setVariants(variants.map((x, j) => (j === i ? { ...x, size: e.target.value } : x)))} />
                <Input placeholder="Colour" value={v.color} onChange={(e) => setVariants(variants.map((x, j) => (j === i ? { ...x, color: e.target.value } : x)))} />
                <Input type="number" min={0} placeholder="Stock" value={v.stock} onChange={(e) => setVariants(variants.map((x, j) => (j === i ? { ...x, stock: e.target.value } : x)))} />
                <Input type="number" min={0} step="0.01" placeholder="Price override" value={v.price} onChange={(e) => setVariants(variants.map((x, j) => (j === i ? { ...x, price: e.target.value } : x)))} />
                <Button type="button" variant="ghost" onClick={() => setVariants(variants.filter((_, j) => j !== i))}>
                  Remove
                </Button>
              </div>
            ))}
          </div>
        )}
      </Card>

      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={() => router.back()}>
          Cancel
        </Button>
        <Button type="submit" loading={pending}>
          Save product
        </Button>
      </div>
    </form>
  );
}
