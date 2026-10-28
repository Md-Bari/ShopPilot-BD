"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { ErrorAlert, Loading } from "@/components/ui/feedback";
import { Button, Field, Input, Textarea } from "@/components/ui/primitives";
import { businessApi } from "@/lib/api/endpoints";
import { useAction } from "@/lib/hooks";
import { useSession } from "@/lib/session";

export default function OnboardingPage() {
  const router = useRouter();
  const { me, loading, refresh, selectBusiness } = useSession();
  const [form, setForm] = useState({ name: "", phone: "", address: "" });
  const { run, pending, error } = useAction(businessApi.create);

  useEffect(() => {
    if (!loading && !me) router.replace("/login");
  }, [loading, me, router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const business = await run({ name: form.name, phone: form.phone || undefined, address: form.address || undefined });
    if (business) {
      selectBusiness(business.id);
      await refresh();
      router.replace("/dashboard");
    }
  }

  if (loading || !me) return <Loading />;

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-50 to-slate-100 px-4">
      <form onSubmit={onSubmit} className="w-full max-w-lg space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <div>
          <h1 className="text-xl font-semibold">Set up your shop</h1>
          <p className="mt-1 text-sm text-slate-500">
            You start on a 14-day free trial. No payment is taken now.
          </p>
        </div>
        <ErrorAlert error={error} />
        <Field label="Shop name">
          <Input required minLength={2} placeholder="e.g. Nusrat's Boutique" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <Field label="Shop phone (optional)" hint="Bangladeshi numbers like 01712-345678 are fine.">
          <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        </Field>
        <Field label="Pickup / shop address (optional)">
          <Textarea value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
        </Field>
        <Button type="submit" className="w-full" loading={pending}>
          Create shop
        </Button>
      </form>
    </div>
  );
}
