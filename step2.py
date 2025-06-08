#!/usr/bin/env python3
"""
STEP 2 - DATA PROCESSOR (MERGER AND FILTER)
====================================

This script will extract specific fields from step1.json and merge them by match ID.
To be built incrementally in Jupyter.

NOTE ON ODDS DATA STRUCTURE:
---------------------------
The odds data from the API is structured as an ARRAY OF ARRAYS (nested array/2D array).
Each element in the main array is itself an array containing:
  [timestamp, string_value, numeric_odds1, numeric_odds2, numeric_odds3, integer1, integer2, score_string]
Example:
  [1749393410, "8", 8.5, 5.9, 1.23, 2, 0, "0-1"]

This structure contains odds for asia, eu, and bs (bookmakers).

ODDS FILTERING LOGIC:
--------------------
Step 2 filters the odds data to only keep entries from the early minutes of each match:
- The odds arrays are found in: match["odds"][company_id][odds_type]
  where company_id is the betting company (e.g., "2", "4", "5", etc.)
  and odds_type is one of: "asia" (spread), "bs" (over/under), "eu" (moneyline), or "cr"
- Each odds array contains 8 elements: [timestamp, minute, odds1, odds2, odds3, int1, int2, score]
- Only keeps odds from minutes 2, 3, 4, 5, and 6 (filters out minute 1 and anything after minute 6)
- The minute value is found in the second position of each odds array (index 1)
- If there are multiple odds updates within the same minute, only the most recent one is kept
  (determined by the highest timestamp in the first position)
- This filtering is applied to all odds types: asia (spread), bs (over/under), eu (moneyline), and cr
- The result is a cleaner dataset with just 5 odds entries per type per company, focusing on 
  the critical early match period when odds are most volatile and informative

MERGING LOGIC:
--------------
ID-Based Connections:
1. BY MATCH ID:
   - Live endpoint → gives you match.id
   - Details endpoint → query with match.id → returns detailed match info (environment, venue, etc.)
   - Odds endpoint → query with match.id → returns betting odds

2. BY TEAM ID:
   - Live/Details endpoints → give you home_team_id and away_team_id
   - Team endpoint → query with team_id → returns team names, logos, market values

3. BY COMPETITION ID:
   - Live/Details endpoints → give you competition_id
   - Competition endpoint → query with competition_id → returns competition name, type, logo

4. BY COUNTRY ID:
   - Team endpoint → gives you country_id (which country the team is from)
   - Competition endpoint → gives you country_id (which country hosts the competition)
   - Country endpoint → returns all countries (you filter by country_id)

The Complete Flow:
1. Get live matches (each has match_id, home_team_id, away_team_id, competition_id)
2. Use match_id → fetch details & odds
3. Collect all unique team_ids → fetch team info
4. Collect all unique competition_ids → fetch competition info  
5. Fetch country list once (for reference)

This mapping allows Step 2 to merge everything together - taking a match and enriching it with 
team names, competition details, country info, weather data, and betting odds all connected by their respective IDs.

FIELDS TO EXTRACT FROM STEP 1:
------------------------------
ENDPOINT 1: /match/detail_live (live)
- id (match id)

ENDPOINT 2: /match/recent/list (details)
- id (match id)
- season_id
- competition_id
- home_team_id
- away_team_id
- status_id
- home_scores[]
- away_scores[]
- home_position
- away_position
- environment{} (weather data - OPTIONAL:
  - weather_id
  - pressure
  - temperature
  - wind_speed
  - humidity
  - weather)

ENDPOINT 3: /odds/history (odds)
Results keyed by Company ID (2, 4, 5, 9, 10, 13, 15, 16, 17, 22):
- asia[] (8 elements per array)
- bs[] (8 elements per array)
- eu[] (8 elements per array)
- cr[] (8 elements per array)
Each array contains: [timestamp, match_time, odds_values..., status, sealed, score]

ENDPOINT 4: /team/additional/list (team)
- id (team id)
- competition_id
- country_id
- name
- uid (merged team id)

ENDPOINT 5: /competition/additional/list (competition)
- id (competition id)
- category_id
- country_id
- name

ENDPOINT 6: /country/list (country)
- id (country id)
- category_id
- name
"""

import json
import logging
from datetime import datetime
import pytz
import time
from pathlib import Path

# Constants
STEP1_JSON = "/root/6-4-2025/step1.json"
STEP2_JSON = "/root/6-4-2025/step2.json"
TZ = pytz.timezone("America/New_York")

# Betting Company ID to Name mapping
BETTING_COMPANIES = {
    "2": "BET365",
    "3": "Crown",
    "4": "10BET",
    "5": "Ladbrokes",
    "6": "Mansion88",
    "7": "Macauslot",
    "8": "SNAI",
    "9": "William Hill",
    "10": "Easybets",
    "11": "Vcbet",
    "12": "EuroBet",
    "13": "Interwetten",
    "14": "12bet",
    "15": "Sbobet",
    "16": "Wewbet",
    "17": "18Bet",
    "18": "Fun88",
    "21": "188bet",
    "22": "Pinnacle"
}

# Preferred order for betting company selection (BET365 first)
PREFERRED_COMPANIES = ["2", "3", "4", "5", "6", "9", "10", "11", "13", "14", "15", "16", "17", "21", "22"]

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_summary_fields(match: dict) -> dict:
    """Extract key fields from a merged match for summary."""
    return {
        "match_id": match.get("id", ""),
        "home": match.get("home", {}).get("name", "Unknown"),
        "away": match.get("away", {}).get("name", "Unknown"),
        "home_id": match.get("home", {}).get("id", ""),
        "away_id": match.get("away", {}).get("id", ""),
        "score": f"{match.get('home_scores', [0])[-1] if match.get('home_scores') else 0}-{match.get('away_scores', [0])[-1] if match.get('away_scores') else 0}",
        "status_id": match.get("status_id", 0),
        "competition": match.get("league", {}).get("name", "Unknown"),
        "competition_id": match.get("league", {}).get("id", ""),
        "country": match.get("league", {}).get("country_name", "Unknown"),
        "match_time": match.get("match_time", ""),
        "kickoff": match.get("kickoff", ""),
        "venue": match.get("venue", {}).get("name", "") if match.get("venue") else "",
        "home_position": match.get("home_position", ""),
        "away_position": match.get("away_position", ""),
    }

def extract_odds(match: dict) -> dict:
    """Extract betting odds from match data."""
    odds_data = {}
    if "odds" in match and isinstance(match["odds"], dict):
        # Odds are organized by company ID
        for company_id, company_odds in match["odds"].items():
            if isinstance(company_odds, dict):
                odds_data[company_id] = {
                    "asia": company_odds.get("asia", []),
                    "bs": company_odds.get("bs", []),
                    "eu": company_odds.get("eu", []),
                    "cr": company_odds.get("cr", [])
                }
    return odds_data

def extract_environment(match: dict) -> dict:
    """Extract environment/weather data from match."""
    env = match.get("environment", {})
    if isinstance(env, dict):
        return {
            "weather": env.get("weather", ""),
            "temperature": env.get("temperature", ""),
            "humidity": env.get("humidity", ""),
            "wind_speed": env.get("wind_speed", ""),
            "pressure": env.get("pressure", "")
        }
    return {}

def extract_events(match: dict) -> list:
    """Extract match events if available."""
    return match.get("events", [])

def filter_odds_by_minutes(odds_data, min_minute=2, max_minute=6):
    """
    Filter odds arrays to only keep entries where the minute field (second field) 
    is between min_minute and max_minute (inclusive).
    For multiple entries in the same minute, keep only the last one (highest timestamp).
    
    Args:
        odds_data: The odds data structure (dict with asia, bs, eu, cr arrays)
        min_minute: Minimum minute value to keep (as integer)
        max_minute: Maximum minute value to keep (as integer)
    
    Returns:
        Filtered odds data
    """
    filtered_odds = {}
    
    for odds_type in ['asia', 'bs', 'eu', 'cr']:
        if odds_type in odds_data:
            # First, collect all valid entries grouped by minute
            minute_entries = {}
            
            for array in odds_data[odds_type]:
                # Check if the array has at least 2 elements and the second element is the minute field
                if len(array) >= 2:
                    minute_field = array[1]  # Get the minute field
                    
                    # Convert to integer for numeric comparison
                    try:
                        minute_num = int(minute_field) if minute_field != "" else -1
                        
                        # Only keep if minute field is between min and max (inclusive)
                        if min_minute <= minute_num <= max_minute:
                            # Group by minute, keeping track of timestamp
                            if minute_num not in minute_entries:
                                minute_entries[minute_num] = []
                            minute_entries[minute_num].append(array)
                    except (ValueError, TypeError):
                        # Skip entries that can't be converted to int
                        pass
            
            # Now keep only the last entry (highest timestamp) for each minute
            filtered_arrays = []
            for minute in sorted(minute_entries.keys()):
                # Sort by timestamp (first element) and take the last one
                entries_for_minute = sorted(minute_entries[minute], key=lambda x: x[0])
                filtered_arrays.append(entries_for_minute[-1])  # Take the last (highest timestamp)
            
            filtered_odds[odds_type] = filtered_arrays
    
    return filtered_odds

def merge_and_summarize(live_matches: list, match_details: dict, match_odds: dict, 
                        team_info: dict, competition_info: dict, countries: dict) -> list:
    """Merge live match data with enriched data from other endpoints."""
    summaries = []
    
    for match in live_matches:
        match_id = str(match.get("id", ""))
        if not match_id:
            continue
            
        # Get details for this match
        details_wrapper = match_details.get(match_id, {})
        details = None
        if isinstance(details_wrapper, dict) and "results" in details_wrapper:
            results = details_wrapper.get("results", [])
            if results and isinstance(results, list) and len(results) > 0:
                details = results[0]
        
        # Initialize match structure if needed
        if not match.get("home"):
            match["home"] = {}
        if not match.get("away"):
            match["away"] = {}
        if not match.get("league"):
            match["league"] = {}
        
        # Merge details into match (including team IDs)
        if details:
            # Set team IDs
            home_team_id = details.get("home_team_id", "")
            away_team_id = details.get("away_team_id", "")
            competition_id = details.get("competition_id", "")
            
            if home_team_id:
                match["home"]["id"] = home_team_id
            if away_team_id:
                match["away"]["id"] = away_team_id
            if competition_id:
                match["league"]["id"] = competition_id
            
            # Add status_id if not present
            if "status_id" not in match and "status_id" in details:
                match["status_id"] = details["status_id"]
                
            # Merge other fields from details
            for key, value in details.items():
                if key not in ["home_team_id", "away_team_id", "competition_id"] and key not in match:
                    match[key] = value
        
        # Get odds data
        odds_wrapper = match_odds.get(match_id, {})
        if isinstance(odds_wrapper, dict) and "results" in odds_wrapper:
            odds_results = odds_wrapper.get("results", {})
            # Check if results is a dictionary (actual format) not a list
            if isinstance(odds_results, dict) and odds_results:
                match["odds"] = odds_results
            else:
                match["odds"] = {}
        
        # Get team names using team IDs
        home_team_id = str(match.get("home", {}).get("id", "") or details.get("home_team_id", ""))
        away_team_id = str(match.get("away", {}).get("id", "") or details.get("away_team_id", ""))
        
        # Lookup home team
        if home_team_id and home_team_id in team_info:
            team_wrapper = team_info[home_team_id]
            if isinstance(team_wrapper, dict) and "results" in team_wrapper:
                team_results = team_wrapper.get("results", [])
                if team_results and isinstance(team_results, list) and len(team_results) > 0:
                    team_data = team_results[0]
                    match["home"]["name"] = team_data.get("name", "Unknown")
                    match["home"]["short_name"] = team_data.get("short_name", "")
                    match["home"]["logo"] = team_data.get("logo", "")
        
        # Lookup away team
        if away_team_id and away_team_id in team_info:
            team_wrapper = team_info[away_team_id]
            if isinstance(team_wrapper, dict) and "results" in team_wrapper:
                team_results = team_wrapper.get("results", [])
                if team_results and isinstance(team_results, list) and len(team_results) > 0:
                    team_data = team_results[0]
                    match["away"]["name"] = team_data.get("name", "Unknown")
                    match["away"]["short_name"] = team_data.get("short_name", "")
                    match["away"]["logo"] = team_data.get("logo", "")
        
        # Get competition info
        comp_id = str(match.get("league", {}).get("id", "") or details.get("competition_id", ""))
        country_name = "Unknown"
        if comp_id and comp_id in competition_info:
            comp_wrapper = competition_info[comp_id]
            if isinstance(comp_wrapper, dict) and "results" in comp_wrapper:
                comp_results = comp_wrapper.get("results", [])
                if comp_results and isinstance(comp_results, list) and len(comp_results) > 0:
                    comp_data = comp_results[0]
                    match["league"]["name"] = comp_data.get("name", "Unknown")
                    match["league"]["short_name"] = comp_data.get("short_name", "")
                    match["league"]["logo"] = comp_data.get("logo", "")
                    
                    # Get country ID from competition and look up country name
                    country_id = comp_data.get("country_id", "")
                    if country_id and countries:
                        # Check if countries has the country data
                        if country_id in countries:
                            country_data = countries[country_id]
                            if isinstance(country_data, dict):
                                # Direct country object format
                                country_name = country_data.get("name", "Unknown")
                    
                    match["league"]["country_name"] = country_name
                    match["league"]["country_code"] = ""
        
        # Extract summary fields
        summary = extract_summary_fields(match)
        
        # Extract and filter odds - select only one betting company
        raw_odds = extract_odds(match)
        selected_company_id = None
        selected_odds = {}
        
        # Try to find BET365 first, then fall back to preferred order
        for company_id in PREFERRED_COMPANIES:
            if company_id in raw_odds and raw_odds[company_id]:
                # Check if this company has any odds data
                has_data = False
                for odds_type in ['asia', 'bs', 'eu']:
                    if raw_odds[company_id].get(odds_type):
                        has_data = True
                        break
                
                if has_data:
                    selected_company_id = company_id
                    selected_odds = filter_odds_by_minutes(raw_odds[company_id])
                    break
        
        # Set the selected odds and company info
        if selected_company_id:
            summary["odds"] = selected_odds
            summary["odds_company_id"] = selected_company_id
            summary["odds_company_name"] = BETTING_COMPANIES.get(selected_company_id, f"Company {selected_company_id}")
        else:
            summary["odds"] = {}
            summary["odds_company_id"] = None
            summary["odds_company_name"] = None
        
        summary["environment"] = extract_environment(match)
        summary["events"] = extract_events(match)
        
        summaries.append(summary)
    
    return summaries

def save_match_summaries(data: dict, output_file: str) -> bool:
    """Save the processed match summaries to JSON file."""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Failed to save to {output_file}: {e}")
        return False

def main():
    """Main entry point"""
    logger.info("Step 2 processing started...")
    
    # Track processing time
    start_time = time.time()
    
    try:
        # Load step1.json
        logger.info(f"Loading {STEP1_JSON}...")
        with open(STEP1_JSON, 'r', encoding='utf-8') as f:
            step1_data = json.load(f)
        
        # Extract live matches and payload data
        live_matches = step1_data.get("live_matches", {})
        payload_data = {k: v for k, v in step1_data.items() if k != "live_matches"}
        
        # Build country lookup dictionary
        countries_data = payload_data.get("countries", {})
        country_lookup = {}
        for key, value in countries_data.items():
            if isinstance(value, list):
                for country in value:
                    if isinstance(country, dict) and "id" in country:
                        country_lookup[country["id"]] = country
        
        logger.info(f"Found {len(live_matches.get('results', []))} live matches")
        logger.info(f"Found {len(payload_data.get('team_info', {}))} teams")
        logger.info(f"Found {len(payload_data.get('competition_info', {}))} competitions")
        logger.info(f"Found {len(country_lookup)} countries")
        
        # Merge and summarize
        logger.info("Merging and summarizing match data...")
        merged_data = {
            "summaries": merge_and_summarize(live_matches.get("results", []), 
                                              payload_data.get("match_details", {}), 
                                              payload_data.get("match_odds", {}), 
                                              payload_data.get("team_info", {}), 
                                              payload_data.get("competition_info", {}), 
                                              country_lookup),
            "metadata": {
                "total_matches": len(live_matches.get("results", [])),
                "timestamp": datetime.now(TZ).isoformat(),
                "source": "step2.py"
            }
        }
        
        # Add processing time
        processing_time = time.time() - start_time
        merged_data["metadata"]["processing_time"] = f"{processing_time:.2f} seconds"
        
        # Add step2 processing summary
        merged_data["step2_processing_summary"] = {
            "processed_at": datetime.now(TZ).strftime("%m/%d/%Y %I:%M:%S %p %Z"),
            "input_file": STEP1_JSON,
            "output_file": STEP2_JSON,
            "total_matches_processed": len(merged_data["summaries"]),
            "processing_time": f"{processing_time:.2f} seconds",
            "pipeline_timing": {
                "step2_start": datetime.now(TZ).isoformat(),
                "step2_duration": f"{processing_time:.2f} seconds"
            }
        }
        
        # Save to step2.json
        logger.info(f"Saving {len(merged_data['summaries'])} match summaries to {STEP2_JSON}...")
        success = save_match_summaries(merged_data, STEP2_JSON)
        
        if success:
            logger.info(f"Step 2 completed successfully in {processing_time:.2f} seconds")
            logger.info(f"Created {len(merged_data['summaries'])} match summaries")
        else:
            logger.error("Step 2 failed to save output")
            
    except FileNotFoundError:
        logger.error(f"Could not find {STEP1_JSON}. Please run step1.py first.")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {STEP1_JSON}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in Step 2: {e}")
        raise

if __name__ == "__main__":
    main()
