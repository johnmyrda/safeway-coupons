from pathlib import Path

from .accounts import Account
from .client import SafewayClient
from .email import email_clip_results, email_error
from .errors import ClipError, Error, TooManyClipErrors
from .models import Offer, OfferStatus
from .utils import yield_delay

CLIP_ERROR_MAX = 5


class SafewayCoupons:
    def __init__(
        self,
        send_email: bool = True,
        sendmail: list[str] | None = None,
        debug_level: int = 0,
        debug_dir: Path | None = None,
        sleep_level: int = 0,
        dry_run: bool = False,
        max_clip_count: int = 0,
        max_clip_errors: int = CLIP_ERROR_MAX,
    ) -> None:
        self.send_email = send_email
        self.sendmail = sendmail or ["/usr/sbin/sendmail"]
        self.debug_level = debug_level
        self.debug_dir = debug_dir
        self.sleep_level = sleep_level
        self.dry_run = dry_run
        self.max_clip_count = max_clip_count
        self.max_clip_errors = max_clip_errors

    def clip_for_account(self, account: Account) -> None:
        if self.dry_run:
            print(
                "*** DRY RUN: Coupons will be listed, but nothing will be "
                "clipped and no email will be sent. ***"
            )
            print(f"Checking Safeway account {account.username}")
        else:
            print(f"Clipping coupons for Safeway account {account.username}")
        try:
            swy = SafewayClient(account, self.debug_dir)
            clipped_offers: list[Offer] = []
            clip_errors: list[ClipError] = []
            offers = swy.get_offers()
            unclipped_offers = [
                o for o in offers if o.status == OfferStatus.Unclipped
            ]
            if not unclipped_offers:
                if self.dry_run:
                    print(
                        "*** DRY RUN COMPLETE: No unclipped coupons found; "
                        "nothing would be clipped. ***"
                    )
                else:
                    print("Nothing to do")
                return
            rjust_size = len(str(len(unclipped_offers)))
            for i, offer in enumerate(
                yield_delay(
                    unclipped_offers, self.sleep_level, self.debug_level
                )
            ):
                progress_count = (
                    f"({str(i + 1).rjust(rjust_size, ' ')}"
                    f"/{len(unclipped_offers)}) "
                )
                try:
                    if self.dry_run:
                        print(f"{progress_count} Would clip {offer}")
                    else:
                        swy.clip(offer)
                        print(f"{progress_count} Clipped {offer}")
                    clipped_offers.append(offer)
                    if (
                        self.max_clip_count
                        and len(clipped_offers) >= self.max_clip_count
                    ):
                        print(
                            "Clip maximum count of "
                            f"{self.max_clip_count} reached"
                        )
                        break
                except ClipError as e:
                    print(f"{progress_count} {e}")
                    clip_errors.append(e)
                    if (
                        self.max_clip_errors
                        and len(clip_errors) >= self.max_clip_errors
                    ):
                        raise TooManyClipErrors(
                            e,
                            clipped_offers=clipped_offers,
                            errors=clip_errors,
                        )

            if self.dry_run:
                clipped_count = len(clipped_offers)
                coupon_label = "coupon" if clipped_count == 1 else "coupons"
                print(
                    "*** DRY RUN COMPLETE: "
                    f"{clipped_count} {coupon_label} would be clipped. ***"
                )
            else:
                print(f"Clipped {len(clipped_offers)} coupons")
            email_clip_results(
                self.sendmail,
                account,
                clipped_offers,
                error=None,
                clip_errors=clip_errors,
                debug_level=self.debug_level,
                send_email=self.send_email and not self.dry_run,
            )
        except Error as e:
            email_error(
                self.sendmail,
                account,
                error=e,
                debug_level=self.debug_level,
                send_email=self.send_email and not self.dry_run,
            )
            raise
