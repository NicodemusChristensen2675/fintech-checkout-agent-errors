from src.checkout_agent import PaymentEvent, authorize_payment


class RecordingClient:
    def __init__(self):
        self.payloads = []

    def capture(self, payload):
        self.payloads.append(payload)
        return {"event_id": "evt-1"}


def test_large_order_is_held_before_calling_payment_gateway():
    event = PaymentEvent("ord-risk", "cust-9", 150_000, "USD", "tok")
    called = []
    result, notice = authorize_payment(event, lambda _: called.append(True), RecordingClient())
    assert result == "manual_review"
    assert notice.action == "manual_review"
    assert called == []


def test_gateway_failure_is_captured_and_becomes_audit_notice():
    event = PaymentEvent("ord-fail", "cust-9", 1200, "USD", "tok")
    client = RecordingClient()
    result, notice = authorize_payment(event, lambda _: (_ for _ in ()).throw(ValueError("declined")), client)
    assert result == "payment_failed"
    assert notice.action == "payment_failed"
    assert client.payloads[0]["context"]["order_id"] == "ord-fail"
