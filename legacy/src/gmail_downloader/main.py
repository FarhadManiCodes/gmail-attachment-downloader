"""
Main CLI application using Typer
"""

import typer
from rich.console import Console
from rich.panel import Panel
from typing_extensions import Annotated

# TODO: Import our modules
# from .gmail_client import GmailClient
# from .downloader import AttachmentDownloader
# from .config import load_config

app = typer.Typer(
    name="gmail-downloader",
    help="Gmail Attachment Downloader - Real-time email attachment management",
    rich_markup_mode="rich"
)
console = Console()

@app.command()
def download(
    sender: Annotated[list[str], typer.Option("--sender", "-s", help="Filter by sender email")] = None,
    after: Annotated[str, typer.Option("--after", "-a", help="Download emails after date (YYYY-MM-DD)")] = None,
    extensions: Annotated[list[str], typer.Option("--extensions", "-e", help="File extensions to download")] = None,
    output: Annotated[str, typer.Option("--output", "-o", help="Output directory")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview without downloading")] = False,
):
    """Download attachments based on filters"""
    console.print(Panel.fit("🔄 Download mode - [bold]Coming soon![/bold]"))
    # TODO: Implement download logic


@app.command()
def watch(
    sender: Annotated[list[str], typer.Option("--sender", "-s", help="Monitor emails from sender")] = None,
    extensions: Annotated[list[str], typer.Option("--extensions", "-e", help="File extensions to watch")] = None,
    interval: Annotated[int, typer.Option("--interval", "-i", help="Check interval in seconds")] = 30,
):
    """Watch for new emails and download attachments in real-time"""
    console.print(Panel.fit("👀 Watch mode - [bold]Coming soon![/bold]"))
    # TODO: Implement watch logic


@app.command()
def status():
    """Show download statistics and current status"""
    console.print(Panel.fit("📊 Status - [bold]Coming soon![/bold]"))
    # TODO: Implement status display


if __name__ == "__main__":
    app()
