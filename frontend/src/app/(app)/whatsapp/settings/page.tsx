"use client";

import { useState, type ReactNode } from "react";
import { ErrorAlert, Loading, PageHeader } from "@/components/ui/feedback";
import { Badge, Button, Card, Input } from "@/components/ui/primitives";
import { whatsappApi } from "@/lib/api/endpoints";
import { formatDateTime, formatPhone } from "@/lib/format";
import { useAction, useApi } from "@/lib/hooks";
import { canManage, useSession } from "@/lib/session";
import type { WhatsAppSettings } from "@/lib/types";

const STATE_BADGE: Record<WhatsAppSettings["state"], ReactNode> = {
  connected: <Badge tone="green">Connected</Badge>,
  pending_check: <Badge tone="amber">Linked — connection not verified</Badge>,
  check_failed: <Badge tone="red">Connection check failed</Badge>,
  not_connected: <Badge>Not connected</Badge>,
};

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5 py-2 sm:flex-row sm:items-center sm:justify-between">
      <dt className="text-sm text-slate-500">{label}</dt>
      <dd className="text-sm font-medium text-slate-800 break-all">{children}</dd>
    </div>
  );
}

const yesNo = (ok: boolean) => (ok ? <Badge tone="green">configured</Badge> : <Badge tone="red">missing</Badge>);

export default function WhatsAppSettingsPage() {
  const { membership } = useSession();
  const manager = canManage(membership);
  const { data, error, loading, reload, setData } = useApi(whatsappApi.settings);
  const connect = useAction(whatsappApi.connect);
  const check = useAction(whatsappApi.check);
  const disconnect = useAction(whatsappApi.disconnect);
  const addRecipient = useAction(whatsappApi.addTestRecipient);
  const removeRecipient = useAction(whatsappApi.removeTestRecipient);
  const [phone, setPhone] = useState("");
  const [label, setLabel] = useState("");

  if (loading && !data) return <Loading />;
  if (error) return <ErrorAlert error={error} onRetry={reload} />;
  if (!data) return null;
  const env = data.environment;
  const config = data.configuration;
  const actionError = connect.error || check.error || disconnect.error;

  return (
    <div className="space-y-6">
      <PageHeader
        title="WhatsApp Settings"
        description="Official Meta WhatsApp Cloud API. The access token stays on the server and is never sent to the browser."
        actions={STATE_BADGE[data.state]}
      />
      <ErrorAlert error={actionError} />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Connection">
          <dl className="divide-y divide-slate-100">
            <Row label="Status">{STATE_BADGE[data.state]}</Row>
            <Row label="Mode">{(config?.mode || env.mode) === "test" ? <Badge tone="amber">Test number</Badge> : <Badge tone="green">Production</Badge>}</Row>
            <Row label="Phone number ID">{config?.phone_number_id || env.phone_number_id || "—"}</Row>
            <Row label="WhatsApp Business Account ID">{config?.waba_id || env.waba_id || "—"}</Row>
            <Row label="Display number">{config?.display_phone_number || "—"}</Row>
            <Row label="Verified name">{config?.verified_name || "—"}</Row>
            <Row label="Access token">{env.access_token_present ? <code>{env.access_token_masked}</code> : <Badge tone="red">missing</Badge>}</Row>
            <Row label="Graph API version">{env.api_version}</Row>
            <Row label="Last check">
              {config?.last_check_at ? (
                <>
                  {formatDateTime(config.last_check_at)} {config.last_check_ok ? <Badge tone="green">ok</Badge> : <Badge tone="red">failed</Badge>}
                </>
              ) : (
                "never"
              )}
            </Row>
          </dl>
          {config?.last_check_error && <p className="mt-2 rounded bg-rose-50 p-2 text-xs text-rose-700">{config.last_check_error}</p>}
          {manager ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {!config ? (
                <Button loading={connect.pending} disabled={!env.access_token_present || !env.phone_number_id} onClick={async () => { const r = await connect.run(); if (r) setData(r); }}>
                  Connect test number
                </Button>
              ) : (
                <>
                  <Button variant="secondary" loading={check.pending} onClick={async () => { const r = await check.run(); if (r) setData(r); }}>
                    Run connection check
                  </Button>
                  <Button variant="danger" loading={disconnect.pending} onClick={async () => { if (window.confirm("Disconnect WhatsApp from this business?")) { const r = await disconnect.run(); if (r) setData(r); } }}>
                    Disconnect
                  </Button>
                </>
              )}
            </div>
          ) : (
            <p className="mt-4 text-xs text-slate-500">Only owners and admins can change WhatsApp settings.</p>
          )}
          {!env.access_token_present && (
            <p className="mt-3 text-xs text-slate-500">Set META_ACCESS_TOKEN and META_PHONE_NUMBER_ID in the server environment, then restart the API.</p>
          )}
        </Card>

        <Card title="Webhook">
          <dl className="divide-y divide-slate-100">
            <Row label="Callback path"><code>https://&lt;your-backend&gt;{data.webhook.callback_path}</code></Row>
            <Row label="Verify token">{yesNo(data.webhook.verify_token_configured)}</Row>
            <Row label="App secret (signature check)">{yesNo(data.webhook.app_secret_configured)}</Row>
            <Row label="Verified by Meta">{data.webhook.verified_at ? formatDateTime(data.webhook.verified_at) : "not yet"}</Row>
            <Row label="Last event received">{data.webhook.last_event_at ? formatDateTime(data.webhook.last_event_at) : "none yet"}</Row>
          </dl>
          <p className="mt-3 text-xs text-slate-500">
            In the Meta App Dashboard → WhatsApp → Configuration, set the callback URL to your public HTTPS backend URL (for local
            development use a tunnel such as cloudflared or ngrok) and subscribe to the <code>messages</code> field.
          </p>
        </Card>

        <Card title="Authorized test recipients">
          <p className="mb-3 text-xs text-slate-500">
            In test mode Meta only delivers to numbers you added in the Meta app (max 5). Add the same numbers here; other numbers are blocked
            before any API call.
          </p>
          <ul className="mb-3 divide-y divide-slate-100 text-sm">
            {data.test_recipients.length === 0 && <li className="py-2 text-slate-500">No test recipients yet.</li>}
            {data.test_recipients.map((r) => (
              <li key={r.id} className="flex items-center justify-between py-2">
                <span>
                  {formatPhone(r.phone)} {r.label && <span className="text-slate-500">· {r.label}</span>}
                </span>
                {manager && (
                  <Button variant="ghost" onClick={async () => { if (await removeRecipient.run(r.id)) void reload(); }}>
                    Remove
                  </Button>
                )}
              </li>
            ))}
          </ul>
          {manager && (
            <div className="grid gap-2 sm:grid-cols-3">
              <Input placeholder="01712-345678" value={phone} onChange={(e) => setPhone(e.target.value)} />
              <Input placeholder="Label (optional)" value={label} onChange={(e) => setLabel(e.target.value)} />
              <Button variant="secondary" loading={addRecipient.pending} disabled={!phone} onClick={async () => { if (await addRecipient.run(phone, label)) { setPhone(""); setLabel(""); void reload(); } }}>
                Add
              </Button>
            </div>
          )}
          <div className="mt-2"><ErrorAlert error={addRecipient.error || removeRecipient.error} /></div>
        </Card>

        <Card title="Message templates">
          <p className="mb-3 text-xs text-slate-500">
            Business-initiated messages outside the 24-hour window must use templates approved in WhatsApp Manager. Create templates with exactly
            this text, then set their names in the server environment.
          </p>
          <ul className="space-y-3 text-sm">
            {data.templates.map((t) => (
              <li key={t.kind} className="rounded-lg border border-slate-200 p-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{t.kind.replace("_", " ")}</span>
                  {t.configured ? <Badge tone="blue">{t.template_name} ({t.language})</Badge> : <Badge tone="amber">not configured — 24h window only</Badge>}
                </div>
                <p className="mt-1 text-xs text-slate-600">{t.body}</p>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card title="Recent API errors">
        {data.recent_errors.length === 0 ? (
          <p className="text-sm text-slate-500">No errors recorded.</p>
        ) : (
          <ul className="divide-y divide-slate-100 text-sm">
            {data.recent_errors.map((e) => (
              <li key={e.id} className="py-2">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="red">{e.error_kind || "error"}</Badge>
                  <span className="font-medium">{e.operation}</span>
                  {e.error_code && <span className="text-slate-500">code {e.error_code}</span>}
                  {e.http_status && <span className="text-slate-500">HTTP {e.http_status}</span>}
                  <span className="text-xs text-slate-400">{formatDateTime(e.created_at)}</span>
                </div>
                <p className="mt-1 text-slate-600">{e.message}</p>
                {e.fbtrace_id && <p className="text-xs text-slate-400">fbtrace_id: {e.fbtrace_id}</p>}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
