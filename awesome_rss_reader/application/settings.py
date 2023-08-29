from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class ApplicationSettings(BaseSettings):
    name: str = "Awesome RSS Reader"

    release_ver: str = "development"
    release_commit: str = "unknown"

    feed_update_frequency_s: int = 5 * 60
    feed_update_retry_delay_m: list[int] = [2, 5, 8]  # noqa: RUF012
    feed_update_fetch_timeout_s: int = 10

    model_config = SettingsConfigDict(env_prefix="APP_")


class AuthSettings(BaseSettings):
    secret_key: str
    algorithm: Literal["HS256"] = "HS256"
    token_expiry_s: int = 60 * 60 * 24

    model_config = SettingsConfigDict(env_prefix="AUTH_")
