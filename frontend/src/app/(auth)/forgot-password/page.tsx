"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { ErrorAlert, SuccessAlert } from "@/components/ui/feedback";
import { Button, Field, Input } from "@/components/ui/primitives";
import { authApi } from "@/lib/api/endpoints";
import { useAction } from "@/lib/hooks";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [done, setDone] = useState(false);
  const { run, pending, error } = useAction(authApi.requestReset);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (await run(email)) setDone(true);
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <h1 className="text-xl font-semibold">Reset your password</h1>
      {done ? (
        <SuccessAlert>If an account exists for {email}, a reset link has been sent. Check your inbox.</SuccessAlert>
      ) : (
        <>
          <ErrorAlert error={error} />
          <Field label="Email">
            <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <Button type="submit" className="w-full" loading={pending}>
            Send reset link
          </Button>
        </>
      )}
      <p className="text-center text-sm">
        <Link href="/login" className="text-brand-700 hover:underline">
          Back to sign in
        </Link>
      </p>
    </form>
  );
}
