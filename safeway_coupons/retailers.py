from __future__ import annotations

from enum import StrEnum


class Retailer(StrEnum):
    SAFEWAY = "safeway"
    JEWEL_OSCO = "jewel-osco"

    @property
    def display_name(self) -> str:
        return {
            self.SAFEWAY: "Safeway",
            self.JEWEL_OSCO: "Jewel-Osco",
        }[self]

    @property
    def origin(self) -> str:
        return {
            self.SAFEWAY: "https://www.safeway.com",
            self.JEWEL_OSCO: "https://www.jewelosco.com",
        }[self]

    @property
    def login_url(self) -> str:
        if self == self.JEWEL_OSCO:
            return f"{self.origin}/loyalty/coupons-deals"
        return self.origin

    @property
    def offers_url(self) -> str:
        return f"{self.origin}/abs/pub/xapi/offers/companiongalleryoffer"

    @property
    def clip_url(self) -> str:
        return f"{self.origin}/abs/pub/web/j4u/api/offers/clip"
