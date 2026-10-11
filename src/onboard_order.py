import argparse
import json

from marketplace_domain import BuyerUpdate, InfraiClient, SellerAsset, onboard_order


def main() -> None:
    parser = argparse.ArgumentParser(description="Check seller TXT proof before order handoff")
    parser.add_argument("domain")
    parser.add_argument("txt_name")
    parser.add_argument("txt_content")
    parser.add_argument("buyer_email")
    parser.add_argument("order_id")
    args = parser.parse_args()
    result = onboard_order(InfraiClient(), SellerAsset(args.domain, args.txt_name, args.txt_content),
                           BuyerUpdate(args.buyer_email, args.order_id))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
