from starlette.requests import Request
from structlog.stdlib import BoundLogger


def get_logger(request: Request) -> BoundLogger:
    return request.app.state.logger
