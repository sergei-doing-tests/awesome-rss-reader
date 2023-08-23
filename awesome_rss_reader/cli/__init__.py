import click

from awesome_rss_reader.cli.api import api


@click.group()
def main() -> None:
    ...


main.add_command(api)
