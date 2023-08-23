from datetime import UTC, datetime


def now_aware() -> datetime:
    return datetime.now(tz=UTC)
