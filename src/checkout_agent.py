from dataclasses import dataclass
from typing import Any, Callable

from .infrai_client import InfraiClient


@dataclass(frozen=True)
class PaymentEvent:
    order_id: str
    customer_id: str
    amount_cents: int
    currency: str
    payment_token: str


@dataclass(frozen=True)
class AuditNotice:
    order_id: str
    action: str
    reason: str


def authorize_payment(event: PaymentEvent, charge: Callable[[PaymentEvent], str], client: InfraiClient) -> tuple[str, AuditNotice]:
    """Choose a checkout action, recording agent failures with order context."""
    if event.amount_cents > 100_000:
        notice = AuditNotice(event.order_id, "manual_review", "amount exceeds review threshold")
        return "manual_review", notice
    try:
        receipt = charge(event)
    except Exception as exc:
        client.capture({
            "title": "checkout payment authorization failed",
            "message": f"{type(exc).__name__}: {exc}",
            "level": "error",
            "fingerprint": ["checkout-agent", "authorize-payment"],
            "exception": repr(exc),
            "context": {"order_id": event.order_id, "customer_id": event.customer_id, "amount_cents": event.amount_cents},
        })
        notice = AuditNotice(event.order_id, "payment_failed", "authorization service error recorded")
        return "payment_failed", notice
    return receipt, AuditNotice(event.order_id, "payment_authorized", "payment token accepted")


if __name__ == "__main__":
    event = PaymentEvent("ord-1042", "cust-77", 4200, "USD", "tok_demo")
    result, notice = authorize_payment(event, lambda _: "receipt-1042", InfraiClient())
    print({"result": result, "audit": notice.__dict__})
