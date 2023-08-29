import asyncio

import click

from awesome_rss_reader.application import di
from awesome_rss_reader.application.di import Container
from awesome_rss_reader.core.usecase.schedule_feed_update import ScheduleFeedUpdateInput


@click.command(context_settings={"auto_envvar_prefix": "SCHEDULER"})
@click.option(
    "--interval",
    default=30,
    type=click.INT,
    help="Define how often to run the job scheduler",
)
@click.option(
    "--concurrency",
    default=20,
    type=click.INT,
    help="Define how much jobs to schedule at a time",
)
def scheduler(
    interval: int,
    concurrency: int,
) -> None:
    click.echo(f"Running scheduler with {interval=}s and {concurrency=}")
    container = di.init()
    asyncio.run(run(container, interval, concurrency))


async def schedule_feed_update(container: Container, concurrency: int) -> None:
    uc_input = ScheduleFeedUpdateInput(batch_size=concurrency)
    uc = container.use_cases.schedule_feed_update()
    await uc.execute(uc_input)


async def run(
    container: Container,
    interval: int,
    concurrency: int,
) -> None:
    while True:
        await asyncio.gather(
            schedule_feed_update(container, concurrency),
            asyncio.sleep(interval),
        )
