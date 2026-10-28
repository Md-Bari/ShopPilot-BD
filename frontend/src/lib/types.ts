// Response shapes returned by the FastAPI backend. Money values arrive as decimal strings.

export type Money = string | number;

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  is_superuser: boolean;
  preferred_language: string;
}

export interface Membership {
  business_id: number;
  business_name: string;
  role: "owner" | "admin" | "staff";
}

export interface Me {
  user: User;
  memberships: Membership[];
}

export interface Business {
  id: number;
  name: string;
  slug: string;
  phone: string | null;
  email: string | null;
  address: string | null;
  facebook_page_url: string | null;
  timezone: string;
  currency: string;
  order_prefix: string;
  default_delivery_charge: number;
  created_at: string;
}

export interface Member {
  id: number;
  user_id: number;
  email: string;
  full_name: string;
  role: string;
}

export interface PaymentMethod {
  id: number;
  code: string;
  label: string;
  is_active: boolean;
}

export interface Variant {
  id: number;
  sku: string | null;
  size: string;
  color: string;
  label: string;
  price: Money | null;
  effective_price: Money;
  stock: number;
  low_stock_threshold: number;
  is_active: boolean;
}

export interface Product {
  id: number;
  name: string;
  sku: string;
  description: string | null;
  price: Money;
  cost_price: Money | null;
  status: "active" | "archived";
  image_url: string | null;
  total_stock: number;
  variants: Variant[];
  created_at: string;
  updated_at: string;
}

export interface ImportSummary {
  products_created: number;
  products_updated: number;
  variants_created: number;
  variants_updated: number;
  errors: { row: number; message: string }[];
}

export interface Customer {
  id: number;
  name: string;
  phone: string;
  address: string | null;
  area: string | null;
  notes: string | null;
  created_at: string;
  order_count: number;
  last_order_at: string | null;
}

export interface Consent {
  id: number;
  channel: string;
  purpose: "transactional" | "marketing";
  status: "granted" | "revoked";
  source: string;
  note: string | null;
  recorded_at: string;
}

export type OrderStatus = "pending" | "confirmed" | "processing" | "shipped" | "delivered" | "cancelled" | "returned";

export interface OrderSummary {
  id: number;
  order_number: string;
  status: OrderStatus;
  payment_status: string;
  total: Money;
  amount_paid: Money;
  created_at: string;
}

export interface CustomerDetail {
  customer: Customer;
  orders: OrderSummary[];
  consents: Consent[];
  transactional_consent: "granted" | "revoked" | null;
  marketing_consent: "granted" | "revoked" | null;
}

export interface OrderListItem extends OrderSummary {
  payment_method_code: string;
  customer: { id: number; name: string; phone: string };
}

export interface OrderItem {
  id: number;
  product_id: number | null;
  variant_id: number | null;
  product_name: string;
  variant_label: string;
  sku: string | null;
  unit_price: Money;
  quantity: number;
  line_total: Money;
}

export interface StatusHistory {
  id: number;
  from_status: string | null;
  to_status: string;
  note: string | null;
  changed_by_name: string | null;
  created_at: string;
}

export interface Payment {
  id: number;
  amount: Money;
  method_code: string;
  reference: string | null;
  created_at: string;
}

export interface Message {
  id: number;
  conversation_id: number;
  order_id: number | null;
  direction: "inbound" | "outbound";
  message_type: string;
  text: string | null;
  template_name: string | null;
  notification_kind: string | null;
  status: string;
  status_updated_at: string | null;
  error_code: string | null;
  error_title: string | null;
  error_detail: string | null;
  safe_metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface OrderDetail extends OrderListItem {
  subtotal: Money;
  delivery_charge: Money;
  discount: Money;
  shipping_address: string | null;
  note: string | null;
  confirmed_at: string | null;
  shipped_at: string | null;
  delivered_at: string | null;
  cancelled_at: string | null;
  returned_at: string | null;
  items: OrderItem[];
  payments: Payment[];
  status_history: StatusHistory[];
  allowed_next_statuses: OrderStatus[];
  messages: Message[];
}

export type NotificationKind = "order_confirmed" | "order_shipped" | "order_delivered" | "custom";

export interface NotificationPreview {
  kind: NotificationKind;
  order_id: number;
  order_number: string;
  recipient_phone: string;
  recipient_name: string;
  channel: "template" | "text";
  template_name: string | null;
  template_language: string | null;
  parameters: string[];
  text: string;
  mode: "test" | "production";
  service_window_open: boolean;
  service_window_expires_at: string | null;
  transactional_consent: string | null;
  can_send: boolean;
  blockers: string[];
}

export interface SendResult {
  replayed: boolean;
  message: Message;
}

export interface Conversation {
  id: number;
  wa_id: string;
  contact_name: string | null;
  customer_id: number | null;
  customer_name: string | null;
  last_message_at: string | null;
  last_message_preview: string | null;
  last_inbound_at: string | null;
  unread_count: number;
  service_window_open: boolean;
}

export interface ConversationDetail {
  conversation: Conversation;
  customer: { id: number; name: string; phone: string } | null;
  messages: Message[];
  service_window_expires_at: string | null;
  can_reply: boolean;
  reply_blockers: string[];
}

export interface WhatsAppSettings {
  state: "not_connected" | "pending_check" | "check_failed" | "connected";
  connected: boolean;
  environment: {
    access_token_present: boolean;
    access_token_masked: string;
    phone_number_id: string | null;
    waba_id: string | null;
    app_secret_present: boolean;
    verify_token_present: boolean;
    api_version: string;
    mode: string;
  };
  configuration: {
    phone_number_id: string;
    waba_id: string | null;
    display_phone_number: string | null;
    verified_name: string | null;
    mode: string;
    credential_source: string;
    is_enabled: boolean;
    last_check_at: string | null;
    last_check_ok: boolean | null;
    last_check_error: string | null;
  } | null;
  webhook: {
    callback_path: string;
    verify_token_configured: boolean;
    app_secret_configured: boolean;
    verified_at: string | null;
    last_event_at: string | null;
  };
  templates: { kind: string; template_name: string | null; language: string; configured: boolean; body: string }[];
  test_recipients: { id: number; phone: string; label: string | null }[];
  recent_errors: {
    id: number;
    operation: string;
    http_status: number | null;
    error_code: string | null;
    error_kind: string | null;
    message: string;
    fbtrace_id: string | null;
    created_at: string;
  }[];
}

export interface Dashboard {
  date: string;
  today: { orders: number; gross_order_value: Money; collected_revenue: Money };
  month_to_date: { orders: number; gross_order_value: Money; collected_revenue: Money; estimated_profit: Money };
  pending_confirmations: number;
  last_30_days_status_counts: Record<OrderStatus, number>;
  low_stock: { variant_id: number; product_id: number; product_name: string; variant_label: string; stock: number; threshold: number }[];
  recent_activity: {
    type: "order" | "message";
    at: string;
    title: string;
    subtitle: string;
    order_id?: number;
    conversation_id?: number;
    status?: string;
  }[];
  whatsapp: WhatsAppStats;
}

export interface WhatsAppStats {
  period_days: number;
  outbound_total: number;
  inbound_total: number;
  by_status: Record<string, number>;
  delivery_rate: number | null;
}

export interface SalesReport {
  date_from: string;
  date_to: string;
  orders: number;
  gross_order_value: Money;
  collected_revenue: Money;
  estimated_profit: Money;
  by_status: Record<OrderStatus, { count: number; value: Money }>;
  daily: { date: string; orders: number; gross_order_value: Money; collected_revenue: Money }[];
  top_products: { product_name: string; quantity: number; value: Money }[];
}

export interface Plan {
  code: string;
  name: string;
  price_bdt: Money;
  billing_period_days: number;
  monthly_order_limit: number | null;
  monthly_message_limit: number | null;
  is_public: boolean;
}

export interface Subscription {
  status: "trial" | "pending_payment" | "active" | "expired" | "cancelled" | null;
  is_paid: boolean;
  plan: Plan | null;
  requested_plan: Plan | null;
  current_period_start: string | null;
  current_period_end: string | null;
  payment_reference: string | null;
  usage: Record<string, number>;
  plans: Plan[];
}
