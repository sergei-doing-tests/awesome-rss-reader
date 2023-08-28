import uuid

from pydantic import AwareDatetime, BaseModel


class NewUserPost(BaseModel):
    user_uid: uuid.UUID
    post_id: int
    read_at: AwareDatetime


class UserPost(NewUserPost):
    id: int  # noqa: A003
