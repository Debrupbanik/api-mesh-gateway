"""CLI entry point for API Mesh Gateway."""

import click
from .main import run
from .config import get_settings


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """API Mesh Gateway - AI-Powered API Gateway."""
    pass


@cli.command()
def start():
    """Start the API Mesh Gateway."""
    run()


@cli.command()
def config():
    """Show current configuration."""
    settings = get_settings()
    click.echo(f"Host: {settings.host}:{settings.port}")
    click.echo(f"Redis: {settings.redis_url}")
    click.echo(f"AI Predictions: {settings.ai_predictions_enabled}")


if __name__ == "__main__":
    cli()
