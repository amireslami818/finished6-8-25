#!/usr/bin/env python3
"""
Step 7 Rich - Beautiful HTML Display with Simple Log Output

This script generates THREE SEPARATE OUTPUTS from Step 7:

1. step7_matches.html (from step7_rich.py) - Beautiful HTML output
   - Rich formatted with colors, emojis, and styling
   - View in browser or VS Code preview
   - White background with colored odds (green/orange/red)
   - Centered competition headers
   - Box-drawing UI elements
   
2. step7_simple.log (from step7_rich.py) - Simple text log
   - Clean, minimal format without special characters
   - Easy to read in any text editor
   - Shows competition, matches, scores, and odds
   - Suitable for parsing or quick viewing
   
3. step7_matches.log (from step7.py) - Detailed log output
   - Uses Unicode box-drawing characters
   - Emoji icons for visual appeal
   - More detailed formatting
   - Original Step 7 output format

All three files are generated when running the Step 7 display scripts.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
import pytz
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.logging import RichHandler
from rich.layout import Layout
from rich import box
from rich.progress import track
from rich.align import Align

# Status mapping with emojis
STATUS_MAP = {
    0: "Not Started",
    1: "Not Started",
    2: "First Half ⚽",
    3: "Half-Time ⏸️",
    4: "Second Half ⚽",
    5: "Overtime ⏱️",
    6: "Overtime ⏱️",
    7: "Penalties 🥅"
}

# Weather descriptions
WEATHER_DESCRIPTIONS = {
    0: "Clear",
    1: "Partially cloudy",
    2: "Overcast",
    3: "Light rain",
    4: "Heavy rain",
    5: "Thunderstorm",
    6: "Light snow",
    7: "Heavy snow",
    8: "Fog"
}

def load_step2_data():
    """Load processed data from step2.json"""
    step2_file = Path("step2.json")
    if not step2_file.exists():
        return []
    
    with open(step2_file, 'r') as f:
        data = json.load(f)
        return data.get('summaries', [])

def filter_inplay_matches(matches):
    """Filter matches by in-play status"""
    inplay_statuses = [2, 3, 4, 5, 6, 7]
    return [m for m in matches if m.get('status_id') in inplay_statuses]

def group_by_competition(matches):
    """Group matches by competition"""
    competitions = {}
    for match in matches:
        comp_id = match.get('competition_id')
        if comp_id not in competitions:
            competitions[comp_id] = {
                'name': match.get('competition', 'Unknown'),
                'country': match.get('country', 'Unknown'),
                'matches': []
            }
        competitions[comp_id]['matches'].append(match)
    
    # Sort matches within each competition by status_id
    for comp in competitions.values():
        comp['matches'].sort(key=lambda x: x.get('status_id', 999))
    
    return competitions

def load_daily_count():
    """Load daily match count"""
    counter_file = Path("daily_match_counter.json")
    if not counter_file.exists():
        return 0
    
    with open(counter_file, 'r') as f:
        data = json.load(f)
        return data.get('daily_fetch_count', 0)

def format_american_odds(value):
    """Format American odds with proper sign"""
    try:
        val = float(value)
        if val > 0:
            return f"+{int(val)}"
        else:
            return str(int(val))
    except:
        return "N/A"

def create_match_panel(console, match, match_num=None, total_matches=None):
    """Create a Rich panel for a single match"""
    # Extract data
    home = match.get('home', 'Unknown')
    away = match.get('away', 'Unknown')
    score = match.get('score', '0-0')
    status_id = match.get('status_id', 0)
    status_desc = STATUS_MAP.get(status_id, f"Unknown ({status_id})")
    
    # Get odds data
    odds_company = match.get('odds_company_name', 'N/A')
    money_line = match.get('money_line_american', [])
    spread = match.get('spread_american', [])
    over_under = match.get('over_under_american', [])
    
    # Get environment data
    env = match.get('environment', {})
    weather = env.get('weather_description', 'Unknown')
    temp_f = env.get('temperature_fahrenheit', 'N/A')
    wind_mph = env.get('wind_speed_mph', 'N/A')
    
    # Build content string
    content_lines = []
    
    # Score
    content_lines.append(f"[bold cyan]📊 SCORE: {score}[/bold cyan]")
    content_lines.append("")
    
    # Money Line
    if money_line and len(money_line) > 0:
        latest_ml = money_line[-1]
        if len(latest_ml) >= 5:
            content_lines.append(f"[bold]💰 Money Line ({odds_company}):[/bold]")
            content_lines.append(f"   Home: [green]{format_american_odds(latest_ml[2])}[/green]")
            content_lines.append(f"   Draw: [yellow]{format_american_odds(latest_ml[3])}[/yellow]")
            content_lines.append(f"   Away: [red]{format_american_odds(latest_ml[4])}[/red]")
            content_lines.append("")
    
    # Spread
    if spread and len(spread) > 0:
        latest_spread = spread[-1]
        if len(latest_spread) >= 5:
            content_lines.append(f"[bold]📈 Spread:[/bold]")
            content_lines.append(f"   Home: [green]{format_american_odds(latest_spread[2])}[/green]")
            content_lines.append(f"   Line: [white]{latest_spread[3]}[/white]")
            content_lines.append(f"   Away: [red]{format_american_odds(latest_spread[4])}[/red]")
            content_lines.append("")
    
    # Over/Under
    if over_under and len(over_under) > 0:
        latest_ou = over_under[-1]
        if len(latest_ou) >= 5:
            content_lines.append(f"[bold]📊 Over/Under:[/bold]")
            content_lines.append(f"   Over: [green]{format_american_odds(latest_ou[2])}[/green]")
            content_lines.append(f"   Total: [white]{latest_ou[3]}[/white]")
            content_lines.append(f"   Under: [red]{format_american_odds(latest_ou[4])}[/red]")
            content_lines.append("")
    
    # Environment
    content_lines.append(f"[yellow]🌤️  Weather: {weather} | Temp: {temp_f} | Wind: {wind_mph}[/yellow]")
    
    # Join all lines
    content_str = "\n".join(content_lines)
    
    # Create panel with team names and status
    title = f"{home} vs {away}"
    if match_num and total_matches:
        title = f"[{match_num} of {total_matches}] {title}"
    subtitle = status_desc
    
    return Panel(
        content_str,
        title=title,
        subtitle=subtitle,
        style="green",
        box=box.ROUNDED,
        padding=(1, 2)
    )

def setup_simple_logger():
    """Setup a simple logger for plain text output"""
    logger = logging.getLogger('step7_simple')
    logger.setLevel(logging.INFO)
    
    # Create handler for simple log file
    handler = logging.FileHandler('step7_simple.log', mode='w', encoding='utf-8')
    handler.setLevel(logging.INFO)
    
    # Simple format without timestamps (since we add them in the message)
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    return logger

def main():
    """Main function"""
    # Setup Rich console with recording
    console = Console(record=True, width=120)
    
    # Setup simple logger
    simple_logger = setup_simple_logger()
    
    # Get current time in Eastern
    eastern = pytz.timezone('America/New_York')
    now = datetime.now(eastern)
    
    # Print header
    console.print("\n[bold magenta]Step 7 - Football Match Display (Rich HTML Output)[/bold magenta]")
    console.print(f"[dim]{now.strftime('%Y-%m-%d %I:%M:%S %p ET')}[/dim]\n")
    
    # Log start to simple logger
    simple_logger.info(f"Step 7 - Match Display Report")
    simple_logger.info(f"Generated at: {now.strftime('%Y-%m-%d %I:%M:%S %p ET')}")
    
    # Load data
    matches = load_step2_data()
    if not matches:
        console.print("[red]No match data found in step2.json[/red]")
        simple_logger.info("No match data found in step2.json")
        return
    
    # Filter in-play matches
    inplay_matches = filter_inplay_matches(matches)
    total_matches = len(inplay_matches)
    daily_count = load_daily_count()
    
    # Log total matches to simple logger
    simple_logger.info(f"Total In-Play Matches: {total_matches}")
    simple_logger.info("=" * 80)
    simple_logger.info("")
    
    # Print stats
    stats_table = Table(title="📊 Match Statistics", box=box.ROUNDED)
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="bold green")
    stats_table.add_row("Active In-Play Matches", str(total_matches))
    stats_table.add_row("Daily Fetches", str(daily_count))
    console.print(stats_table)
    console.print("")
    
    # Group by competition
    competitions = group_by_competition(inplay_matches)
    
    # Sort competitions alphabetically by name
    sorted_competitions = sorted(competitions.items(), key=lambda x: x[1]['name'])
    
    # Display matches by competition
    for comp_id, comp_data in sorted_competitions:
        # Competition header
        comp_content = Align.center(
            f"[bold]{comp_data['name']}[/bold]\n[dim]📍 {comp_data['country']} | 📋 {len(comp_data['matches'])} matches[/dim]"
        )
        comp_panel = Panel(
            comp_content,
            style="blue",
            box=box.DOUBLE,
            expand=True,
            padding=(0, 2)
        )
        console.print(comp_panel)
        
        # Simple logger output for competition
        simple_logger.info(f"Competition: {comp_data['name']}")
        simple_logger.info(f"Country: {comp_data['country']}")
        simple_logger.info(f"Matches: {len(comp_data['matches'])}")
        simple_logger.info("-" * 80)
        
        # Display matches with numbering
        total_matches = len(comp_data['matches'])
        for idx, match in enumerate(comp_data['matches'], 1):
            match_panel = create_match_panel(console, match, match_num=idx, total_matches=total_matches)
            console.print(match_panel)
            
            # Simple logger output for match
            simple_logger.info(f"  [{idx} of {total_matches}] {match.get('home', 'Unknown')} vs {match.get('away', 'Unknown')}")
            simple_logger.info(f"  Score: {match.get('score', '0-0')} | Status: {STATUS_MAP.get(match.get('status_id', 0), f"Unknown ({match.get('status_id', 0)})")}")
            
            # Get latest odds
            money_line = match.get('money_line_american', [])
            spread = match.get('spread_american', [])
            over_under = match.get('over_under_american', [])
            
            if money_line and len(money_line) > 0:
                latest_ml = money_line[-1]
                if len(latest_ml) >= 5:
                    simple_logger.info(f"  Money Line: {format_american_odds(latest_ml[2]):>6} / {format_american_odds(latest_ml[3]):>6} / {format_american_odds(latest_ml[4]):>6}")
            if spread and len(spread) > 0:
                latest_spread = spread[-1]
                if len(latest_spread) >= 5:
                    simple_logger.info(f"  Spread: {format_american_odds(latest_spread[2]):>6} ({latest_spread[3]:>6}) / {format_american_odds(latest_spread[4]):>6}")
            if over_under and len(over_under) > 0:
                latest_ou = over_under[-1]
                if len(latest_ou) >= 5:
                    simple_logger.info(f"  O/U: {format_american_odds(latest_ou[2]):>6} ({latest_ou[3]:>5}) / {format_american_odds(latest_ou[4]):>6}")
            simple_logger.info("")
        
        console.print("")  # Space between competitions
        simple_logger.info("")
    
    # Status breakdown
    status_counts = {}
    for match in inplay_matches:
        status_id = match.get('status_id', 0)
        status_desc = STATUS_MAP.get(status_id, f"Unknown ({status_id})")
        status_counts[status_desc] = status_counts.get(status_desc, 0) + 1
    
    # Footer with status breakdown
    footer_table = Table(title="🎯 Match Status Breakdown", box=box.ROUNDED)
    footer_table.add_column("Status", style="cyan")
    footer_table.add_column("Count", style="bold")
    
    for status, count in sorted(status_counts.items()):
        footer_table.add_row(status, str(count))
    
    console.print(footer_table)
    
    # Export to HTML
    html_content = console.export_html(inline_styles=True)
    
    # Wrap with proper HTML structure and white background styling
    full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Step 7 - Football Match Display</title>
    <style>
        body {{
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            background-color: white;
            color: black;
            padding: 20px;
            line-height: 1.4;
        }}
        pre {{
            font-family: inherit;
            margin: 0;
            background-color: white;
            color: black;
        }}
        /* Override Rich's dark theme colors */
        .r1, .r2, .r3, .r4, .r5, .r6, .r7, .r8, .r9, .r10, .r11, .r12, .r13, .r14, .r15, .r16 {{
            color: black !important;
        }}
        /* Keep special colors for odds */
        .r10 {{ color: #0066cc !important; font-weight: bold; }} /* Blue for headers */
        .r11 {{ color: #666666 !important; }} /* Gray for subheaders */
        .r13 {{ color: #006600 !important; font-weight: bold; }} /* Green for home odds */
        .r14 {{ color: #cc6600 !important; font-weight: bold; }} /* Orange for draw odds */
        .r15 {{ color: #cc0000 !important; font-weight: bold; }} /* Red for away odds */
        .r16 {{ color: #0066cc !important; }} /* Blue for line values */
    </style>
</head>
<body>
{html_content}
</body>
</html>"""
    
    # Save HTML file
    output_file = Path("step7_matches.html")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    console.print(f"\n✅ [bold green]Step 7 completed![/bold green]")
    console.print(f"   [cyan]HTML output saved to:[/cyan] {output_file.absolute()}")
    console.print(f"   [cyan]Simple log saved to:[/cyan] {Path('step7_simple.log').absolute()}")
    console.print(f"   [cyan]Total matches displayed:[/cyan] {total_matches}")
    console.print(f"   [dim]Open the HTML file in VS Code or a browser to view the beautiful output![/dim]")

if __name__ == "__main__":
    main()
