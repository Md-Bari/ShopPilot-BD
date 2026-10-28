"use client";

import { useEffect, useState } from "react";
import { ErrorAlert, Loading, PageHeader } from "@/components/ui/feedback";
import { Badge, Button, Card, Field, Input, Select, Textarea } from "@/components/ui/primitives";
import { businessApi } from "@/lib/api/endpoints";
import { useAction, useApi } from "@/lib/hooks";
import { canManage, useSession } from "@/lib/session";

export default function BusinessSettingsPage() {
  const { membership, refresh } = useSession();
  const manager = canManage(membership);
  const business = useApi(businessApi.current);
  const members = useApi(businessApi.members);
  const methods = useApi(() => businessApi.paymentMethods(false));
  const [form, setForm] = useState({ name: "", phone: "", email: "", address: "", facebook_page_url: "", order_prefix: "", default_delivery_charge: "0" });
  const [saved, setSaved] = useState(false);
  const [invite, setInvite] = useState({ email: "", role: "staff" });
  const [method, setMethod] = useState({ code: "", label: "" });

  const update = useAction(businessApi.update);
  const addMember = useAction(businessApi.addMember);
  const removeMember = useAction(businessApi.removeMember);
  const saveMethod = useAction(businessApi.savePaymentMethod);

  useEffect(() => {
    const b = business.data;
    if (b)
      setForm({
        name: b.name, phone: b.phone || "", email: b.email || "", address: b.address || "",
        facebook_page_url: b.facebook_page_url || "", order_prefix: b.order_prefix,
        default_delivery_charge: String(b.default_delivery_charge),
      });
  }, [business.data]);

  if (business.loading && !business.data) return <Loading />;
  if (business.error) return <ErrorAlert error={business.error} onRetry={business.reload} />;

  async function save() {
    setSaved(false);
    const result = await update.run({
      name: form.name,
      phone: form.phone || null,
      email: form.email || null,
      address: form.address || null,
      facebook_page_url: form.facebook_page_url || null,
      order_prefix: form.order_prefix,
      default_delivery_charge: Number(form.default_delivery_charge) || 0,
    });
    if (result) {
      business.setData(result);
      setSaved(true);
      void refresh();
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Business Settings" />
      <Card title="Shop profile">
        <fieldset disabled={!manager} className="grid gap-4 sm:grid-cols-2">
          <Field label="Shop name"><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
          <Field label="Phone"><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
          <Field label="Email"><Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
          <Field label="Facebook page URL"><Input value={form.facebook_page_url} onChange={(e) => setForm({ ...form, facebook_page_url: e.target.value })} /></Field>
          <Field label="Order number prefix" hint="Orders are numbered like SP-1001."><Input value={form.order_prefix} maxLength={10} onChange={(e) => setForm({ ...form, order_prefix: e.target.value.toUpperCase() })} /></Field>
          <Field label="Default delivery charge (৳)"><Input type="number" min={0} value={form.default_delivery_charge} onChange={(e) => setForm({ ...form, default_delivery_charge: e.target.value })} /></Field>
          <div className="sm:col-span-2"><Field label="Address"><Textarea value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} /></Field></div>
        </fieldset>
        {manager && (
          <div className="mt-4 flex items-center gap-3">
            <Button onClick={save} loading={update.pending}>Save</Button>
            {saved && <span className="text-sm text-emerald-700">Saved.</span>}
          </div>
        )}
        <div className="mt-3"><ErrorAlert error={update.error} /></div>
        <p className="mt-3 text-xs text-slate-500">Time zone: Asia/Dhaka · Currency: BDT (৳)</p>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Team members">
          <ul className="divide-y divide-slate-100 text-sm">
            {members.data?.map((m) => (
              <li key={m.id} className="flex items-center justify-between py-2">
                <span>
                  {m.full_name} <span className="block text-xs text-slate-500">{m.email}</span>
                </span>
                <span className="flex items-center gap-2">
                  <Badge tone={m.role === "owner" ? "purple" : m.role === "admin" ? "blue" : "gray"}>{m.role}</Badge>
                  {manager && m.role !== "owner" && (
                    <Button variant="ghost" onClick={async () => { if (window.confirm(`Remove ${m.email}?`) && (await removeMember.run(m.id)) !== undefined) void members.reload(); }}>
                      Remove
                    </Button>
                  )}
                </span>
              </li>
            ))}
          </ul>
          {manager && (
            <div className="mt-4 grid gap-2 border-t border-slate-100 pt-4 sm:grid-cols-3">
              <Input type="email" placeholder="Their account email" value={invite.email} onChange={(e) => setInvite({ ...invite, email: e.target.value })} />
              <Select value={invite.role} onChange={(e) => setInvite({ ...invite, role: e.target.value })}>
                <option value="staff">Staff</option>
                <option value="admin">Admin</option>
              </Select>
              <Button variant="secondary" loading={addMember.pending} disabled={!invite.email} onClick={async () => { if (await addMember.run(invite.email, invite.role)) { setInvite({ email: "", role: "staff" }); void members.reload(); } }}>
                Add member
              </Button>
            </div>
          )}
          <p className="mt-2 text-xs text-slate-500">The person must register a ShopPilot account first. Staff can manage orders, products and customers.</p>
          <div className="mt-2"><ErrorAlert error={addMember.error || removeMember.error} /></div>
        </Card>

        <Card title="Payment methods">
          <ul className="divide-y divide-slate-100 text-sm">
            {methods.data?.map((m) => (
              <li key={m.id} className="flex items-center justify-between py-2">
                <span>
                  {m.label} <code className="text-xs text-slate-500">{m.code}</code>
                </span>
                {manager ? (
                  <Button variant="ghost" onClick={async () => { if (await saveMethod.run({ code: m.code, label: m.label, is_active: !m.is_active })) void methods.reload(); }}>
                    {m.is_active ? <Badge tone="green">enabled</Badge> : <Badge>disabled</Badge>}
                  </Button>
                ) : m.is_active ? <Badge tone="green">enabled</Badge> : <Badge>disabled</Badge>}
              </li>
            ))}
          </ul>
          {manager && (
            <div className="mt-4 grid gap-2 border-t border-slate-100 pt-4 sm:grid-cols-3">
              <Input placeholder="code (e.g. rocket)" value={method.code} onChange={(e) => setMethod({ ...method, code: e.target.value.toLowerCase() })} />
              <Input placeholder="Label (e.g. Rocket)" value={method.label} onChange={(e) => setMethod({ ...method, label: e.target.value })} />
              <Button variant="secondary" loading={saveMethod.pending} disabled={!method.code || !method.label} onClick={async () => { if (await saveMethod.run({ ...method, is_active: true })) { setMethod({ code: "", label: "" }); void methods.reload(); } }}>
                Add method
              </Button>
            </div>
          )}
          <div className="mt-2"><ErrorAlert error={saveMethod.error} /></div>
        </Card>
      </div>
    </div>
  );
}
