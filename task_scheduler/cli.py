"""Command-line interface for the task scheduler."""

import click
from datetime import date, timedelta
from pathlib import Path
from .loader import load_team
from .config import SchedulingConfig
from .scheduler import Scheduler
from .export import export_to_csv, export_to_ics, export_audit_log


@click.group()
def cli():
    """Task Scheduler System - Generate fair, auditable schedules for ATM and SysAid tasks."""
    pass


@cli.command()
@click.option('--team', '-t', required=True, type=click.Path(exists=True), help='Path to team YAML file')
@click.option('--config', '-c', required=True, type=click.Path(exists=True), help='Path to config YAML file')
@click.option('--start', '-s', required=True, type=str, help='Start date (YYYY-MM-DD)')
@click.option('--end', '-e', type=str, help='End date (YYYY-MM-DD). Defaults to 7 days after start.')
@click.option('--out', '-o', type=click.Path(), default='out/schedule.csv', help='Output CSV file path')
@click.option('--ics', type=click.Path(), help='Optional: also export to ICS calendar file')
@click.option('--audit', type=click.Path(), default='out/audit.log', help='Path for audit log file')
def generate(team, config, start, end, out, ics, audit):
    """Generate a schedule for the specified date range."""
    try:
        # Parse dates
        start_date = date.fromisoformat(start)
        if end:
            end_date = date.fromisoformat(end)
        else:
            end_date = start_date + timedelta(days=6)  # Default to 1 week
        
        click.echo(f"Loading team from {team}...")
        members = load_team(team)
        click.echo(f"Loaded {len(members)} team members")
        
        click.echo(f"Loading configuration from {config}...")
        scheduling_config = SchedulingConfig.from_yaml(config)
        
        click.echo(f"Generating schedule from {start_date} to {end_date}...")
        scheduler = Scheduler(scheduling_config)
        schedule = scheduler.generate_schedule(members, start_date, end_date)
        
        click.echo(f"Generated {len(schedule.assignments)} assignments")
        
        # Create output directory if needed
        out_path = Path(out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        click.echo(f"Exporting to CSV: {out}")
        export_to_csv(schedule, out)
        
        if ics:
            ics_path = Path(ics)
            ics_path.parent.mkdir(parents=True, exist_ok=True)
            click.echo(f"Exporting to ICS: {ics}")
            export_to_ics(schedule, ics, scheduling_config.timezone)
        
        # Export audit log
        audit_path = Path(audit)
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        export_audit_log(scheduler.audit.get_log(), audit)
        
        click.echo(f"\nSchedule generated successfully!")
        click.echo(f"  - CSV: {out}")
        if ics:
            click.echo(f"  - ICS: {ics}")
        click.echo(f"  - Audit log: {audit}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--team', '-t', required=True, type=click.Path(exists=True), help='Path to team YAML file')
@click.option('--config', '-c', required=True, type=click.Path(exists=True), help='Path to config YAML file')
@click.option('--date', '-d', required=True, type=str, help='Date to check (YYYY-MM-DD)')
def check(team, config, date):
    """Check availability and eligibility for a specific date."""
    try:
        check_date = date.fromisoformat(date)
        
        members = load_team(team)
        scheduling_config = SchedulingConfig.from_yaml(config)
        
        click.echo(f"\nChecking availability for {check_date}:\n")
        
        for member in members:
            is_available = member.is_available_on(check_date)
            status = "✓ Available" if is_available else "✗ Unavailable"
            click.echo(f"  {member.name}: {status}")
            
            if not is_available:
                # Explain why
                if check_date in member.unavailable_dates:
                    click.echo(f"    Reason: Marked as unavailable date")
                elif any(start <= check_date <= end for start, end in member.unavailable_ranges):
                    for start, end in member.unavailable_ranges:
                        if start <= check_date <= end:
                            click.echo(f"    Reason: Unavailable range {start} to {end}")
                else:
                    weekday = check_date.weekday()
                    if weekday not in member.office_days:
                        click.echo(f"    Reason: Not an office day (weekday {weekday})")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    cli()

