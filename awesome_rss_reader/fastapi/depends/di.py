from starlette.requests import Request

from awesome_rss_reader.application.di import Container


def get_container(request: Request) -> Container:
    return request.app.state.container
