from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from structlog.stdlib import BoundLogger

from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.entity.user import User
from awesome_rss_reader.fastapi.depends.di import get_container
from awesome_rss_reader.fastapi.depends.logging import get_logger

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(
    container: Container = Depends(get_container),
    logger: BoundLogger = Depends(get_logger),
    token: str = Depends(oauth2_scheme),
) -> User:
    auth_settings = container.settings.auth()

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, auth_settings.secret_key, algorithms=[auth_settings.algorithm])
    except JWTError:
        logger.exception("Unable to decode JWT token", token=token)
        raise credentials_exception

    if user_uid := payload.get("sub"):
        return User(uid=user_uid)

    logger.warning("User UID not found in JWT token", token=token, payload=payload)

    raise credentials_exception
