from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from jose import jwt

from awesome_rss_reader.application.settings import AuthSettings
from awesome_rss_reader.core.entity.user import User
from awesome_rss_reader.core.repository.user import UserRepository
from awesome_rss_reader.core.usecase.base import BaseUseCase


@dataclass
class AuthUserOutput:
    user: User
    token: str


@dataclass
class AuthenticateUserUseCase(BaseUseCase):
    user_repository: UserRepository
    auth_settings: AuthSettings

    async def execute(self) -> AuthUserOutput:
        user = await self.user_repository.create()
        access_token = self._generate_token_for_user(user)

        return AuthUserOutput(
            user=user,
            token=access_token,
        )

    def _generate_token_for_user(self, user: User) -> str:
        claims = {
            "sub": str(user.uid),
            "exp": datetime.now(tz=UTC) + timedelta(seconds=self.auth_settings.token_expiry_s),
        }
        return jwt.encode(
            claims, key=self.auth_settings.secret_key, algorithm=self.auth_settings.algorithm
        )
