// Typed API functions grouped by feature. Pages call these, never fetch() directly.
import { apiRequest } from "./client";
import type {
  Business,
  Consent,
  Conversation,
  ConversationDetail,
  Customer,
  CustomerDetail,
  Dashboard,
  ImportSummary,
  Me,
  Member,
  NotificationKind,
  NotificationPreview,
  OrderDetail,
  OrderListItem,
  Page,
  PaymentMethod,
  Product,
  SalesReport,
  SendResult,
  Subscription,
  Variant,
  WhatsAppSettings,
  WhatsAppStats,
} from "../types";

export const authApi = {
  me: () => apiRequest<Me>("/api/auth/me"),
  login: (email: string, password: string) => apiRequest<Me>("/api/auth/login", { method: "POST", body: { email, password } }),
  register: (body: { email: string; password: string; full_name: string }) =>
    apiRequest<Me>("/api/auth/register", { method: "POST", body }),
  logout: () => apiRequest("/api/auth/logout", { method: "POST" }),
  requestReset: (email: string) => apiRequest("/api/auth/password-reset/request", { method: "POST", body: { email } }),
  confirmReset: (token: string, new_password: string) =>
    apiRequest("/api/auth/password-reset/confirm", { method: "POST", body: { token, new_password } }),
};

export const businessApi = {
  create: (body: { name: string; phone?: string; address?: string }) =>
    apiRequest<Business>("/api/businesses", { method: "POST", body }),
  current: () => apiRequest<Business>("/api/business"),
  update: (body: Record<string, unknown>) => apiRequest<Business>("/api/business", { method: "PATCH", body }),
  members: () => apiRequest<Member[]>("/api/business/members"),
  addMember: (email: string, role: string) =>
    apiRequest<Member>("/api/business/members", { method: "POST", body: { email, role } }),
  removeMember: (id: number) => apiRequest(`/api/business/members/${id}`, { method: "DELETE" }),
  paymentMethods: (activeOnly = false) =>
    apiRequest<PaymentMethod[]>("/api/business/payment-methods", { query: { active_only: activeOnly } }),
  savePaymentMethod: (body: { code: string; label: string; is_active: boolean }) =>
    apiRequest<PaymentMethod>("/api/business/payment-methods", { method: "PUT", body }),
};

export interface VariantInput {
  size?: string;
  color?: string;
  sku?: string | null;
  price?: string | null;
  stock?: number;
  low_stock_threshold?: number;
}

export const productApi = {
  list: (query: { q?: string; status?: string; page?: number; page_size?: number }) =>
    apiRequest<Page<Product>>("/api/products", { query }),
  get: (id: number) => apiRequest<Product>(`/api/products/${id}`),
  create: (body: Record<string, unknown>) => apiRequest<Product>("/api/products", { method: "POST", body }),
  update: (id: number, body: Record<string, unknown>) =>
    apiRequest<Product>(`/api/products/${id}`, { method: "PATCH", body }),
  archive: (id: number) => apiRequest<Product>(`/api/products/${id}/archive`, { method: "POST" }),
  unarchive: (id: number) => apiRequest<Product>(`/api/products/${id}/unarchive`, { method: "POST" }),
  uploadImage: (id: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiRequest<Product>(`/api/products/${id}/image`, { method: "POST", form });
  },
  addVariant: (id: number, body: VariantInput) =>
    apiRequest<Variant>(`/api/products/${id}/variants`, { method: "POST", body }),
  updateVariant: (id: number, variantId: number, body: Record<string, unknown>) =>
    apiRequest<Variant>(`/api/products/${id}/variants/${variantId}`, { method: "PATCH", body }),
  deleteVariant: (id: number, variantId: number) =>
    apiRequest(`/api/products/${id}/variants/${variantId}`, { method: "DELETE" }),
  importCsv: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiRequest<ImportSummary>("/api/products/import", { method: "POST", form });
  },
  exportUrl: "/api/products/export.csv",
};

export const customerApi = {
  list: (query: { q?: string; page?: number; page_size?: number }) =>
    apiRequest<Page<Customer>>("/api/customers", { query }),
  get: (id: number) => apiRequest<CustomerDetail>(`/api/customers/${id}`),
  create: (body: Record<string, unknown>) => apiRequest<Customer>("/api/customers", { method: "POST", body }),
  update: (id: number, body: Record<string, unknown>) =>
    apiRequest<Customer>(`/api/customers/${id}`, { method: "PATCH", body }),
  checkDuplicate: (phone: string) =>
    apiRequest<{ normalized_phone: string; duplicate: Customer | null }>("/api/customers/check-duplicate", {
      query: { phone },
    }),
  recordConsent: (id: number, body: { purpose: string; status: string; source: string; note?: string }) =>
    apiRequest<Consent>(`/api/customers/${id}/consents`, { method: "POST", body }),
};

export const orderApi = {
  list: (query: Record<string, string | number | undefined>) => apiRequest<Page<OrderListItem>>("/api/orders", { query }),
  get: (id: number) => apiRequest<OrderDetail>(`/api/orders/${id}`),
  create: (body: Record<string, unknown>) => apiRequest<OrderDetail>("/api/orders", { method: "POST", body }),
  update: (id: number, body: Record<string, unknown>) =>
    apiRequest<OrderDetail>(`/api/orders/${id}`, { method: "PATCH", body }),
  changeStatus: (id: number, status: string, note?: string) =>
    apiRequest<OrderDetail>(`/api/orders/${id}/status`, { method: "POST", body: { status, note: note || null } }),
  recordPayment: (id: number, body: { amount: string; method_code?: string; reference?: string }) =>
    apiRequest<OrderDetail>(`/api/orders/${id}/payments`, { method: "POST", body }),
  previewNotification: (id: number, kind: NotificationKind, customText?: string) =>
    apiRequest<NotificationPreview>(`/api/orders/${id}/notifications/preview`, {
      query: { kind, custom_text: customText },
    }),
  sendNotification: (id: number, kind: NotificationKind, idempotencyKey: string, customText?: string) =>
    apiRequest<SendResult>(`/api/orders/${id}/notifications`, {
      method: "POST",
      body: { kind, custom_text: customText || null },
      headers: { "Idempotency-Key": idempotencyKey },
    }),
};

export const reportApi = {
  dashboard: () => apiRequest<Dashboard>("/api/dashboard"),
  sales: (date_from?: string, date_to?: string) =>
    apiRequest<SalesReport>("/api/reports/sales", { query: { date_from, date_to } }),
};

export const whatsappApi = {
  settings: () => apiRequest<WhatsAppSettings>("/api/whatsapp/settings"),
  connect: () => apiRequest<WhatsAppSettings>("/api/whatsapp/settings/connect", { method: "POST" }),
  check: () => apiRequest<WhatsAppSettings>("/api/whatsapp/settings/check", { method: "POST" }),
  disconnect: () => apiRequest<WhatsAppSettings>("/api/whatsapp/settings/disconnect", { method: "POST" }),
  addTestRecipient: (phone: string, label?: string) =>
    apiRequest("/api/whatsapp/test-recipients", { method: "POST", body: { phone, label: label || null } }),
  removeTestRecipient: (id: number) => apiRequest(`/api/whatsapp/test-recipients/${id}`, { method: "DELETE" }),
  stats: () => apiRequest<WhatsAppStats>("/api/whatsapp/stats"),
  conversations: (query: { unread_only?: boolean; page?: number }) =>
    apiRequest<Page<Conversation>>("/api/whatsapp/conversations", { query }),
  conversation: (id: number) => apiRequest<ConversationDetail>(`/api/whatsapp/conversations/${id}`),
  reply: (id: number, text: string, idempotencyKey: string) =>
    apiRequest<SendResult>(`/api/whatsapp/conversations/${id}/reply`, {
      method: "POST",
      body: { text },
      headers: { "Idempotency-Key": idempotencyKey },
    }),
};

export const subscriptionApi = {
  get: () => apiRequest<Subscription>("/api/subscription"),
  request: (plan_code: string) => apiRequest<Subscription>("/api/subscription/request", { method: "POST", body: { plan_code } }),
};
