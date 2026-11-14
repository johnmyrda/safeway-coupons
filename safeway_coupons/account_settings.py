from __future__ import annotations

from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, ConfigDict, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import TomlConfigSettingsSource

if TYPE_CHECKING:
    from pathlib import Path


class TomlAccount(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    username: str = Field(min_length=1)
    password: SecretStr = Field(min_length=1)
    notify: str | None = None
    sender: str | None = None


class TomlAccounts(BaseSettings):
    model_config = SettingsConfigDict(
        extra="forbid", hide_input_in_errors=True
    )

    email_sender: str | None = None
    accounts: list[TomlAccount]

    @classmethod
    def load(cls, path: Path) -> Self:
        # An explicitly supplied file is the only source here. Environment
        # accounts retain their existing precedence in Account.load_all().
        source = TomlConfigSettingsSource(cls, toml_file=path)
        return cls.model_validate(source())
