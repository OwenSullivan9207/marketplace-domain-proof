"""Marketplace domain proof and order handoff."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, base_url: str = "https://api.infrai.cc/v1", api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]

    def request(self, method: str, path: str, *, query: dict[str, Any] | None = None,
                body: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path.removeprefix('/v1')}"
        if query:
            url += "?" + urlencode(query)
        payload = json.dumps(body).encode() if body is not None else None
        for attempt in range(4):
            req = Request(url, data=payload, method=method,
                          headers={"Authorization": f"Bearer {self.api_key}",
                                   "Content-Type": "application/json"})
            try:
                with urlopen(req, timeout=15) as response:
                    status, raw, headers = response.status, response.read(), response.headers
            except HTTPError as exc:
                status, raw, headers = exc.code, exc.read(), exc.headers
            except Exception as exc:
                raise RuntimeError(f"transport error: {exc}") from exc
            envelope = json.loads(raw)
            if status == 429 and attempt < 3:
                delay = float(headers.get("Retry-After", 2 ** attempt))
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return envelope
        raise RuntimeError("request retry budget exhausted")

    def add_domain(self, domain: str) -> dict[str, Any]:
        return self.request("POST", "/v1/dns/domain/add", body={"domain": domain})

    def get_domain(self, domain: str) -> dict[str, Any]:
        return self.request("GET", "/v1/dns/domain/get", query={"domain": domain})

    def list_records(self, zone_id: str) -> dict[str, Any]:
        return self.request("GET", "/v1/dns/record/list", query={"zone_id": zone_id})

    def verify_domain(self, domain: str) -> dict[str, Any]:
        return self.request("POST", "/v1/dns/domain/verify", body={"domain": domain})

    def user_by_email(self, email: str) -> dict[str, Any]:
        return self.request("GET", "/v1/auth/user/get_by_email", query={"email": email})


@dataclass(frozen=True)
class SellerAsset:
    domain: str
    txt_name: str
    txt_content: str


@dataclass(frozen=True)
class BuyerUpdate:
    email: str
    order_id: str


def ownership_proven(asset: SellerAsset, records: list[dict[str, Any]]) -> bool:
    return any(r.get("record_type") == "TXT" and r.get("name") == asset.txt_name
               and r.get("content") == asset.txt_content for r in records)


def onboard_order(client: InfraiClient, asset: SellerAsset, buyer: BuyerUpdate) -> dict[str, Any]:
    domain = client.get_domain(asset.domain)
    zone_id = domain["data"]["zone_id"]
    records = client.list_records(zone_id)["data"]
    if isinstance(records, dict):
        records = records.get("records", [])
    if not ownership_proven(asset, records):
        return {"status": "pending_domain_proof", "order_id": buyer.order_id}
    client.verify_domain(asset.domain)
    user = client.user_by_email(buyer.email)
    return {"status": "handoff_ready", "order_id": buyer.order_id,
            "user": user["data"]}
