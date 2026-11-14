from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from safeway_coupons.account import Account
from safeway_coupons.account_settings import TomlAccounts

if TYPE_CHECKING:
    from pathlib import Path


def test_toml_accounts(tmp_path: Path) -> None:
    path = tmp_path / "accounts.toml"
    path.write_text(
        'email_sender = "sender@example.com"\n'
        "[[accounts]]\n"
        'username = "one@example.com"\n'
        'password = "first-secret"\n'
        "[[accounts]]\n"
        'username = "two@example.com"\n'
        'password = "second-secret"\n'
        'notify = "alerts@example.com"\n'
        'sender = "custom@example.com"\n'
    )
    one, two = Account.load_all(path)
    assert (one.username, one.password, one.mail_to, one.mail_from) == (
        "one@example.com",
        "first-secret",
        "one@example.com",
        "sender@example.com",
    )
    assert (two.username, two.password, two.mail_to, two.mail_from) == (
        "two@example.com",
        "second-secret",
        "alerts@example.com",
        "custom@example.com",
    )
    assert "first-secret" not in repr(TomlAccounts.load(path))


def test_env_still_takes_precedence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "accounts.toml"
    path.write_text("not valid toml")
    monkeypatch.setenv("SAFEWAY_ACCOUNT_USERNAME", "env@example.com")
    monkeypatch.setenv("SAFEWAY_ACCOUNT_PASSWORD", "env-secret")
    accounts = Account.load_all(path)
    assert len(accounts) == 1
    assert accounts[0].username == "env@example.com"


def test_ini_still_supported(tmp_path: Path) -> None:
    path = tmp_path / "accounts.ini"
    path.write_text("[ini@example.com]\npassword = ini-secret\n")
    accounts = Account.load_all(path)
    assert len(accounts) == 1
    assert accounts[0].password == "ini-secret"  # noqa: S105


@pytest.mark.parametrize(
    "content",
    [
        '[[accounts]]\nusername = "user@example.com"\n',
        '[[accounts]]\nusername = "user@example.com"\npassword = ""\n',
        """[[accounts]]
username = "user@example.com"
password = "secret-value"
unexpected = true
""",
    ],
)
def test_invalid_toml_accounts(tmp_path: Path, content: str) -> None:
    path = tmp_path / "accounts.toml"
    path.write_text(content)
    with pytest.raises(ValidationError) as exc_info:
        Account.load_all(path)
    assert "secret-value" not in str(exc_info.value)


def test_missing_toml_file_fails(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        Account.load_all(tmp_path / "missing.toml")
