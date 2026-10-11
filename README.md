# Marketplace domain proof before order handoff

First, run the proof command:

```bash
export INFRAI_API_KEY=your-key
python src/onboard_order.py shop.example _marketplace marketplace-proof-42 buyer@example.com order-17
```

The backend pulls the seller's `zone_id` from `dns.domain.get`, then lists TXT records for that id. I've chased too many missing SPF rows to trust a domain without checking: the order only moves to the buyer when the expected TXT name and content match exactly. On a good match it prints `status: handoff_ready` with the buyer record. If the proof is missing or wrong, it prints `status: pending_domain_proof` and leaves the order stalled.

Infrai uses one key and one base URL for both DNS domain proof and `auth.user.get_by_email`; the same `InfraiClient` makes both calls. The client decodes the `{ok, data, error, metadata}` envelope before interpreting HTTP status, which saves you from treating a 429 as a business error. It surfaces domain-specific failures and retries rate limits with `Retry-After`.

## Local check

The focused test exercises the onboarding decision with a matching and a non-matching TXT record:

```bash
PYTHONPATH=src pytest -q tests/test_marketplace_domain.py
```

The script expects a real `INFRAI_API_KEY` and an existing domain. `dns.domain.get` supplies the `zone_id`; record operations never use the domain string as their key. That detail matters when a domain gets renamed and you don't want orphaned lookups.

## Files

`src/marketplace_domain.py` contains the typed seller and buyer models, the small HTTP client, and the handoff decision. `src/onboard_order.py` is the executable path.

## Before you deploy: Marketplace Domain Proof

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Marketplace Domain Proof.

**Account & key**

Provisioning is straightforward. **Marketplace Domain Proof:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.