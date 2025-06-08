#!/usr/bin/env python3
"""
Step 7: Pretty Display for In-Play Matches

This script generates ONE of the THREE STEP 7 OUTPUTS:

1. step7_matches.html (from step7_rich.py) - Beautiful HTML output
   - Rich formatted with colors, emojis, and styling
   - View in browser or VS Code preview
   
2. step7_simple.log (from step7_rich.py) - Simple text log
   - Clean, minimal format without special characters
   - Easy to read in any text editor
   
3. step7_matches.log (from THIS script - step7.py) - Detailed log output
   - Uses Unicode box-drawing characters (╔═╗╠╣╚╝┏━┓┣┫┗┛)
   - Emoji icons (⚽🏆🌍📊💰📈🌤️📅🎯🔍) for visual appeal
   - Beautiful formatted display that looks like a modern sports betting UI
   - Shows competition headers, match details, scores, odds, and environment

To generate all outputs:
- Run step7.py for step7_matches.log
- Run step7_rich.py for both step7_matches.html and step7_simple.log
"""

import json
import logging
from datetime import datetime
from pathlib import Path
import pytz

# ---------------------------------------------------------------------------
# Constants and Configuration
# ---------------------------------------------------------------------------
TZ = pytz.timezone("America/New_York")
BASE_DIR = Path(__file__).resolve().parent
STEP2_FILE = BASE_DIR / "step2.json"
LOG_FILE = BASE_DIR / "step7_matches.log"
DAILY_COUNTER_FILE = BASE_DIR / "daily_match_counter.json"

# Status codes we care about (in-play matches)
STATUS_FILTER = {2, 3, 4, 5, 6, 7}

# Status descriptions
STATUS_MAP = {
    0: "Abnormal",
    1: "Not Started",
    2: "First Half",
    3: "Half-Time", 
    4: "Second Half",
    5: "Overtime",
    6: "Overtime",
    7: "Penalty Shootout",
    8: "Finished",
    9: "Delayed",
    10: "Interrupted",
    11: "Cut in Half",
    12: "Cancelled",
    13: "TBD"
}

# ---------------------------------------------------------------------------
# Logger Setup
# ---------------------------------------------------------------------------
def setup_logger():
    """Setup a logger that writes beautiful formatted output to file"""
    logger = logging.getLogger('step7_display')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    
    # File handler for pretty output
    file_handler = logging.FileHandler(LOG_FILE, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # Simple formatter - just the message, no timestamps
    formatter = logging.Formatter('%(message)s')
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    return logger

# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------
def get_eastern_time():
    """Get current time in Eastern timezone"""
    return datetime.now(TZ).strftime("%Y-%m-%d %I:%M:%S %p ET")

def get_daily_fetch_count():
    """Get today's fetch count from counter file"""
    try:
        if DAILY_COUNTER_FILE.exists():
            with open(DAILY_COUNTER_FILE, 'r') as f:
                data = json.load(f)
                today = datetime.now(TZ).strftime("%Y-%m-%d")
                return data.get(today, {}).get("count", 0)
    except:
        pass
    return 0

def format_score(home_score, away_score):
    """Format score with visual styling"""
    return f"{home_score} - {away_score}"

def format_american_odds(odds_value):
    """Convert decimal/HK odds to American format with proper + or -"""
    try:
        odds = float(odds_value)
        if odds <= 0:
            return "N/A"
        
        # For decimal odds (money line)
        if odds >= 1.0:
            if odds >= 2.0:
                american = int((odds - 1) * 100)
                return f"+{american}"
            else:
                american = int(-100 / (odds - 1))
                return f"{american}"
        # For HK odds (spread, o/u, corners)
        else:
            american = int(-100 / odds)
            return f"{american}"
    except:
        return "N/A"

# ---------------------------------------------------------------------------
# Display Functions
# ---------------------------------------------------------------------------
def write_header(logger, total_matches, fetch_count):
    """Write beautiful header"""
    logger.info("╔" + "═" * 78 + "╗")
    logger.info("║" + " " * 20 + "⚽ LIVE FOOTBALL MATCHES ⚽" + " " * 32 + "║")
    logger.info("╠" + "═" * 78 + "╣")
    logger.info(f"║ 📅 Generated: {get_eastern_time():<45} ║")
    logger.info(f"║ 🎯 Active Matches: {total_matches:<10} │ 📊 Daily Fetches: {fetch_count:<10} ║")
    logger.info(f"║ 🔍 Status Filter: First Half, Half-Time, Second Half, OT, Penalties" + " " * 10 + "║")
    logger.info("╚" + "═" * 78 + "╝")
    logger.info("")

def write_competition_header(logger, comp_name, country, match_count):
    """Write a competition section header"""
    logger.info("")
    logger.info("┌" + "─" * 78 + "┐")
    
    # Center the competition name with trophy emoji
    comp_line = f"🏆 {comp_name}"
    country_line = f"🌍 {country}"
    # Calculate padding for centering
    comp_padding = (78 - len(comp_line) - len(country_line) - 5) // 2
    centered_line = f"{comp_line}{' ' * comp_padding}{country_line}"
    # Ensure the line is exactly 78 chars
    centered_line = f"{centered_line:<78}"
    logger.info(f"│ {centered_line} │")
    
    # Center the match count
    count_line = f"📋 Matches: {match_count}"
    count_padding = (78 - len(count_line)) // 2
    centered_count = f"{' ' * count_padding}{count_line}"
    centered_count = f"{centered_count:<78}"
    logger.info(f"│ {centered_count} │")
    
    logger.info("└" + "─" * 78 + "┘")

def write_match(logger, match, match_num=None, total_matches=None):
    """Write a single match with beautiful formatting"""
    # Box width constants
    BOX_WIDTH = 72  # Total width including borders
    INNER_WIDTH = 70  # Width between borders
    
    # Extract data
    home = match.get('home', 'Unknown')[:25]  # Limit to 25 chars
    away = match.get('away', 'Unknown')[:25]  # Limit to 25 chars
    score = match.get('score', '0-0')
    status_id = match.get('status_id', 0)
    status_desc = STATUS_MAP.get(status_id, f"Unknown ({status_id})")[:15]
    
    # Get odds data
    odds_company = match.get('odds_company_name', 'N/A')
    odds_company = str(odds_company)[:8] if odds_company else 'N/A'
    
    # Get latest odds from arrays
    money_line = match.get('money_line_american', [])
    spread = match.get('spread_american', [])
    over_under = match.get('over_under_american', [])
    
    # Get environment data
    env = match.get('environment', {})
    weather = env.get('weather_description', 'Unknown')
    temp_f = env.get('temperature_fahrenheit', 'N/A')
    wind_mph = env.get('wind_speed_mph', 'N/A')
    
    # Match header with fixed width formatting
    logger.info("")
    logger.info("  " + "┏" + "━" * INNER_WIDTH + "┓")
    
    # Format team vs line
    team_line = f"{home:<25} vs {away:<25}"
    status_part = f"{status_desc:<15}"
    middle_content = f"{team_line} ┃ {status_part}"
    if match_num and total_matches:
        match_header = f"[{match_num} of {total_matches}] {middle_content}"
    else:
        match_header = middle_content
    logger.info(f"  ┃ {match_header:<{INNER_WIDTH}} ┃")
    
    logger.info("  " + "┣" + "━" * INNER_WIDTH + "┫")
    
    # Score line
    score_text = f"📊 SCORE: {score:^59}"
    logger.info(f"  ┃ {score_text:<{INNER_WIDTH}} ┃")
    
    # Betting Odds
    if money_line and len(money_line) > 0:
        latest_ml = money_line[-1]  # Get latest odds
        if len(latest_ml) >= 5:
            home_ml = str(latest_ml[2])[:10]
            draw_ml = str(latest_ml[3])[:10]
            away_ml = str(latest_ml[4])[:10]
            logger.info("  " + "┣" + "━" * INNER_WIDTH + "┫")
            
            ml_title = f"💰 MONEY LINE ({odds_company}):"
            logger.info(f"  ┃ {ml_title:<{INNER_WIDTH}} ┃")
            
            odds_line = f"   Home: {home_ml:<10} │ Draw: {draw_ml:<10} │ Away: {away_ml:<25}"
            logger.info(f"  ┃ {odds_line:<{INNER_WIDTH}} ┃")
    
    if spread and len(spread) > 0:
        latest_spread = spread[-1]
        if len(latest_spread) >= 5:
            home_spread = str(latest_spread[2])[:10]
            handicap = str(latest_spread[3])[:10]
            away_spread = str(latest_spread[4])[:10]
            logger.info("  " + "┣" + "━" * INNER_WIDTH + "┫")
            
            spread_title = "📈 SPREAD:"
            logger.info(f"  ┃ {spread_title:<{INNER_WIDTH}} ┃")
            
            spread_line = f"   Home: {home_spread:<10} │ Line: {handicap:<10} │ Away: {away_spread:<26}"
            logger.info(f"  ┃ {spread_line:<{INNER_WIDTH}} ┃")
    
    if over_under and len(over_under) > 0:
        latest_ou = over_under[-1]
        if len(latest_ou) >= 5:
            over_odds = str(latest_ou[2])[:10]
            total_line = str(latest_ou[3])[:10]
            under_odds = str(latest_ou[4])[:10]
            logger.info("  " + "┣" + "━" * INNER_WIDTH + "┫")
            
            ou_title = "📊 OVER/UNDER:"
            logger.info(f"  ┃ {ou_title:<{INNER_WIDTH}} ┃")
            
            ou_line = f"   Over: {over_odds:<10} │ Total: {total_line:<10} │ Under: {under_odds:<25}"
            logger.info(f"  ┃ {ou_line:<{INNER_WIDTH}} ┃")
    
    # Environment - ensure consistent formatting
    logger.info("  " + "┣" + "━" * INNER_WIDTH + "┫")
    
    env_title = "🌤️  ENVIRONMENT:"
    logger.info(f"  ┃ {env_title:<{INNER_WIDTH}} ┃")
    
    # Format environment data with proper padding
    weather_str = str(weather)[:15] if weather else "Unknown"
    temp_str = str(temp_f)[:10] if temp_f and temp_f != 'N/A' else "N/A"
    wind_str = str(wind_mph)[:10] if wind_mph and wind_mph != 'N/A' else "N/A"
    
    env_line = f"   Weather: {weather_str:<15} │ Temp: {temp_str:<10} │ Wind: {wind_str:<18}"
    logger.info(f"  ┃ {env_line:<{INNER_WIDTH}} ┃")
    
    logger.info("  " + "┗" + "━" * INNER_WIDTH + "┛")

def write_footer(logger, total_matches, status_counts):
    """Write beautiful footer"""
    logger.info("")
    logger.info("")
    logger.info("╔" + "═" * 78 + "╗")
    logger.info("║" + " " * 25 + "📊 SUMMARY STATISTICS" + " " * 32 + "║")
    logger.info("╠" + "═" * 78 + "╣")
    logger.info(f"║ Total Active Matches: {total_matches:<54} ║")
    logger.info("╟" + "─" * 78 + "╢")
    logger.info("║ Status Breakdown:" + " " * 60 + "║")
    for status_id, count in sorted(status_counts.items()):
        status_name = STATUS_MAP.get(status_id, f"Unknown ({status_id})")
        logger.info(f"║   • {status_name:<20}: {count:<49} ║")
    logger.info("╠" + "═" * 78 + "╣")
    logger.info(f"║ 🕐 Completed: {get_eastern_time():<47} ║")
    logger.info("╚" + "═" * 78 + "╝")

# ---------------------------------------------------------------------------
# Main Processing
# ---------------------------------------------------------------------------
def main():
    """Main processing function"""
    print(f"Starting Step 7 - Pretty Display at {get_eastern_time()}")
    
    # Setup logger
    logger = setup_logger()
    
    # Load step2.json
    if not STEP2_FILE.exists():
        print(f"Error: {STEP2_FILE} not found!")
        return
    
    with open(STEP2_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Get summaries
    summaries = data.get('summaries', [])
    
    # Filter by status
    filtered_matches = [m for m in summaries if m.get('status_id', 0) in STATUS_FILTER]
    
    # Group by competition
    competitions = {}
    status_counts = {}
    
    for match in filtered_matches:
        comp = match.get('competition', 'Unknown')
        if comp not in competitions:
            competitions[comp] = []
        competitions[comp].append(match)
        
        # Count statuses
        status_id = match.get('status_id', 0)
        status_counts[status_id] = status_counts.get(status_id, 0) + 1
    
    # Sort matches within each competition by status_id (2-7)
    for comp in competitions:
        competitions[comp].sort(key=lambda x: x.get('status_id', 999))
    
    # Get counts
    total_matches = len(filtered_matches)
    fetch_count = get_daily_fetch_count()
    
    # Write header
    write_header(logger, total_matches, fetch_count)
    
    # Sort competitions alphabetically by name
    sorted_competitions = sorted(competitions.items(), key=lambda x: x[0])
    
    # Write matches grouped by competition
    if total_matches > 0:
        for competition, matches in sorted_competitions:
            country = matches[0].get('country', 'Unknown')
            write_competition_header(logger, competition, country, len(matches))
            
            # Write each match with numbering
            for idx, match in enumerate(matches, 1):
                write_match(logger, match, match_num=idx, total_matches=len(matches))
    
    # Write footer
    write_footer(logger, total_matches, status_counts)
    
    print(f"✅ Step 7 completed! Output written to: {LOG_FILE}")
    print(f"   Total matches displayed: {total_matches}")
    print(f"   View the beautiful output: cat {LOG_FILE}")

if __name__ == "__main__":
    main()