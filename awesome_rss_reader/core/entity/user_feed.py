from uuid import UUID

from pydantic import AwareDatetime, BaseModel


class NewUserFeed(BaseModel):
    user_uid: UUID
    feed_id: int


class UserFeed(NewUserFeed):
    id: int  # noqa: A003
    created_at: AwareDatetime
