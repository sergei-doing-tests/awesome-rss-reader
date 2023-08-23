from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class ApplicationSettings(BaseSettings):
    release_ver: str = "unknown"
    release_commit: str = "unknown"


class AuthSettings(BaseSettings):
    secret_key: str
    algorithm: Literal["HS256"] = "HS256"
    token_expiry_s: int = 60 * 60 * 24

    model_config = SettingsConfigDict(env_prefix="AUTH_")
