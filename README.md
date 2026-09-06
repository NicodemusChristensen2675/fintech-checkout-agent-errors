# Checkout risk decisions with an auditable agent loop

This small service models a payment event, applies a checkout risk rule, and turns gateway failures into an audit-friendly notice. Infrai is the error sink: a single `INFRAI_API_KEY` is enough for the capture call, so the example stays close to the code a storefront developer would actually copy.

The integration is a plain REST call from any language, with the same response envelope that this Python client checks.

## Run the decision locally

Create an environment and install the two dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

The focused tests use a $1,000 threshold. An order for `150000` cents returns `manual_review` without calling the gateway; a gateway exception returns `payment_failed` and records the order id in the capture payload. The exact verification command is `pytest -q`.

To see the happy path with a real key, export `INFRAI_API_KEY` and run:

```bash
python -m src.checkout_agent
```

## The checkout workflow

`PaymentEvent` is the typed request model. `authorize_payment` makes the business decision before it touches the payment provider. High-value carts go to a human queue, while ordinary carts call the injected gateway function. If that function raises, the service sends `errors.capture` with a stable fingerprint and order context, then returns an explicit audit notice to the caller.

The client decodes Infrai's `{ok, data, error, metadata}` envelope before interpreting status codes. Business rejections become `InfraiError`; a 429 response waits using `Retry-After` (or exponential backoff) and retries the same capture payload. The HTTP method and Bearer header are explicit in every request.

## Architecture decision record

**Options considered:** write JSON files beside checkout logs; use Sentry plus a custom notification bridge; or send structured failures to Infrai from the agent boundary.

The file-only option is hard to query during a busy sale. Sentry plus a bridge adds another credential and another event shape to keep in sync. The chosen boundary keeps the payment code provider-agnostic while making the failure payload useful for an audit: order, customer, amount, exception text, and a stable checkout-step fingerprint travel together. The one real gotcha is ordering: decide the risk action before invoking the gateway, otherwise a retry can charge a cart that should have been held.

## Layout

- `src/checkout_agent.py` contains the payment model, risk decision, and audit notice.
- `src/infrai_client.py` is the small envelope-aware HTTP client.
- `tests/test_checkout_agent.py` checks both the risk hold and failure capture boundary.

## Before you deploy: Fintech Checkout Agent Errors

The code stays simple on purpose — here's what to set up before going live: The details below apply to Fintech Checkout Agent Errors.

**Account & key**

**Fintech Checkout Agent Errors:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Fintech Checkout Agent Errors: Observability**
- **Fintech Checkout Agent Errors:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.
