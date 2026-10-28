"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";
import { ErrorAlert, SuccessAlert } from "@/components/ui/feedback";
import { Button, Field, Input } from "@/components/ui/primitives";
import { ApiError } from "@/lib/api/client";
import { authApi } from "@/lib/api/endpoints";
import { useAction } from "@/lib/hooks";

function ResetForm() {
  const token = useSearchParams().get("token") || "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [done, setDone] = useState(false);
  const { run, pending, error, setError } = useAction(authApi.confirmReset);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (password !== confirm) {
      setError(new ApiError(0, "mismatch", "Passwords do not match."));
      return;
    }
    if (await run(token, password)) setDone(true);
  }

  if (!token) return <ErrorAlert error="This reset link is missing its token. Request a new one." />;

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <h1 className="text-xl font-semibold">Choose a new password</h1>
      {done ? (
        <SuccessAlert>
          Password updated.{" "}
          <Link href="/login" className="font-medium underline">
            Sign in
          </Link>
        </SuccessAlert>
      ) : (
        <>
          <ErrorAlert error={error} />
          <Field label="New password" hint="At least 8 characters with letters and numbers.">
            <Input type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} />
          </Field>
          <Field label="Confirm password">
            <Input type="password" required minLength={8} value={confirm} onChange={(e) => setConfirm(e.target.value)} />
          </Field>
          <Button type="submit" className="w-full" loading={pending}>
            Update password
          </Button>
        </>
      )}
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetForm />
    </Suspense>
  );
}
