#!/usr/bin/env python3
"""Interactive console UI for Resy Bot"""

import json
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

import questionary
from questionary import Style
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from resy_bot.models import ResyConfig, ReservationRequest, TimedReservationRequest
from resy_bot.manager import ResyManager
from resy_bot.api_access import ResyApiAccess

# Custom style for questionary
custom_style = Style([
    ('qmark', 'fg:#673ab7 bold'),
    ('question', 'bold'),
    ('answer', 'fg:#f44336 bold'),
    ('pointer', 'fg:#673ab7 bold'),
    ('highlighted', 'fg:#673ab7 bold'),
    ('selected', 'fg:#cc5454'),
    ('separator', 'fg:#cc5454'),
    ('instruction', ''),
    ('text', ''),
    ('disabled', 'fg:#858585 italic')
])

console = Console()


def load_credentials() -> ResyConfig:
    """Load credentials from credentials.json"""
    cred_path = Path("credentials.json")
    if not cred_path.exists():
        console.print("[red]Error: credentials.json not found![/red]")
        console.print("Please create credentials.json with your Resy API credentials.")
        sys.exit(1)

    with open(cred_path) as f:
        config_data = json.load(f)

    return ResyConfig(**config_data)


def display_banner():
    """Display welcome banner"""
    banner = Text()
    banner.append("\n🍽️  ", style="bold red")
    banner.append("RESY BOT", style="bold cyan")
    banner.append(" - Restaurant Reservation Assistant\n", style="bold white")

    console.print(Panel(
        banner,
        box=box.DOUBLE,
        border_style="cyan",
        padding=(1, 2)
    ))


def search_restaurant(config: ResyConfig, last_venue_id: str = None) -> str:
    """Search for restaurant info by venue ID"""
    console.print("\n[bold cyan]🔍 Restaurant Search[/bold cyan]\n")

    venue_id = questionary.text(
        "Enter venue ID:",
        default=last_venue_id if last_venue_id else "",
        style=custom_style
    ).ask()

    if not venue_id:
        return last_venue_id

    try:
        # Create API access
        api_access = ResyApiAccess.build(config)

        with console.status("[bold green]Fetching restaurant info..."):
            import requests
            headers = {
                'Authorization': config.get_authorization(),
                'X-Resy-Auth-Token': config.token,
            }
            resp = requests.get(
                f'https://api.resy.com/3/venue',
                params={'id': venue_id},
                headers=headers
            )

        if resp.status_code != 200:
            console.print(f"[red]Error: Could not find venue {venue_id}[/red]")
            return last_venue_id

        venue_data = resp.json()

        # Display venue info
        table = Table(show_header=False, box=box.ROUNDED, border_style="cyan")
        table.add_column("Field", style="bold cyan", width=20)
        table.add_column("Value", style="white")

        table.add_row("Name", venue_data.get('name', 'N/A'))
        table.add_row("Venue ID", str(venue_id))
        table.add_row("Type", venue_data.get('type', 'N/A'))

        location = venue_data.get('location', {})
        address = f"{location.get('address_1', '')}, {location.get('locality', '')}, {location.get('region', '')}"
        table.add_row("Address", address)
        table.add_row("Neighborhood", location.get('neighborhood', 'N/A'))

        price_range = venue_data.get('price_range', 0)
        price_display = "$" * price_range if price_range else "N/A"
        table.add_row("Price Range", price_display)

        if venue_data.get('rating'):
            table.add_row("Rating", f"{venue_data['rating']:.1f}/5.0")

        console.print("\n")
        console.print(Panel(table, title="[bold]Restaurant Info[/bold]", border_style="cyan"))

        return venue_id

    except Exception as e:
        console.print(f"[red]Error fetching venue info: {e}[/red]")
        return last_venue_id


def make_reservation_interactive(config: ResyConfig, default_venue_id: str = None):
    """Interactive reservation maker"""
    console.print("\n[bold cyan]📅 Make a Reservation[/bold cyan]\n")

    # Venue ID
    venue_id = questionary.text(
        "Venue ID:",
        default=default_venue_id if default_venue_id else "",
        style=custom_style
    ).ask()

    if not venue_id:
        console.print("[yellow]Reservation cancelled[/yellow]")
        return

    # Party size
    party_size = questionary.text(
        "Party size:",
        default="2",
        validate=lambda x: x.isdigit() and int(x) > 0,
        style=custom_style
    ).ask()

    # Date selection
    date_type = questionary.select(
        "How would you like to specify the date?",
        choices=[
            "Specific date (YYYY-MM-DD)",
            "Days in advance"
        ],
        style=custom_style
    ).ask()

    ideal_date = None
    days_in_advance = None

    if "Specific date" in date_type:
        # Suggest tomorrow as default
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        ideal_date = questionary.text(
            "Reservation date (YYYY-MM-DD):",
            default=tomorrow,
            style=custom_style
        ).ask()
    else:
        days_in_advance = questionary.text(
            "Days in advance:",
            default="7",
            validate=lambda x: x.isdigit() and int(x) > 0,
            style=custom_style
        ).ask()
        days_in_advance = int(days_in_advance)

    # Time
    ideal_hour = questionary.text(
        "Ideal hour (0-23):",
        default="19",
        validate=lambda x: x.isdigit() and 0 <= int(x) <= 23,
        style=custom_style
    ).ask()

    ideal_minute = questionary.text(
        "Ideal minute (0-59):",
        default="0",
        validate=lambda x: x.isdigit() and 0 <= int(x) <= 59,
        style=custom_style
    ).ask()

    # Window
    window_hours = questionary.text(
        "Time window (hours +/-) :",
        default="1",
        validate=lambda x: x.isdigit() and int(x) > 0,
        style=custom_style
    ).ask()

    # Preference
    prefer_early = questionary.confirm(
        "Prefer earlier times if equidistant?",
        default=False,
        style=custom_style
    ).ask()

    # Seating type (optional)
    preferred_type = questionary.text(
        "Preferred seating type (leave blank for any):",
        default="",
        style=custom_style
    ).ask()

    # Drop time
    console.print("\n[cyan]When do reservations open?[/cyan]")
    expected_drop_hour = questionary.text(
        "Drop hour (0-23):",
        default="9",
        validate=lambda x: x.isdigit() and 0 <= int(x) <= 23,
        style=custom_style
    ).ask()

    expected_drop_minute = questionary.text(
        "Drop minute (0-59):",
        default="0",
        validate=lambda x: x.isdigit() and 0 <= int(x) <= 59,
        style=custom_style
    ).ask()

    # Confirmation
    console.print("\n[bold]📋 Reservation Summary:[/bold]")
    summary_table = Table(show_header=False, box=box.SIMPLE)
    summary_table.add_column("Field", style="cyan")
    summary_table.add_column("Value", style="white")

    summary_table.add_row("Venue ID", venue_id)
    summary_table.add_row("Party Size", party_size)
    summary_table.add_row("Date", ideal_date if ideal_date else f"{days_in_advance} days in advance")
    summary_table.add_row("Time", f"{ideal_hour}:{ideal_minute:0>2}")
    summary_table.add_row("Window", f"±{window_hours} hours")
    summary_table.add_row("Prefer Early", "Yes" if prefer_early else "No")
    if preferred_type:
        summary_table.add_row("Seating Type", preferred_type)
    summary_table.add_row("Drop Time", f"{expected_drop_hour}:{expected_drop_minute:0>2}")

    console.print(summary_table)
    console.print()

    confirm = questionary.confirm(
        "Proceed with reservation?",
        default=True,
        style=custom_style
    ).ask()

    if not confirm:
        console.print("[yellow]Reservation cancelled[/yellow]")
        return

    # Build reservation request
    reservation_request = ReservationRequest(
        venue_id=venue_id,
        party_size=int(party_size),
        ideal_hour=int(ideal_hour),
        ideal_minute=int(ideal_minute),
        window_hours=int(window_hours),
        prefer_early=prefer_early,
        preferred_type=preferred_type if preferred_type else None,
        ideal_date=ideal_date if ideal_date else None,
        days_in_advance=days_in_advance
    )

    timed_request = TimedReservationRequest(
        reservation_request=reservation_request,
        expected_drop_hour=int(expected_drop_hour),
        expected_drop_minute=int(expected_drop_minute)
    )

    # Make reservation
    try:
        manager = ResyManager.build(config)

        console.print("\n[bold green]🚀 Starting reservation bot...[/bold green]")
        console.print("[dim]The bot will wait until drop time and then attempt to book.[/dim]\n")

        resy_token = manager.make_reservation_at_opening_time(timed_request)

        console.print(Panel(
            f"[bold green]✅ Reservation successful![/bold green]\n\n"
            f"Resy Token: {resy_token}",
            title="Success",
            border_style="green"
        ))

    except Exception as e:
        console.print(Panel(
            f"[bold red]❌ Reservation failed[/bold red]\n\n"
            f"Error: {str(e)}",
            title="Error",
            border_style="red"
        ))


def main():
    """Main interactive loop"""
    display_banner()

    try:
        config = load_credentials()
        console.print("[green]✓ Credentials loaded successfully[/green]\n")
    except Exception as e:
        console.print(f"[red]Failed to load credentials: {e}[/red]")
        return

    last_venue_id = None

    while True:
        action = questionary.select(
            "What would you like to do?",
            choices=[
                "🔍 Search restaurant by venue ID",
                "📅 Make a reservation",
                "❌ Exit"
            ],
            style=custom_style
        ).ask()

        if "Exit" in action:
            console.print("\n[cyan]👋 Thanks for using Resy Bot![/cyan]\n")
            break
        elif "Search restaurant" in action:
            last_venue_id = search_restaurant(config, last_venue_id)
        elif "Make a reservation" in action:
            make_reservation_interactive(config, last_venue_id)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
