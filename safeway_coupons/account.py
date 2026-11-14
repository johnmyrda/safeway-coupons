from __future__ import annotations

import configparser
import itertools
import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, Self

from filelock import FileLock, Timeout

from .config import config
from .errors import AccountLockedError
from .retailers import Retailer

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


@dataclass
class Account:
    username: str
    password: str = field(repr=False)
    mail_to: str
    mail_from: str
    retailer: Retailer = Retailer.SAFEWAY

    @property
    @contextmanager
    def lock(self) -> Generator[None]:
        try:
            with FileLock(self.lock_file, mode=0o600, blocking=False):
                yield
        except Timeout as e:
            raise AccountLockedError(e, self) from e

    @cached_property
    def lock_file(self) -> Path:
        return self.state_dir / "lock"

    @cached_property
    def state_dir(self) -> Path:
        path = config.state_dir / "accounts" / self.username.lower()
        # Keep Safeway's existing browser profile and lock path unchanged.
        if self.retailer != Retailer.SAFEWAY:
            path /= self.retailer.value
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def load_from_env(cls) -> Self | None:
        username = os.environ.get("SAFEWAY_ACCOUNT_USERNAME")
        password = os.environ.get("SAFEWAY_ACCOUNT_PASSWORD")
        mail_to = os.environ.get("SAFEWAY_ACCOUNT_MAIL_TO")
        mail_from = os.environ.get("SAFEWAY_ACCOUNT_MAIL_FROM")
        if username and password:
            retailer = cls.parse_retailer(
                os.environ.get("COUPON_RETAILER", Retailer.SAFEWAY)
            )
            return cls(
                username=username,
                password=password,
                mail_to=mail_to or username,
                mail_from=mail_from or username,
                retailer=retailer,
            )
        return None

    @classmethod
    def load_all_from_config(cls, config_file: Path) -> list[Self]:
        config = configparser.ConfigParser()
        with config_file.open() as f:
            config.read_file(itertools.chain(["[_no_section]"], f))
        accounts: list[Self] = []
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
            username = config.get(section, "username", fallback=section)
            retailer = cls.parse_retailer(
                config.get(section, "retailer", fallback=Retailer.SAFEWAY)
            )
            accounts.append(
                cls(
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

    @classmethod
    def load_all(cls, config_file: Path | None = None) -> list[Self]:
        account = cls.load_from_env()
        if account:
            return [account]
        if config_file:
            accounts = cls.load_all_from_config(config_file)
            if accounts:
                return accounts
        return []
