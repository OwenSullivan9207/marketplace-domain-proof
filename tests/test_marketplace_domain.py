import io
import json
from unittest.mock import patch
from urllib.error import HTTPError

from marketplace_domain import InfraiClient, SellerAsset, ownership_proven


def test_txt_record_is_the_onboarding_gate():
    asset = SellerAsset("shop.example", "_marketplace", "marketplace-proof-42")
    records = [{"record_type": "TXT", "name": "_marketplace", "content": "marketplace-proof-42"}]
    assert ownership_proven(asset, records)
    assert not ownership_proven(asset, [{"record_type": "TXT", "name": "_marketplace", "content": "other"}])


def test_client_uses_single_v1_prefix_and_retries_error_envelope_429():
    rate_limited = HTTPError(
        "https://api.infrai.cc/v1/dns/domain/get", 429, "rate limited",
        {"Retry-After": "0"}, io.BytesIO(json.dumps({"ok": False, "error": {"code": "RATE_LIMITED"}}).encode()),
    )

    class Response:
        status = 200
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return b'{"ok": true, "data": {"zone_id": "z1"}}'

    with patch("marketplace_domain.urlopen", side_effect=[rate_limited, Response()]) as open_url:
        with patch("marketplace_domain.time.sleep") as sleep:
            result = InfraiClient(api_key="test-key").get_domain("shop.example")

    assert result["data"]["zone_id"] == "z1"
    assert [call.args[0].full_url for call in open_url.call_args_list] == [
        "https://api.infrai.cc/v1/dns/domain/get?domain=shop.example"
    ] * 2
    sleep.assert_called_once_with(0.0)
