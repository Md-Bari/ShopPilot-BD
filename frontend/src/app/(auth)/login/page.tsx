"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type FormEvent } from "react";
import { ErrorAlert } from "@/components/ui/feedback";
import { Button, Field, Input } from "@/components/ui/primitives";
import { authApi } from "@/lib/api/endpoints";
import { useAction } from "@/lib/hooks";
import { useT } from "@/lib/i18n";
import { useSession } from "@/lib/session";

function safeNext(next: string | null): string {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/dashboard";
}

function LoginForm() {
  const { t } = useT();
  const router = useRouter();
  const params = useSearchParams();
  const { me, refresh } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { run, pending, error } = useAction(authApi.login);

  useEffect(() => {
    if (me) router.replace(safeNext(params.get("next")));
  }, [me, params, router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (await run(email, password)) {
      const session = await refresh();
      router.replace(session && session.memberships.length === 0 ? "/onboarding" : safeNext(params.get("next")));
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <h1 className="text-xl font-semibold">{t("Sign in")}</h1>
      <ErrorAlert error={error} />
      <Field label={t("Email")}>
        <Input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
      </Field>
      <Field label={t("Password")}>
        <Input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
      </Field>
      <Button type="submit" className="w-full" loading={pending}>
        {t("Sign in")}
      </Button>
      <div className="flex justify-between text-sm">
        <Link href="/forgot-password" className="text-brand-700 hover:underline">
          {t("Forgot password?")}
        </Link>
        <Link href="/register" className="text-brand-700 hover:underline">
          {t("Create account")}
        </Link>
      </div>
    </form>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
