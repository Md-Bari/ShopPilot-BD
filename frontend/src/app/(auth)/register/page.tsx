"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { ErrorAlert } from "@/components/ui/feedback";
import { Button, Field, Input } from "@/components/ui/primitives";
import { authApi } from "@/lib/api/endpoints";
import { useAction } from "@/lib/hooks";
import { useT } from "@/lib/i18n";
import { useSession } from "@/lib/session";

export default function RegisterPage() {
  const { t } = useT();
  const router = useRouter();
  const { refresh } = useSession();
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });
  const { run, pending, error } = useAction(authApi.register);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (await run(form)) {
      await refresh();
      router.replace("/onboarding");
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <h1 className="text-xl font-semibold">{t("Create account")}</h1>
      <ErrorAlert error={error} />
      <Field label={t("Full name")}>
        <Input required minLength={2} value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
      </Field>
      <Field label={t("Email")}>
        <Input type="email" autoComplete="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
      </Field>
      <Field label={t("Password")} hint="At least 8 characters with letters and numbers.">
        <Input
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
        />
      </Field>
      <Button type="submit" className="w-full" loading={pending}>
        {t("Create account")}
      </Button>
      <p className="text-center text-sm text-slate-600">
        Already have an account?{" "}
        <Link href="/login" className="text-brand-700 hover:underline">
          {t("Sign in")}
        </Link>
      </p>
    </form>
  );
}
