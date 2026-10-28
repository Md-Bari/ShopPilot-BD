"use client";

import type { ReactNode } from "react";
import { ErrorAlert, Loading, PageHeader } from "@/components/ui/feedback";
import { Badge, Button, Card } from "@/components/ui/primitives";
import { subscriptionApi } from "@/lib/api/endpoints";
import { formatBDT, formatDate } from "@/lib/format";
import { useAction, useApi } from "@/lib/hooks";
import { canManage, useSession } from "@/lib/session";

const STATUS: Record<string, ReactNode> = {
  trial: <Badge tone="blue">Free trial</Badge>,
  active: <Badge tone="green">Active · paid</Badge>,
  pending_payment: <Badge tone="amber">Awaiting payment confirmation</Badge>,
  expired: <Badge tone="red">Expired</Badge>,
  cancelled: <Badge>Cancelled</Badge>,
};

function limit(value: number | null) {
  return value === null ? "Unlimited" : value.toLocaleString("en-IN");
}

export default function SubscriptionPage() {
  const { membership } = useSession();
  const { data, error, loading, reload, setData } = useApi(subscriptionApi.get);
  const request = useAction(subscriptionApi.request);

  if (loading && !data) return <Loading />;
  if (error) return <ErrorAlert error={error} onRetry={reload} />;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <PageHeader title="Subscription" description="Payments are confirmed manually by the ShopPilot team during the pilot." />
      <Card title="Current plan">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-lg font-semibold">{data.plan?.name ?? "No plan"}</span>
          {data.status && STATUS[data.status]}
        </div>
        <p className="mt-2 text-sm text-slate-600">
          {data.status === "trial" ? "Trial ends" : "Current period ends"} {formatDate(data.current_period_end)}.
          {!data.is_paid && data.status !== "trial" && " This subscription is not paid."}
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg bg-slate-50 p-3 text-sm">
            Orders this month: <strong>{data.usage.orders ?? 0}</strong> / {limit(data.plan?.monthly_order_limit ?? null)}
          </div>
          <div className="rounded-lg bg-slate-50 p-3 text-sm">
            WhatsApp messages this month: <strong>{data.usage.whatsapp_messages ?? 0}</strong> / {limit(data.plan?.monthly_message_limit ?? null)}
          </div>
        </div>
        {data.requested_plan && (
          <p className="mt-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
            You requested the <strong>{data.requested_plan.name}</strong> plan ({formatBDT(data.requested_plan.price_bdt)}/month). Send the payment
            via bKash/Nagad with your shop name as reference; we activate it after verifying the payment. Until then it is <strong>not</strong> active.
          </p>
        )}
      </Card>

      <div className="grid gap-4 sm:grid-cols-2">
        {data.plans.map((plan) => {
          const current = data.plan?.code === plan.code && data.status === "active";
          return (
            <Card key={plan.code} title={plan.name}>
              <p className="text-2xl font-bold">
                {formatBDT(plan.price_bdt)}
                <span className="text-sm font-normal text-slate-500"> / month</span>
              </p>
              <ul className="mt-3 space-y-1 text-sm text-slate-600">
                <li>✓ {limit(plan.monthly_order_limit)} orders / month</li>
                <li>✓ {limit(plan.monthly_message_limit)} WhatsApp messages / month</li>
                <li>✓ Products, customers, reports and inbox</li>
              </ul>
              {canManage(membership) && (
                <Button
                  className="mt-4 w-full"
                  variant={current ? "secondary" : "primary"}
                  disabled={current || data.requested_plan?.code === plan.code}
                  loading={request.pending}
                  onClick={async () => { const r = await request.run(plan.code); if (r) setData(r); }}
                >
                  {current ? "Current plan" : data.requested_plan?.code === plan.code ? "Requested" : "Request this plan"}
                </Button>
              )}
            </Card>
          );
        })}
      </div>
      <ErrorAlert error={request.error} />
    </div>
  );
}
