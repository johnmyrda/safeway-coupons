import configparser
import itertools
import os

from .accounts import Account
from .retailers import Retailer


class Config:
    @classmethod
    def load_accounts(cls, config_file: str | None = None) -> list[Account]:
        account = cls.load_account_from_env()
        if account:
            return [account]
        if config_file:
            accounts = cls.load_accounts_from_config(config_file)
            if accounts:
                return accounts
        return []

    @classmethod
    def load_account_from_env(cls) -> Account | None:
        username = os.environ.get("SAFEWAY_ACCOUNT_USERNAME")
        password = os.environ.get("SAFEWAY_ACCOUNT_PASSWORD")
        mail_to = os.environ.get("SAFEWAY_ACCOUNT_MAIL_TO")
        mail_from = os.environ.get("SAFEWAY_ACCOUNT_MAIL_FROM")
        if username and password:
            retailer = cls.parse_retailer(
                os.environ.get("COUPON_RETAILER", Retailer.SAFEWAY)
            )
            return Account(
                username=username,
                password=password,
                mail_to=mail_to or username,
                mail_from=mail_from or username,
                retailer=retailer,
            )
        return None

    @classmethod
    def load_accounts_from_config(cls, config_file: str) -> list[Account]:
        config = configparser.ConfigParser()
        with open(config_file) as f:
            config.read_file(itertools.chain(["[_no_section]"], f))
        accounts: list[Account] = []
        mail_from = None
        for section in config.sections():
            if section in ["_no_section", "_global"]:
                if config.has_option(section, "email_sender"):
                    mail_from = config.get(section, "email_sender")
                continue
            mail_to = (
                config.get(section, "notify")
                if config.has_option(section, "notify")
                else None
            )
            username = config.get(section, "username", fallback=str(section))
            retailer = cls.parse_retailer(
                config.get(
                    section,
                    "retailer",
                    fallback=Retailer.SAFEWAY,
                )
            )
            accounts.append(
                Account(
                    username=username,
                    password=config.get(section, "password"),
                    mail_to=mail_to or username,
                    mail_from=mail_from or username,
                    retailer=retailer,
                )
            )
        return accounts

    @staticmethod
    def parse_retailer(value: str) -> Retailer:
        try:
            return Retailer(value.lower())
        except ValueError as e:
            choices = ", ".join(retailer.value for retailer in Retailer)
            raise ValueError(
                f"Unknown retailer {value!r}; expected one of: {choices}"
            ) from e
