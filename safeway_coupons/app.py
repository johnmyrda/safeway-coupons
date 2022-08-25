import argparse
from typing import List

from .client import SafewayClient
from .config import Config
from .models import Offer, OfferStatus
from .utils import yield_delay


def parse_args() -> argparse.Namespace:
    description = 'Automatic coupon clipper for "Safeway for U" coupons'
    arg_parser = argparse.ArgumentParser(description=description)
    arg_parser.add_argument(
        "-c",
        "--accounts-config",
        dest="accounts_config",
        metavar="file",
        help=(
            "Path to configuration file containing Safeway "
            "accounts information"
        ),
    )
    arg_parser.add_argument(
        "-d",
        "--debug",
        dest="debug",
        action="count",
        default=0,
        help=(
            "Print debugging information on stdout. Specify "
            "twice to increase verbosity."
        ),
    )
    arg_parser.add_argument(
        "-n",
        "--no-email",
        dest="email",
        action="store_false",
        help=(
            "Print summary information on standard output "
            "instead of sending email"
        ),
    )
    arg_parser.add_argument(
        "-p",
        "--pretend",
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Print coupons that would be clipped, but don't clip them",
    )
    arg_parser.add_argument(
        "-S",
        "--no-sleep",
        "--no-delay",
        dest="sleep_level",
        action="count",
        default=0,
        help=(
            "Don't wait between long requests. Specify twice to never wait."
        ),
    )
    return arg_parser.parse_args()


def v2() -> None:
    args = parse_args()
    accounts = Config.load_accounts(config_file=args.accounts_config)
    clipped_offers: List[Offer] = []
    for account in accounts:
        print(account)
        swy = SafewayClient(account)
        offers = swy.get_offers()
        unclipped_offers = [
            o for o in offers if o.status == OfferStatus.Unclipped
        ]
        for offer in yield_delay(unclipped_offers, args.sleep_level):
            print(offer)
            if not args.dry_run:
                swy.clip(offer)
            clipped_offers.append(offer)
    print(f"Clipped {len(clipped_offers)} coupons")
