from enum import StrEnum, auto

from pydantic import BaseModel, ConfigDict


class ApiTokenType(StrEnum):
    bearer = auto()


class ApiToken(BaseModel):
    access_token: str
    token_type: ApiTokenType

    model_config = ConfigDict(use_enum_values=True)


class ApiReleaseStats(BaseModel):
    version: str
    commit: str
