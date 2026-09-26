from enum import StrEnum


class Retailer(StrEnum):
    SAFEWAY = "safeway"
    JEWEL_OSCO = "jewel-osco"

    @property
    def display_name(self) -> str:
        match self:
            case Retailer.SAFEWAY:
                return "Safeway"
            case Retailer.JEWEL_OSCO:
                return "Jewel-Osco"

    @property
    def origin(self) -> str:
        match self:
            case Retailer.SAFEWAY:
                return "https://www.safeway.com"
            case Retailer.JEWEL_OSCO:
                return "https://www.jewelosco.com"

    @property
    def login_url(self) -> str:
        match self:
            case Retailer.SAFEWAY:
                return self.origin
            case Retailer.JEWEL_OSCO:
                return f"{self.origin}/loyalty/coupons-deals"

    @property
    def offers_url(self) -> str:
        return f"{self.origin}/abs/pub/xapi/offers/companiongalleryoffer"

    @property
    def clip_url(self) -> str:
        return f"{self.origin}/abs/pub/web/j4u/api/offers/clip"
