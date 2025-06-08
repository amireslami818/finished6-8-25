"""
STEP2.PY FIELD PATHS REFERENCE
This file documents all the dictionary paths and field mappings used in step2.py
for quick reference and validation.
"""

# =============================================================================
# INPUT DATA PATHS (from step1.json)
# =============================================================================

# Live matches array
LIVE_MATCHES = "step1_data['live_matches']['results']"
# Each match in live_matches has:
MATCH_ID = "match['id']"
MATCH_STATUS = "match['status_id']"
MATCH_SCORE = "match['score']"

# Match details (enriched data)
MATCH_DETAILS = "step1_data['match_details'][match_id]['results']"
# Details include:
MATCH_HOME = "match['home']"  # {'id': team_id, 'name': name, 'position': pos}
MATCH_AWAY = "match['away']"  # {'id': team_id, 'name': name, 'position': pos}
MATCH_LEAGUE = "match['league']"  # {'id': comp_id, 'name': name, 'country_name': country}
MATCH_VENUE = "match['venue']"
MATCH_ENVIRONMENT = "match['environment']"  # weather data
MATCH_EVENTS = "match['events']"  # match events

# Match odds by company
MATCH_ODDS = "step1_data['match_odds'][match_id]['results']"
# Each company's odds:
COMPANY_ODDS = "match_odds[company_id]"  # Keys: 'eu', 'asia', 'bs', 'cr'

# Team information
TEAM_INFO = "step1_data['team_info'][team_id]['results'][0]"
# Team fields:
TEAM_NAME = "team['name']"
TEAM_LOGO = "team['logo']"
TEAM_COUNTRY_ID = "team['country_id']"

# Competition information
COMP_INFO = "step1_data['competition_info'][comp_id]['results'][0]"
# Competition fields:
COMP_NAME = "comp['name']"
COMP_COUNTRY_ID = "comp['country_id']"
COMP_LOGO = "comp['logo']"

# Countries (list format in step1)
COUNTRIES = "step1_data['countries']['results']"  # List of country objects

# =============================================================================
# ODDS FIELD MAPPINGS (API → Our Names)
# =============================================================================

ODDS_FIELD_MAPPING = {
    "eu": "money_line",      # European/Money Line odds [home_win, draw, away_win]
    "asia": "spread",        # Asian Handicap/Spread [home_odds, handicap, away_odds]
    "bs": "over_under",      # Ball Size/Over-Under [over_odds, total, under_odds]
    "cr": "corners"          # Corner totals [over_odds, total, under_odds]
}

# Each odds array contains 8 elements:
# [timestamp, minute, val1, val2, val3, status, sealed, score]

# =============================================================================
# OUTPUT STRUCTURE (step2.json)
# =============================================================================

OUTPUT_SUMMARY_FIELDS = [
    # NEW PRIORITIZED ODDS FIELDS (come first)
    "money_line",         # Renamed from 'eu'
    "spread",            # Renamed from 'asia'
    "over_under",        # Renamed from 'bs'
    "corners",           # Renamed from 'cr'
    "odds_company_id",   # Selected betting company ID
    "odds_company_name", # Human-readable company name
    
    # ORIGINAL NESTED ODDS
    "odds",              # {company_id: {money_line:[], spread:[], ...}}
    
    # MATCH IDENTIFICATION
    "match_id",
    "status_id",
    "status",            # Same as status_id
    
    # TEAM INFORMATION
    "home",              # Team name
    "away",              # Team name
    "home_id",          # Team ID
    "away_id",          # Team ID
    "home_position",    # League position
    "away_position",    # League position
    
    # MATCH DETAILS
    "score",            # "home-away" format
    "match_time",       # Unix timestamp
    "kickoff",          # Time string
    "venue",            # Venue name
    
    # COMPETITION/COUNTRY
    "competition",      # League/competition name
    "competition_id",   # Competition ID
    "country",          # Country name
    
    # ADDITIONAL DATA
    "environment",      # {weather, temperature, humidity, wind_speed, pressure}
    "events"           # List of match events
]

# =============================================================================
# KEY FUNCTIONS AND THEIR PATHS
# =============================================================================

def extract_summary_fields_paths():
    """Shows how extract_summary_fields accesses data"""
    return {
        "match_id": "match.get('id')",
        "home": "match.get('home', {}).get('name', 'Unknown')",
        "away": "match.get('away', {}).get('name', 'Unknown')",
        "home_id": "match.get('home', {}).get('id', '')",
        "away_id": "match.get('away', {}).get('id', '')",
        "score": "f\"{home_scores}-{away_scores}\"",
        "status_id": "match.get('status_id', 0)",
        "competition": "match.get('league', {}).get('name', 'Unknown')",
        "competition_id": "match.get('league', {}).get('id', '')",
        "country": "match.get('league', {}).get('country_name', 'Unknown')",
        "match_time": "match.get('match_time', 0)",
        "kickoff": "match.get('kickoff', '')",
        "venue": "match.get('venue', '')",
        "home_position": "match.get('home', {}).get('position', '')",
        "away_position": "match.get('away', {}).get('position', '')"
    }

def extract_odds_paths():
    """Shows how extract_odds maps API fields to our names"""
    return {
        "input": "match['odds'][company_id]",
        "output": {
            "money_line": "company_odds.get('eu', [])",
            "spread": "company_odds.get('asia', [])",
            "over_under": "company_odds.get('bs', [])",
            "corners": "company_odds.get('cr', [])"
        }
    }

# =============================================================================
# PREFERRED BETTING COMPANIES
# =============================================================================

PREFERRED_COMPANIES = ["2", "3", "4", "5", "6", "9", "10", "11", "13", "14", "15", "16", "17", "21", "22"]

BETTING_COMPANIES = {
    "2": "BET365",
    "3": "Crown",
    "4": "Ladbrokes", 
    "5": "William Hill",
    "6": "Interwetten",
    "9": "Betfair",
    "10": "10BET",
    "11": "188BET",
    "13": "SBOBET",
    "14": "Easybets",
    "15": "Pinnacle",
    "16": "SNAI",
    "17": "Vcbet",
    "21": "Betclic",
    "22": "Coral"
}

# =============================================================================
# VALIDATION TESTS
# =============================================================================

def validate_odds_renaming():
    """Quick test to ensure odds are properly renamed"""
    test_odds = {
        "2": {
            "eu": [[1234567890, "2", 1.5, 3.5, 5.0, "", "", "0:0"]],
            "asia": [[1234567890, "3", 1.8, -0.5, 2.1, "", "", "0:0"]],
            "bs": [[1234567890, "4", 1.9, 2.5, 1.9, "", "", "0:0"]],
            "cr": [[1234567890, "5", 1.85, 9.5, 1.95, "", "", "0:0"]]
        }
    }
    
    # This should map to:
    expected = {
        "2": {
            "money_line": [[1234567890, "2", 1.5, 3.5, 5.0, "", "", "0:0"]],
            "spread": [[1234567890, "3", 1.8, -0.5, 2.1, "", "", "0:0"]],
            "over_under": [[1234567890, "4", 1.9, 2.5, 1.9, "", "", "0:0"]],
            "corners": [[1234567890, "5", 1.85, 9.5, 1.95, "", "", "0:0"]]
        }
    }
    
    return test_odds, expected

# Usage in merge_and_summarize():
# 1. Extract odds: raw_odds = extract_odds(enriched_match)
# 2. Select company: Iterate PREFERRED_COMPANIES, check if has data
# 3. Filter by minutes: selected_odds = filter_odds_by_minutes(raw_odds[company_id])
# 4. Add to summary: summary["money_line"] = selected_odds.get("money_line", [])
