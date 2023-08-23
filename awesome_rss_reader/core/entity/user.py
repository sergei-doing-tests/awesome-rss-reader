from uuid import UUID

from pydantic import BaseModel


class User(BaseModel):
    uid: UUID
