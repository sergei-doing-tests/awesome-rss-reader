from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class ApplicationSettings(BaseSettings):
    name: str = "Awesome RSS Reader"
    release_ver: str = "development"
    release_commit: str = "unknown"

    model_config = SettingsConfigDict(env_prefix="APP_")


class AuthSettings(BaseSettings):
    secret_key: str
    algorithm: Literal["HS256"] = "HS256"
    token_expiry_s: int = 60 * 60 * 24

    model_config = SettingsConfigDict(env_prefix="AUTH_")
