from pathlib import Path

import pytest

from safeway_coupons.config import Config
from safeway_coupons.retailers import Retailer


@pytest.mark.parametrize(
    ("retailer", "display_name", "origin", "login_url"),
    [
        (
            Retailer.SAFEWAY,
            "Safeway",
            "https://www.safeway.com",
            "https://www.safeway.com",
        ),
        (
            Retailer.JEWEL_OSCO,
            "Jewel-Osco",
            "https://www.jewelosco.com",
            "https://www.jewelosco.com/loyalty/coupons-deals",
        ),
    ],
)
def test_retailer_profile(
    retailer: Retailer,
    display_name: str,
    origin: str,
    login_url: str,
) -> None:
    assert retailer.display_name == display_name
    assert retailer.origin == origin
    assert retailer.login_url == login_url
    assert retailer.offers_url == (
        f"{origin}/abs/pub/xapi/offers/companiongalleryoffer"
    )
    assert retailer.clip_url == f"{origin}/abs/pub/web/j4u/api/offers/clip"


def test_account_retailer_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COUPON_RETAILER", "invalid-unused-value")
    config = tmp_path / "accounts"
    config.write_text(
        "[safeway-account]\n"
        "username = shared@example.com\n"
        "password = safe-password\n"
        "\n"
        "[jewel-account]\n"
        "retailer = jewel-osco\n"
        "username = shared@example.com\n"
        "password = jewel-password\n"
    )

    accounts = Config.load_accounts_from_config(str(config))

    assert [account.retailer for account in accounts] == [
        Retailer.SAFEWAY,
        Retailer.JEWEL_OSCO,
    ]
    assert [account.username for account in accounts] == [
        "shared@example.com",
        "shared@example.com",
    ]


def test_environment_retailer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAFEWAY_ACCOUNT_USERNAME", "jewel@example.com")
    monkeypatch.setenv("SAFEWAY_ACCOUNT_PASSWORD", "test-password")
    monkeypatch.setenv("COUPON_RETAILER", "jewel-osco")

    account = Config.load_account_from_env()

    assert account is not None
    assert account.retailer == Retailer.JEWEL_OSCO


def test_unknown_retailer(tmp_path: Path) -> None:
    config = tmp_path / "accounts"
    config.write_text(
        "[test@example.com]\nretailer = unknown\npassword = test-password\n"
    )

    with pytest.raises(ValueError, match="Unknown retailer 'unknown'"):
        Config.load_accounts_from_config(str(config))
