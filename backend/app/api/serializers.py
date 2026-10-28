"""Model -> response conversions that need more than `from_attributes`."""

from app.api import schemas as s
from app.domain.order_rules import allowed_next_statuses
from app.infrastructure.db.models import Order, Product, User, WhatsAppConversation


def media_url(prefix: str, path: str | None) -> str | None:
    return f"{prefix.rstrip('/')}/{path}" if path else None


def product_out(product: Product, media_prefix: str) -> s.ProductOut:
    out = s.ProductOut.model_validate(product)
    out.image_url = media_url(media_prefix, product.image_path)
    out.total_stock = sum(v.stock for v in product.variants if v.is_active)
    return out


def me_out(user: User) -> s.MeOut:
    return s.MeOut(
        user=s.UserOut.model_validate(user),
        memberships=[
            s.MembershipOut(business_id=m.business_id, business_name=m.business.name, role=m.role)
            for m in user.memberships if m.business.is_active
        ],
    )


def order_detail_out(order: Order, messages=()) -> s.OrderDetailOut:
    out = s.OrderDetailOut.model_validate(order, from_attributes=True)
    out.status_history = [
        s.StatusHistoryOut(id=h.id, from_status=h.from_status, to_status=h.to_status, note=h.note,
                           changed_by_name=h.changed_by.full_name if h.changed_by else None, created_at=h.created_at)
        for h in order.status_history
    ]
    out.allowed_next_statuses = sorted(st.value for st in allowed_next_statuses(order.status))
    out.messages = [s.MessageOut.model_validate(m) for m in messages]
    return out


def conversation_out(conversation: WhatsAppConversation, *, customer_name: str | None,
                     service_window_open: bool) -> s.ConversationOut:
    return s.ConversationOut(
        id=conversation.id, wa_id=conversation.wa_id, contact_name=conversation.contact_name,
        customer_id=conversation.customer_id, customer_name=customer_name,
        last_message_at=conversation.last_message_at, last_message_preview=conversation.last_message_preview,
        last_inbound_at=conversation.last_inbound_at, unread_count=conversation.unread_count,
        service_window_open=service_window_open,
    )
