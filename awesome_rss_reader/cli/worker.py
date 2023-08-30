import asyncio

import click
import structlog

from awesome_rss_reader.application import di
from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.usecase.update_feed_content import UpdateFeedContentInput

logger = structlog.get_logger()


@click.command(context_settings={"auto_envvar_prefix": "WORKER"})
@click.option(
    "--interval",
    default=5,
    type=click.INT,
    help="Define how often to poll the queue for new feed update jobs",
)
@click.option(
    "--concurrency",
    default=50,
    type=click.INT,
    help="Define how much feed update jobs to process at a time",
)
def worker(
    interval: int,
    concurrency: int,
) -> None:
    click.echo(f"Running worker with {interval=}s and {concurrency=}")
    container = di.init()
    asyncio.run(run(container, interval, concurrency))


async def update_feed_content(container: Container, concurrency: int) -> None:
    uc_input = UpdateFeedContentInput(batch_size=concurrency)
    uc = container.use_cases.update_feed_content()
    try:
        await uc.execute(uc_input)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to update feed content", exc_info=exc)


async def run(
    container: Container,
    interval: int,
    concurrency: int,
) -> None:
    while True:
        await asyncio.gather(
            update_feed_content(container, concurrency),
            asyncio.sleep(interval),
        )
