"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState, type FormEvent } from "react";
import { MessageStatusBadge } from "@/components/orders/StatusBadge";
import { EmptyState, ErrorAlert, Loading, PageHeader } from "@/components/ui/feedback";
import { Badge, Button, cx, Textarea } from "@/components/ui/primitives";
import { ApiError, newIdempotencyKey } from "@/lib/api/client";
import { whatsappApi } from "@/lib/api/endpoints";
import { formatDateTime, formatPhone, formatTime } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import { useT } from "@/lib/i18n";

function Conversation({ id, onChanged }: { id: number; onChanged: () => void }) {
  const { data, error, loading, reload } = useApi(() => whatsappApi.conversation(id), [id]);
  const [text, setText] = useState("");
  const [key, setKey] = useState(newIdempotencyKey());
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<ApiError | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "end" });
  }, [data?.messages.length]);

  useEffect(() => {
    onChanged(); // opening marks the conversation read
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function send(e: FormEvent) {
    e.preventDefault();
    setSending(true);
    setSendError(null);
    try {
      await whatsappApi.reply(id, text, key);
      setText("");
      setKey(newIdempotencyKey());
    } catch (err) {
      const apiError = err instanceof ApiError ? err : new ApiError(0, "unknown", "Unexpected error");
      setSendError(apiError);
      if (apiError.code !== "delivery_unknown") setKey(newIdempotencyKey());
    } finally {
      setSending(false);
      void reload();
      onChanged();
    }
  }

  if (loading && !data) return <Loading />;
  if (error) return <ErrorAlert error={error} onRetry={reload} />;
  if (!data) return null;
  const conv = data.conversation;

  return (
    <div className="flex h-[70vh] flex-col">
      <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <div>
          <p className="font-medium">{conv.customer_name || conv.contact_name || formatPhone(conv.wa_id)}</p>
          <p className="text-xs text-slate-500">
            {formatPhone(conv.wa_id)}
            {data.customer && (
              <>
                {" · "}
                <Link href={`/customers/${data.customer.id}`} className="text-brand-700 hover:underline">
                  customer profile
                </Link>
              </>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {conv.service_window_open ? (
            <Badge tone="green">Reply window open until {formatTime(data.service_window_expires_at)}</Badge>
          ) : (
            <Badge tone="amber">Reply window closed</Badge>
          )}
          <Button variant="ghost" onClick={() => reload()} aria-label="Refresh">↻</Button>
        </div>
      </header>
      <div className="flex-1 space-y-2 overflow-y-auto bg-[#efeae2] p-4">
        {data.messages.map((m) => (
          <div key={m.id} className={cx("flex", m.direction === "outbound" ? "justify-end" : "justify-start")}>
            <div className={cx("max-w-[80%] rounded-lg px-3 py-2 text-sm shadow-sm", m.direction === "outbound" ? "bg-[#d9fdd3]" : "bg-white")}>
              {m.text ? <p className="whitespace-pre-wrap">{m.text}</p> : <p className="italic text-slate-500">[{m.message_type}]</p>}
              {m.template_name && <p className="mt-1 text-[10px] uppercase text-slate-500">template · {m.template_name}</p>}
              <div className="mt-1 flex items-center justify-end gap-2 text-[11px] text-slate-500">
                {formatDateTime(m.created_at)}
                {m.direction === "outbound" && <MessageStatusBadge status={m.status} />}
              </div>
              {m.error_detail && <p className="mt-1 text-xs text-rose-600">{m.error_detail}</p>}
            </div>
          </div>
        ))}
        <div ref={bottom} />
      </div>
      <form onSubmit={send} className="space-y-2 border-t border-slate-200 p-3">
        {!data.can_reply && (
          <div className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900">
            {data.reply_blockers.map((b) => (
              <p key={b}>{b}</p>
            ))}
          </div>
        )}
        <ErrorAlert error={sendError} />
        <div className="flex gap-2">
          <Textarea
            className="min-h-[44px] flex-1"
            placeholder={data.can_reply ? "Type a reply…" : "Replies are disabled"}
            disabled={!data.can_reply}
            maxLength={4096}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <Button type="submit" loading={sending} disabled={!data.can_reply || !text.trim()}>
            Send
          </Button>
        </div>
      </form>
    </div>
  );
}

function Inbox() {
  const { t } = useT();
  const params = useSearchParams();
  const [selected, setSelected] = useState<number | null>(params.get("c") ? Number(params.get("c")) : null);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const { data, error, loading, reload } = useApi(() => whatsappApi.conversations({ unread_only: unreadOnly }), [unreadOnly]);

  // Polling keeps the inbox fresh without websockets (MVP).
  useEffect(() => {
    const timer = setInterval(() => void reload(), 20_000);
    return () => clearInterval(timer);
  }, [reload]);

  return (
    <div>
      <PageHeader
        title={t("WhatsApp Inbox")}
        description="Refreshes every 20 seconds."
        actions={
          <>
            <Button variant={unreadOnly ? "primary" : "secondary"} onClick={() => setUnreadOnly(!unreadOnly)}>
              Unread only
            </Button>
            <Button variant="secondary" onClick={() => reload()}>Refresh</Button>
          </>
        }
      />
      {error && <ErrorAlert error={error} onRetry={reload} />}
      {loading && !data ? (
        <Loading />
      ) : data && data.items.length === 0 ? (
        <EmptyState
          title="No conversations yet"
          description="Messages customers send to your WhatsApp number appear here once the webhook is set up (see WhatsApp Settings)."
        />
      ) : data ? (
        <div className="grid overflow-hidden rounded-xl border border-slate-200 bg-white md:grid-cols-3">
          <ul className={cx("divide-y divide-slate-100 border-r border-slate-200 md:block", selected ? "hidden" : "block")}>
            {data.items.map((c) => (
              <li key={c.id}>
                <button
                  className={cx("w-full px-4 py-3 text-left hover:bg-slate-50", selected === c.id && "bg-brand-50")}
                  onClick={() => setSelected(c.id)}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium">{c.customer_name || c.contact_name || formatPhone(c.wa_id)}</span>
                    <span className="shrink-0 text-xs text-slate-400">{formatTime(c.last_message_at)}</span>
                  </div>
                  <div className="mt-0.5 flex items-center justify-between gap-2">
                    <span className="truncate text-sm text-slate-500">{c.last_message_preview}</span>
                    {c.unread_count > 0 && <span className="rounded-full bg-brand-600 px-2 text-xs text-white">{c.unread_count}</span>}
                  </div>
                </button>
              </li>
            ))}
          </ul>
          <div className={cx("md:col-span-2", selected ? "block" : "hidden md:block")}>
            {selected ? (
              <>
                <button className="px-4 pt-3 text-sm text-brand-700 md:hidden" onClick={() => setSelected(null)}>
                  ← All conversations
                </button>
                <Conversation key={selected} id={selected} onChanged={reload} />
              </>
            ) : (
              <div className="flex h-[70vh] items-center justify-center text-sm text-slate-500">Select a conversation</div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default function InboxPage() {
  return (
    <Suspense fallback={<Loading />}>
      <Inbox />
    </Suspense>
  );
}
