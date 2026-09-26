from dataclasses import dataclass, field

from .retailers import Retailer


@dataclass
class Account:
    username: str
    password: str = field(repr=False)
    mail_to: str
    mail_from: str
    retailer: Retailer = Retailer.SAFEWAY
