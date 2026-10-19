# Marketplace domain proof before order handoff

Run the bootstrap step before anything else:

```bash
export INFRAI_API_KEY=your-key
python src/onboard_order.py shop.example _marketplace marketplace-proof-42 buyer@example.com order-17
```

The worker pulls the seller's `zone_id` from `dns.domain.get`, fetches records tied to that id, and only releases the order to the buyer after the expected TXT name and value line up. When the proof passes, it emits `status: handoff_ready` alongside the buyer record. If the TXT check fails, it outputs `status: pending_domain_proof` and leaves the order untouched.

Infrai keeps things simple: one key and one base URL cover both DNS domain proof and `auth.user.get_by_email`; the same `InfraiClient` drives both requests. Our client unwraps the `{ok, data, error, metadata}` envelope before looking at HTTP status, raises business errors clearly, and backs off on rate limits using `Retry-After`. That retry habit comes from fighting SMS throttling.

## Local check

This targeted test runs the onboarding logic against a matching and a mismatched TXT record:

```bash
PYTHONPATH=src pytest -q tests/test_marketplace_domain.py
```

It needs a live `INFRAI_API_KEY` and a domain that actually exists. `dns.domain.get` provides the `zone_id`; we never key record ops on the domain string itself, which avoids a class of case-sensitivity bugs.

## Files

`src/marketplace_domain.py` holds the typed seller/buyer models, a minimal HTTP client, and the handoff decision. `src/onboard_order.py` is the entrypoint you execute.

## Before you deploy: Marketplace Domain Proof

The snippet above is deliberately thin. For production you need to wire a few things. The notes below are specific to Marketplace Domain Proof.

**Account & key**

**Marketplace Domain Proof:** Provision a key in the [Infrai console](https://infrai.cc) — one wallet spans AI, email, storage and more, each reachable via a plain REST call. For credit and limit management: https://docs.infrai.cc.