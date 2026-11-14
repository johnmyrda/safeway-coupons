from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
import responses

from safeway_coupons.account import Account
from safeway_coupons.client.session import SafewayBrowserSession
from safeway_coupons.config import config
from safeway_coupons.models.safeway import OfferMap
from safeway_coupons.retailers import Retailer
from safeway_coupons.safeway import SafewayCoupons

from .utils import create_account, create_offer

if TYPE_CHECKING:
    from pathlib import Path

    from requests import PreparedRequest


@pytest.mark.parametrize("retailer", list(Retailer))
def test_retailer_urls(retailer: Retailer) -> None:
    assert retailer.offers_url.startswith(retailer.origin)
    assert retailer.clip_url.startswith(retailer.origin)
    assert retailer.login_url.startswith(retailer.origin)
    if retailer == Retailer.JEWEL_OSCO:
        assert retailer.login_url.endswith("/loyalty/coupons-deals")


def test_account_configuration_and_profile_isolation(tmp_path: Path) -> None:
    path = tmp_path / "accounts.ini"
    path.write_text(
        "[safeway-account]\nusername = shared@example.com\n"
        "password = safe-password\n"
        "[jewel-account]\nretailer = jewel-osco\n"
        "username = shared@example.com\npassword = jewel-password\n"
    )
    safeway, jewel = Account.load_all_from_config(path)
    assert safeway.retailer == Retailer.SAFEWAY
    assert jewel.retailer == Retailer.JEWEL_OSCO
    assert safeway.username == jewel.username == "shared@example.com"
    assert safeway.state_dir == (
        config.state_dir / "accounts" / "shared@example.com"
    )
    assert jewel.state_dir == safeway.state_dir / "jewel-osco"
    assert jewel.lock_file != safeway.lock_file


def test_env_retailer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAFEWAY_ACCOUNT_USERNAME", "shared@example.com")
    monkeypatch.setenv("SAFEWAY_ACCOUNT_PASSWORD", "test-password")
    monkeypatch.setenv("COUPON_RETAILER", "jewel-osco")
    account = Account.load_from_env()
    assert account is not None
    assert account.retailer == Retailer.JEWEL_OSCO


def test_invalid_retailer(tmp_path: Path) -> None:
    path = tmp_path / "accounts.ini"
    path.write_text("[account]\npassword = test\nretailer = other\n")
    with pytest.raises(ValueError, match="Unknown retailer"):
        Account.load_all_from_config(path)


def test_browser_opens_jewel() -> None:
    browser = SafewayBrowserSession(create_account(Retailer.JEWEL_OSCO))
    page = MagicMock()
    with patch.object(SafewayBrowserSession, "page", page), browser:
        pass
    page.goto.assert_called_once_with(
        "https://www.jewelosco.com/loyalty/coupons-deals"
    )


@pytest.mark.usefixtures("login_success")
@pytest.mark.parametrize("dry_run", [True, False])
def test_jewel_api_routes(
    http_responses: responses.RequestsMock, *, dry_run: bool
) -> None:
    account = create_account(Retailer.JEWEL_OSCO)
    offer = create_offer("1138")
    http_responses.add(
        responses.GET,
        account.retailer.offers_url,
        json=OfferMap(offers={"1138": offer}).model_dump(
            mode="json", by_alias=True, exclude_none=True
        ),
    )

    if not dry_run:

        def clip_response(
            request: PreparedRequest,
        ) -> tuple[int, dict[str, str], str]:
            assert request.body
            body = json.loads(request.body)
            for item in body["items"]:
                item.update({"status": 1, "clipId": 1000, "checked": False})
            return (
                200,
                {"Content-Type": "application/json"},
                json.dumps(body),
            )

        http_responses.add_callback(
            responses.POST, account.retailer.clip_url, callback=clip_response
        )

    SafewayCoupons(send_email=False, dry_run=dry_run).clip_for_account(account)
    assert [call.request.method for call in http_responses.calls] == (
        ["GET"] if dry_run else ["GET", "POST"]
    )
    assert all(
        call.request.url is not None
        and call.request.url.startswith(account.retailer.origin)
        for call in http_responses.calls
    )
