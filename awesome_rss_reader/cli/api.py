import click
import uvicorn


@click.command(context_settings={"auto_envvar_prefix": "API"})
@click.option("--host", default="127.0.0.1", help="Host to run API server on")
@click.option("--port", default=8000, type=click.INT, help="Port to run API server on")
@click.option(
    "--log-level",
    default="info",
    type=click.Choice(["debug", "info", "warning", "error", "critical"]),
)
@click.option(
    "--reload",
    default=False,
    is_flag=True,
    help="Instruct uvicorn to reload on code changes",
)
def api(
    host: str,
    port: int,
    log_level: str,
    reload: bool,  # noqa: FBT001
) -> None:
    click.echo(f"Running API server on {host}:{port} with logging level={log_level}")

    uvicorn.run(
        "awesome_rss_reader.fastapi.entrypoint:get_asgi_app",
        factory=True,
        host=host,
        port=port,
        log_level=log_level,
        reload=reload,
    )
