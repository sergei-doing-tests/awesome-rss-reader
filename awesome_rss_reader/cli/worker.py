import asyncio

import click

from awesome_rss_reader.application import di
from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.usecase.update_feed_content import UpdateFeedContentInput


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
    await uc.execute(uc_input)


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
