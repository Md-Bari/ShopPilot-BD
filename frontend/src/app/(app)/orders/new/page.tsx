"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { ErrorAlert, PageHeader } from "@/components/ui/feedback";
import { Button, Card, Field, Input, Select, Textarea } from "@/components/ui/primitives";
import { businessApi, customerApi, orderApi, productApi } from "@/lib/api/endpoints";
import { formatBDT, formatPhone, toNumber } from "@/lib/format";
import { useAction, useApi, useDebounced } from "@/lib/hooks";
import { useT } from "@/lib/i18n";
import type { Customer, Product, Variant } from "@/lib/types";

interface Line {
  variant: Variant;
  product: Product;
  quantity: number;
  unitPrice: string;
}

export default function NewOrderPage() {
  const { t } = useT();
  const router = useRouter();

  // customer
  const [phone, setPhone] = useState("");
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [existing, setExisting] = useState<Customer | null>(null);
  const debouncedPhone = useDebounced(phone, 400);

  useEffect(() => {
    setExisting(null);
    if (debouncedPhone.replace(/\D/g, "").length < 10) return;
    customerApi
      .checkDuplicate(debouncedPhone)
      .then((res) => {
        setExisting(res.duplicate);
        if (res.duplicate) {
          setName(res.duplicate.name);
          if (res.duplicate.address) setAddress(res.duplicate.address);
        }
      })
      .catch(() => setExisting(null));
  }, [debouncedPhone]);

  // products
  const [productQuery, setProductQuery] = useState("");
  const debouncedQuery = useDebounced(productQuery);
  const products = useApi(() => productApi.list({ q: debouncedQuery, status: "active", page_size: 10 }), [debouncedQuery]);
  const paymentMethods = useApi(() => businessApi.paymentMethods(true), []);
  const business = useApi(businessApi.current, []);

  const [lines, setLines] = useState<Line[]>([]);
  const [deliveryCharge, setDeliveryCharge] = useState<string | null>(null);
  const [discount, setDiscount] = useState("0");
  const [paymentMethod, setPaymentMethod] = useState("cod");
  const [note, setNote] = useState("");

  const delivery = deliveryCharge ?? String(business.data?.default_delivery_charge ?? 0);

  function addVariant(product: Product, variant: Variant) {
    setLines((prev) =>
      prev.some((l) => l.variant.id === variant.id)
        ? prev.map((l) => (l.variant.id === variant.id ? { ...l, quantity: Math.min(l.quantity + 1, variant.stock) } : l))
        : [...prev, { product, variant, quantity: 1, unitPrice: String(toNumber(variant.effective_price)) }],
    );
  }

  const subtotal = useMemo(() => lines.reduce((sum, l) => sum + toNumber(l.unitPrice) * l.quantity, 0), [lines]);
  const total = subtotal + toNumber(delivery) - toNumber(discount);

  const { run, pending, error } = useAction(orderApi.create);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const order = await run({
      ...(existing ? { customer_id: existing.id } : { new_customer: { name, phone, address: address || null } }),
      items: lines.map((l) => ({
        variant_id: l.variant.id,
        quantity: l.quantity,
        unit_price: toNumber(l.unitPrice) !== toNumber(l.variant.effective_price) ? l.unitPrice : null,
      })),
      delivery_charge: delivery || "0",
      discount: discount || "0",
      payment_method_code: paymentMethod,
      shipping_address: address || null,
      note: note || null,
    });
    if (order) router.push(`/orders/${order.id}`);
  }

  return (
    <form onSubmit={onSubmit} className="space-y-6">
      <PageHeader backHref="/orders" title={t("New order")} />
      <ErrorAlert error={error} />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card title={t("Customer")}>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label={t("Phone")} hint="Existing customers are found automatically.">
                <Input required placeholder="01712-345678" value={phone} onChange={(e) => setPhone(e.target.value)} />
              </Field>
              <Field label="Name">
                <Input required disabled={!!existing} value={name} onChange={(e) => setName(e.target.value)} />
              </Field>
              <div className="sm:col-span-2">
                <Field label={t("Address")} hint="Delivery address for this order.">
                  <Textarea value={address} onChange={(e) => setAddress(e.target.value)} />
                </Field>
              </div>
            </div>
            {existing && (
              <p className="mt-3 rounded-lg bg-sky-50 px-3 py-2 text-sm text-sky-800">
                Existing customer: <strong>{existing.name}</strong> ({formatPhone(existing.phone)}). The order will be added to their history.
              </p>
            )}
          </Card>

          <Card title={t("Products")}>
            <Input placeholder="Search products by name or SKU" value={productQuery} onChange={(e) => setProductQuery(e.target.value)} />
            <ul className="mt-3 max-h-64 divide-y divide-slate-100 overflow-y-auto">
              {products.data?.items.map((p) =>
                p.variants
                  .filter((v) => v.is_active)
                  .map((v) => (
                    <li key={v.id} className="flex items-center justify-between gap-2 py-2 text-sm">
                      <span>
                        {p.name} <span className="text-slate-500">· {v.label}</span>
                        <span className="block text-xs text-slate-500">
                          {formatBDT(v.effective_price)} · {v.stock} in stock
                        </span>
                      </span>
                      <Button type="button" variant="secondary" disabled={v.stock === 0} onClick={() => addVariant(p, v)}>
                        {v.stock === 0 ? "Out of stock" : "Add"}
                      </Button>
                    </li>
                  )),
              )}
              {products.data?.items.length === 0 && <li className="py-4 text-center text-sm text-slate-500">No active products match.</li>}
            </ul>

            {lines.length > 0 && (
              <table className="mt-4 w-full text-sm">
                <thead>
                  <tr>
                    <th className="py-2">Item</th>
                    <th className="w-24 py-2">{t("Quantity")}</th>
                    <th className="w-28 py-2">Unit price</th>
                    <th className="py-2 text-right">Line total</th>
                    <th />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {lines.map((l, i) => (
                    <tr key={l.variant.id}>
                      <td className="py-2">
                        {l.product.name} <span className="text-slate-500">({l.variant.label})</span>
                      </td>
                      <td className="py-2">
                        <Input
                          type="number"
                          min={1}
                          max={l.variant.stock}
                          value={l.quantity}
                          onChange={(e) =>
                            setLines(lines.map((x, j) => (j === i ? { ...x, quantity: Math.max(1, Number(e.target.value) || 1) } : x)))
                          }
                        />
                      </td>
                      <td className="py-2">
                        <Input
                          type="number"
                          min={0}
                          step="0.01"
                          value={l.unitPrice}
                          onChange={(e) => setLines(lines.map((x, j) => (j === i ? { ...x, unitPrice: e.target.value } : x)))}
                        />
                      </td>
                      <td className="py-2 text-right">{formatBDT(toNumber(l.unitPrice) * l.quantity)}</td>
                      <td className="py-2 text-right">
                        <button type="button" className="text-rose-600" onClick={() => setLines(lines.filter((_, j) => j !== i))} aria-label="Remove">
                          ✕
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </div>

        <Card title="Summary" className="h-fit">
          <div className="space-y-3">
            <Field label={t("Delivery charge")}>
              <Input type="number" min={0} step="1" value={delivery} onChange={(e) => setDeliveryCharge(e.target.value)} />
            </Field>
            <Field label={t("Discount")}>
              <Input type="number" min={0} step="1" value={discount} onChange={(e) => setDiscount(e.target.value)} />
            </Field>
            <Field label={t("Payment method")}>
              <Select value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)}>
                {paymentMethods.data?.map((m) => (
                  <option key={m.code} value={m.code}>
                    {m.label}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label={t("Note")}>
              <Textarea value={note} onChange={(e) => setNote(e.target.value)} />
            </Field>
            <dl className="space-y-1 border-t border-slate-100 pt-3 text-sm">
              <div className="flex justify-between"><dt>{t("Subtotal")}</dt><dd>{formatBDT(subtotal)}</dd></div>
              <div className="flex justify-between"><dt>{t("Delivery charge")}</dt><dd>{formatBDT(delivery)}</dd></div>
              <div className="flex justify-between"><dt>{t("Discount")}</dt><dd>− {formatBDT(discount)}</dd></div>
              <div className="flex justify-between text-base font-semibold"><dt>{t("Total")}</dt><dd>{formatBDT(total)}</dd></div>
            </dl>
            {toNumber(discount) > subtotal && <p className="text-xs text-rose-600">Discount cannot exceed the subtotal.</p>}
            <Button type="submit" className="w-full" loading={pending} disabled={lines.length === 0 || toNumber(discount) > subtotal}>
              Create order
            </Button>
            <p className="text-xs text-slate-500">Totals are recalculated on the server. Stock is reserved when the order is created.</p>
          </div>
        </Card>
      </div>
    </form>
  );
}
