import click

from awesome_rss_reader.cli.api import api
from awesome_rss_reader.cli.scheduler import scheduler
from awesome_rss_reader.cli.worker import worker


@click.group()
def main() -> None:
    ...


main.add_command(api)
main.add_command(scheduler)
main.add_command(worker)
