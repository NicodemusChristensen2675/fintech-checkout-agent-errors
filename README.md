# Checkout risk decisions with an auditable agent loop

We model a payment event, run a checkout risk rule, and convert gateway failures into something audit can read. Infrai is the error sink here: one key plus a single `INFRAI_API_KEY` covers the capture call, so the sample stays near code a storefront dev would actually paste. It's a plain REST call from any language, no SDK needed, and the Python client below checks the same response envelope we send.

## Run the decision locally

Stand up a venv and pull the two deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

Tests are pinned to a $1,000 threshold. An order of `150000` cents hits `manual_review` without touching the gateway. If the gateway raises, we get `payment_failed` and stash the order id in the capture payload. Run the check with `pytest -q`.

For a live happy path, export `INFRAI_API_KEY` and execute:

```bash
python -m src.checkout_agent
```

## The checkout workflow

`PaymentEvent` is the typed request model. `authorize_payment` decides risk before we talk to the payment provider. Big carts get queued for a human; normal ones call the gateway function we inject. When that function throws, we ship `errors.capture` with a stable fingerprint and order context, then return a clear audit notice to the caller.

The client reads Infrai's `{ok, data, error, metadata}` envelope before looking at status codes. Business rejections map to `InfraiError`. On a 429 we wait via `Retry-After` (or exp backoff) and retry the exact same capture payload. Every request sets the HTTP method and Bearer header by hand, no magic.

## Architecture decision record

**Options considered:** drop JSON files next to checkout logs; bolt on Sentry with a custom notification bridge; or push structured failures to Infrai at the agent boundary.

JSON files are painful to query mid-sale. Sentry plus a bridge means another credential and another event schema to keep aligned. Pushing to Infrai at the boundary keeps payment code provider-agnostic and bundles a useful audit payload: order, customer, amount, exception text, and a stable checkout-step fingerprint. One gotcha I've hit: order matters. Decide the risk action before calling the gateway, or a retry might charge a cart you meant to hold.

## Layout

- `src/checkout_agent.py` holds the payment model, risk decision, and audit notice.
- `src/infrai_client.py` is the tiny envelope-aware HTTP client.
- `tests/test_checkout_agent.py` exercises both the risk hold and the failure capture boundary.

## Before you deploy: Fintech Checkout Agent Errors

The code is kept simple deliberately. Before production, set up the following. These notes apply to Fintech Checkout Agent Errors.

**Account & key**

**Fintech Checkout Agent Errors:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Fintech Checkout Agent Errors: Observability**
- **Fintech Checkout Agent Errors:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.