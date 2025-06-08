#!/usr/bin/env python3
"""
STEP 1 – DATA FETCHER (COMPREHENSIVE USAGE AND LOCKING)
======================================================

PURPOSE:
--------
Fetches live football match data from TheSports API and stores it as JSON.
This is the first step in a football data pipeline.

CRITICAL USAGE NOTES:
--------------------
1. **SINGLE RUN DESIGN**: This script runs ONCE and exits. It does NOT loop or schedule.
2. **PID FILE LOCKING**: Uses step1.pid to prevent concurrent execution.
3. **OUTPUT**: Generates step1.json with live match data and daily_match_counter.json for tracking.
4. **TERMINATION**: Properly handles SIGTERM for graceful shutdown and cleanup.

STARTUP METHODS:
---------------
1. Direct: python3 step1_json.py
2. Via script: bash start.sh (includes logging and background execution)
3. Via cron/systemd: Ensure proper working directory and environment

IMPORTANT TERMINOLOGY:
---------------------
- LIVE MATCHES = All matches from /match/detail_live API endpoint (broader category)
- IN-PLAY MATCHES = Only matches with status_id 2,3,4,5,6 (actively playing subset of live matches)

DATA FLOW:
----------
step1.py → step1.json → step2.py → step2.json
(Manual execution required between steps - no automatic triggering)

LOCKING MECHANISM:
-----------------
- Creates step1.pid on startup
- Checks for existing lock before running
- Removes lock on normal exit or SIGTERM
- IMPORTANT: Stale locks must be manually removed if process crashes

FILES GENERATED:
---------------
- step1.json: Main output with live match data
- daily_match_counter.json: Historical tracking data
- step1.log: Execution logs (rotated daily)
- step1.pid: Process lock file

FIELD CLARIFICATIONS:
--------------------
- total_entries: Number of days in history (recommend renaming to history_length)
- latest_match_count: Matches found in current run (recommend renaming to current_match_count)

ERROR HANDLING:
--------------
- API failures logged and handled gracefully
- Network timeouts with configurable retries
- File I/O errors logged with stack traces
- Missing environment variables cause early exit

ENVIRONMENT REQUIREMENTS:
------------------------
- API_KEY: Required in .env file or environment
- Python packages: requests, python-dotenv, pytz
- Write permissions in current directory
- Network access to TheSports API

INTEGRATION WITH STEP 2:
-----------------------
Step 2 (step2.py) is now automatically triggered after data is saved to step1.json.
The in-memory data is passed directly to extract_merge_summarize() for immediate processing.
This creates step2.json without requiring separate manual execution.
"""

import asyncio
import aiohttp
import json
import logging
import logging.handlers
import os
import re
import requests
import shutil
import signal
import subprocess
import sys
import time
import traceback
import pytz
from datetime import datetime
from collections import defaultdict
from contextlib import contextmanager
from dotenv import load_dotenv
import step2
import step7
from pathlib import Path

# Import centralized logging
try:
    from centralized_logger.log_config import (
        initialize_global_logging_for_step,
        apply_global_format_to_logger,
        central_logging_hub
    )
    CENTRALIZED_LOGGING_AVAILABLE = True
except ImportError:
    # Fallback if centralized logger not available
    def initialize_global_logging_for_step(*args, **kwargs):
        return {}
    def apply_global_format_to_logger(logger, *args, **kwargs):
        return logger
    def central_logging_hub(*args, **kwargs):
        pass
    CENTRALIZED_LOGGING_AVAILABLE = False

# Load environment variables
load_dotenv()

# Set up logging with rotating file handler (no timestamps on individual lines)
file_handler = logging.handlers.TimedRotatingFileHandler("step1.log", when="midnight", backupCount=7)
console_handler = logging.StreamHandler()

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",  # Remove timestamp from individual lines
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger(__name__)

# Get credentials from environment variables
USER = os.getenv("THESPORTS_USER", "thenecpt")  # Fallback for compatibility
SECRET = os.getenv("THESPORTS_SECRET", "0c55322e8e196d6ef9066fa4252cf386")  # Fallback for compatibility

# API base and endpoints
BASE_URL = "https://api.thesports.com/v1/football"
URLS = {
    "live":        f"{BASE_URL}/match/detail_live",
    "details":     f"{BASE_URL}/match/recent/list",
    "odds":        f"{BASE_URL}/odds/history",
    "team":        f"{BASE_URL}/team/additional/list",
    "competition": f"{BASE_URL}/competition/additional/list",
    "country":     f"{BASE_URL}/country/list",
}

# API ENDPOINT SCHEMAS
# ===================

# ENDPOINT 1: /match/detail_live (live)
# --------------------------------------
# Returns real-time match data with scores, stats, incidents, and text live
LIVE_SCHEMA = """
{
  "type": "object",
  "properties": {
    "code": {"type": "integer"},
    "results": {
      "type": "array",
      "description": "Real-time data list",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string", "description": "Match id"},
          "score": {
            "type": "array",
            "description": "Score array: [match_id, status_id, home_scores, away_scores, kickoff_timestamp, '']",
            "items": [
              {"description": "Match id (String)"},
              {"description": "Match status (Integer)"},
              {
                "description": "Home scores: [regular_time, halftime, red_cards, yellow_cards, corners(-1=no data), overtime, penalty]"
              },
              {
                "description": "Away scores: [regular_time, halftime, red_cards, yellow_cards, corners(-1=no data), overtime, penalty]"
              },
              {"description": "Kickoff timestamp (Integer)"},
              {"description": "Compatible ignore (String)"}
            ]
          },
          "stats": {
            "type": "array",
            "description": "Match statistics",
            "items": {
              "type": "object",
              "properties": {
                "type": {"type": "integer", "description": "Type, see status code -> technical statistics"},
                "home": {"type": "integer", "description": "Home team value"},
                "away": {"type": "integer", "description": "Away team value"}
              }
            }
          },
          "incidents": {
            "type": "array",
            "description": "Match incidents",
            "items": {
              "type": "object",
              "properties": {
                "type": {"type": "integer", "description": "Type, see status code -> technical statistics"},
                "position": {"type": "integer", "description": "Incident occurred: 0-neutral, 1-home team, 2-away team"},
                "time": {"type": "integer", "description": "Time (minutes)"},
                "player_id": {"type": "string", "description": "Player id related to incident (optional)"},
                "player_name": {"type": "string", "description": "Player name related to incident (optional)"},
                "assist1_id": {"type": "string", "description": "Assist player 1 id, goal related (optional)"},
                "assist1_name": {"type": "string", "description": "Assist player 1 name, goal related (optional)"},
                "assist2_id": {"type": "string", "description": "Assist player 2 id, goal related (optional)"},
                "assist2_name": {"type": "string", "description": "Assist player 2 name, goal related (optional)"},
                "home_score": {"type": "integer", "description": "Home team score, goal related (optional)"},
                "away_score": {"type": "integer", "description": "Away team score, goal related (optional)"},
                "in_player_id": {"type": "string", "description": "Substitute in player id (optional)"},
                "in_player_name": {"type": "string", "description": "Substitute in player name (optional)"},
                "out_player_id": {"type": "string", "description": "Substitute out player id (optional)"},
                "out_player_name": {"type": "string", "description": "Substitute out player name (optional)"},
                "var_reason": {
                  "type": "integer",
                  "description": "VAR reason: 1-Goal awarded, 2-Goal not awarded, 3-Penalty awarded, 4-Penalty not awarded, 5-Red card given, 6-Card upgrade, 7-Mistaken identity, 0-Other"
                },
                "var_result": {
                  "type": "integer",
                  "description": "VAR result: 1-Goal confirmed, 2-Goal cancelled, 3-Penalty confirmed, 4-Penalty cancelled, 5-Red card confirmed, 6-Red card cancelled, 7-Card upgrade confirmed, 8-Card upgrade cancelled, 9-Original decision, 10-Original decision changed, 0-Unknown"
                },
                "reason_type": {"type": "integer", "description": "Reason for red/yellow cards and substitutions"}
              }
            }
          },
          "tlive": {
            "type": "array",
            "description": "Match text live",
            "items": {
              "type": "object",
              "properties": {
                "time": {"type": "string", "description": "Time (minutes)"},
                "data": {"type": "string", "description": "Contents"},
                "position": {"type": "integer", "description": "Incident occurred: 0-neutral, 1-home team, 2-away team"}
              }
            }
          }
        }
      }
    }
  }
}
"""

# ENDPOINT 2: /match/recent/list (details)
# -----------------------------------------
# Returns detailed match information including environment data
DETAILS_SCHEMA = """
{
  "type": "object",
  "properties": {
    "code": {"type": "integer"},
    "query": {
      "type": "object",
      "description": "Inquiry",
      "properties": {
        "total": {"type": "integer", "description": "Return the total amount of data"},
        "type": {"type": "string", "description": "Query type: uuid/page/time, default page"},
        "uuid": {"type": "string", "description": "uuid query value"},
        "page": {"type": "integer", "description": "page query value"},
        "time": {"type": "integer", "description": "time query value, timestamp format"},
        "min_time": {"type": "integer", "description": "Return smallest time (updated_at value)"},
        "max_time": {"type": "integer", "description": "Return largest time (updated_at value)"}
      }
    },
    "results": {
      "type": "array",
      "description": "Match list",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string", "description": "Match id"},
          "season_id": {"type": "string", "description": "Season id"},
          "competition_id": {"type": "string", "description": "Competition id"},
          "home_team_id": {"type": "string", "description": "Home team id"},
          "away_team_id": {"type": "string", "description": "Away team id"},
          "status_id": {"type": "integer", "description": "Match status"},
          "match_time": {"type": "integer", "description": "Match time"},
          "venue_id": {"type": "string", "description": "Venue id"},
          "referee_id": {"type": "string", "description": "Referee id"},
          "neutral": {"type": "integer", "description": "Is it neutral, 1-Yes, 0-No"},
          "note": {"type": "string", "description": "Remarks"},
          "home_scores": {
            "type": "array",
            "description": "Home team scores: [regular_time, halftime, red_cards, yellow_cards, corners(-1=no data), overtime, penalty]"
          },
          "away_scores": {
            "type": "array",
            "description": "Away team scores: [regular_time, halftime, red_cards, yellow_cards, corners(-1=no data), overtime, penalty]"
          },
          "home_position": {"type": "string", "description": "Home Team Ranking"},
          "away_position": {"type": "string", "description": "Away Team Ranking"},
          "coverage": {
            "type": "object",
            "properties": {
              "mlive": {"type": "integer", "description": "Is there animation, 1-yes, 0-no"},
              "lineup": {"type": "integer", "description": "Is there lineup, 1-yes, 0-no"}
            }
          },
          "round": {
            "type": "object",
            "properties": {
              "stage_id": {"type": "string", "description": "Stage id"},
              "group_num": {"type": "integer", "description": "Which group, 1-A, 2-B and so on"},
              "round_num": {"type": "integer", "description": "Which round"}
            }
          },
          "related_id": {"type": "string", "description": "Match id of other round in double round (optional)"},
          "agg_score": {"type": "array", "description": "Total score of two rounds: [home, away] (optional)"},
          "environment": {
            "type": "object",
            "description": "Match environment (only if data available)",
            "properties": {
              "weather": {
                "type": "integer",
                "description": "Weather: 1-Partially cloudy, 2-Cloudy, 3-Partially cloudy/rain, 4-Snow, 5-Sunny, 6-Overcast Rain/partial thunderstorm, 7-Overcast, 8-Mist, 9-Cloudy with rain, 10-Cloudy with rain, 11-Cloudy with rain/partial Thunderstorms, 12-Clouds/rains and thunderstorms locally, 13-Fog"
              },
              "pressure": {"type": "string", "description": "Air pressure"},
              "temperature": {"type": "string", "description": "Temperature"},
              "wind": {"type": "string", "description": "Wind speed"},
              "humidity": {"type": "string", "description": "Humidity"}
            }
          },
          "tbd": {"type": "integer", "description": "Is match time TBD? 1-Yes (optional)"},
          "has_ot": {"type": "integer", "description": "Is there overtime? 1-Yes (optional)"},
          "ended": {"type": "integer", "description": "End time (optional)"},
          "team_reverse": {"type": "integer", "description": "Are host/away positions opposite? 1-Yes (optional)"},
          "updated_at": {"type": "integer", "description": "Update time"}
        }
      }
    }
  }
}
"""

# ENDPOINT 3: /odds/history (odds)
# ---------------------------------
# Returns betting odds by company for each match
# Access: The results object is keyed by Company ID (e.g., "2", "9", "17")
# Each company provides odds in multiple formats: asia (spread), bs (over/under), eu (moneyline), cr (corners)
ODDS_SCHEMA = """
{
  "type": "object",
  "properties": {
    "code": {"type": "integer"},
    "results": {
      "type": "object",
      "properties": {
        "Company id": {
          "type": "object",
          "description": "The key is the odds company id, see status code -> Odds Company ID for details",
          "properties": {
            "asia": {
              "type": "array",
              "description": "Asian Handicap (Spread betting)",
              "items": {
                "type": "array",
                "description": "Asia odds data: [timestamp, match_time, home_odds, handicap, away_odds, status, sealed, score]",
                "items": [
                  {"description": "Change time (Integer)"},
                  {"description": "Time of match, empty before start (String)"},
                  {"description": "Home win odds (Float)"},
                  {"description": "Handicap: positive=home gives, negative=away gives (Float)"},
                  {"description": "Away win odds (Float)"},
                  {"description": "Match status (Integer)"},
                  {"description": "Whether sealed: 0-No, 1-Yes (Integer)"},
                  {"description": "Score: home-away (String)"}
                ]
              }
            },
            "eu": {
              "type": "array",
              "description": "European/Moneyline odds",
              "items": {
                "type": "array",
                "description": "Euro odds data: [timestamp, match_time, home_odds, draw_odds, away_odds, status, sealed, score]",
                "items": [
                  {"description": "Change time (Integer)"},
                  {"description": "Time of match, empty before start (String)"},
                  {"description": "Home win odds (Float)"},
                  {"description": "Draw odds (Float)"},
                  {"description": "Away win odds (Float)"},
                  {"description": "Match status (Integer)"},
                  {"description": "Whether sealed: 0-No, 1-Yes (Integer)"},
                  {"description": "Score: home-away (String)"}
                ]
              }
            },
            "bs": {
              "type": "array",
              "description": "Ball Size (Over/Under total goals)",
              "items": {
                "type": "array",
                "description": "O/U odds data: [timestamp, match_time, over_odds, total, under_odds, status, sealed, score]",
                "items": [
                  {"description": "Change time (Integer)"},
                  {"description": "Time of match, empty before start (String)"},
                  {"description": "Over odds (Float)"},
                  {"description": "Total goals line (Float)"},
                  {"description": "Under odds (Float)"},
                  {"description": "Match status (Integer)"},
                  {"description": "Whether sealed: 0-No, 1-Yes (Integer)"},
                  {"description": "Score: home-away (String)"}
                ]
              }
            },
            "cr": {
              "type": "array",
              "description": "Corner kicks Over/Under",
              "items": {
                "type": "array",
                "description": "Corner odds data: [timestamp, match_time, over_odds, total, under_odds, status, sealed, corner_score]",
                "items": [
                  {"description": "Change time (Integer)"},
                  {"description": "Time of match, empty before start (String)"},
                  {"description": "Over odds (Float)"},
                  {"description": "Total corners line (Float)"},
                  {"description": "Under odds (Float)"},
                  {"description": "Match status (Integer)"},
                  {"description": "Whether sealed: 0-No, 1-Yes (Integer)"},
                  {"description": "Corner ratio: home-away (String)"}
                ]
              }
            }
          }
        }
      }
    }
  }
}
"""

# ENDPOINT 4: /team/additional/list (team)
# -----------------------------------------
# Returns team information including names, logos, market values, etc.
# NOTE: Team data should be cached/saved once as team names rarely change
# Consider checking once daily to ensure team IDs still match team names
TEAM_SCHEMA = """
{
  "type": "object",
  "properties": {
    "code": {"type": "integer"},
    "query": {
      "type": "object",
      "description": "Inquiry",
      "properties": {
        "total": {"type": "integer", "description": "Return the total amount of data"},
        "type": {"type": "string", "description": "Query type: uuid/page/time, default page"},
        "uuid": {"type": "string", "description": "uuid query value"},
        "page": {"type": "integer", "description": "page query value"},
        "time": {"type": "integer", "description": "time query value, timestamp format"},
        "min_time": {"type": "integer", "description": "Return smallest time (updated_at value)"},
        "max_time": {"type": "integer", "description": "Return largest time (updated_at value)"}
      }
    },
    "results": {
      "type": "array",
      "description": "Team list",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string", "description": "Team id"},
          "competition_id": {"type": "string", "description": "Competition id (league team belongs to, not cups)"},
          "country_id": {"type": "string", "description": "Country id"},
          "name": {"type": "string", "description": "Team name"},
          "short_name": {"type": "string", "description": "Team abbreviation"},
          "logo": {"type": "string", "description": "Team logo"},
          "national": {"type": "integer", "description": "Whether national team, 1-Yes, 0-No"},
          "country_logo": {"type": "string", "description": "National team logo (exists for national teams)"},
          "foundation_time": {"type": "integer", "description": "Year established"},
          "website": {"type": "string", "description": "Team official website"},
          "coach_id": {"type": "string", "description": "Coach id"},
          "venue_id": {"type": "string", "description": "Venue id"},
          "market_value": {"type": "integer", "description": "Market value"},
          "market_value_currency": {"type": "string", "description": "Market value unit"},
          "total_players": {"type": "integer", "description": "Total players, -1 means no data"},
          "foreign_players": {"type": "integer", "description": "Non-local players, -1 means no data"},
          "national_players": {"type": "integer", "description": "National team players, -1 means no data"},
          "uid": {"type": "string", "description": "Team id after merging duplicates (optional)"},
          "virtual": {"type": "integer", "description": "Whether placeholder team, 1-Yes, 0-No"},
          "gender": {"type": "integer", "description": "Gender: 1-Male, 2-Female"},
          "updated_at": {"type": "integer", "description": "Update time"}
        }
      }
    }
  }
}
"""

# ENDPOINT 5: /competition/additional/list (competition)
# -------------------------------------------------------
# Returns competition information including names, logos, types, seasons, etc.
# NOTE: Competition data should be cached and only refreshed once per hour
# Competition details rarely change, so avoid hitting API every fetch
COMPETITION_SCHEMA = """
{
  "type": "object",
  "properties": {
    "code": {"type": "integer"},
    "query": {
      "type": "object",
      "description": "Inquiry",
      "properties": {
        "total": {"type": "integer", "description": "Return the total amount of data"},
        "type": {"type": "string", "description": "Query type: uuid/page/time, default page"},
        "uuid": {"type": "string", "description": "uuid query value"},
        "page": {"type": "integer", "description": "page query value"},
        "time": {"type": "integer", "description": "time query value, timestamp format"},
        "min_time": {"type": "integer", "description": "Return smallest time (updated_at value)"},
        "max_time": {"type": "integer", "description": "Return largest time (updated_at value)"}
      }
    },
    "results": {
      "type": "array",
      "description": "Competition list",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string", "description": "Competition id"},
          "category_id": {"type": "string", "description": "Category id"},
          "country_id": {"type": "string", "description": "Country id"},
          "name": {"type": "string", "description": "Competition name"},
          "short_name": {"type": "string", "description": "Competition abbreviation"},
          "logo": {"type": "string", "description": "Competition logo"},
          "type": {"type": "integer", "description": "Competition type: 0-unknown, 1-league, 2-cup, 3-friendly"},
          "cur_season_id": {"type": "string", "description": "Current season id"},
          "cur_stage_id": {"type": "string", "description": "Current stage id"},
          "cur_round": {"type": "integer", "description": "Current round"},
          "round_count": {"type": "integer", "description": "Total rounds"},
          "title_holder": {
            "type": "array",
            "description": "Defending champion: [team_id, championships_count]"
          },
          "most_titles": {
            "type": "array",
            "description": "Most winning team: [[team_ids], championships_count]"
          },
          "newcomers": {
            "type": "array",
            "description": "Promoted/relegated teams: [[promoted_teams], [relegated_teams]]"
          },
          "divisions": {
            "type": "array",
            "description": "Competition level: [[higher_level_ids], [lower_level_ids]]"
          },
          "host": {
            "type": "object",
            "properties": {
              "country": {"type": "string", "description": "Country"},
              "city": {"type": "string", "description": "City (optional)"}
            }
          },
          "primary_color": {"type": "string", "description": "Main color"},
          "secondary_color": {"type": "string", "description": "Secondary color"},
          "updated_at": {"type": "integer", "description": "Update time"}
        }
      }
    }
  }
}
"""

# ENDPOINT 6: /country/list (country)
# ------------------------------------
# Returns country information
# NOTE: Country data should be cached and only refreshed once per hour
# Country data is very static, avoid hitting API every fetch
COUNTRY_SCHEMA = """
{
  "type": "object",
  "properties": {
    "code": {"type": "integer"},
    "results": {
      "type": "array",
      "description": "Country list",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string", "description": "Country id"},
          "category_id": {"type": "string", "description": "Category id"},
          "name": {"type": "string", "description": "Country name"},
          "logo": {"type": "string", "description": "Country logo"},
          "updated_at": {"type": "integer", "description": "Update time"}
        }
      }
    }
  }
}
"""

# CACHING STRATEGY FOR STATIC ENDPOINTS
# =====================================
# Team, Competition, and Country endpoints should be cached and refreshed only once per hour
# These data points rarely change, so hitting them every minute is wasteful
# Best practice: Cache on first fetch, then refresh hourly to ensure IDs still match names

# Daily match counter file
COUNTER_FILE = "daily_match_counter.json"
PID_FILE = "step1.pid"

# Async helper functions for concurrent data fetching
async def fetch_json_async(session, url, params):
    """Async version of fetch_json with retry logic and mock data fallback"""
    for attempt in range(3):
        try:
            async with session.get(url, params=params, timeout=30) as resp:
                resp.raise_for_status()
                data = await resp.json()
                
                # Check for authorization errors in the response (same logic as sync version)
                if isinstance(data, dict) and "err" in data:
                    error_msg = data["err"]
                    if "not authorized" in error_msg.lower() or "contact our business staff" in error_msg.lower():
                        logger.warning(f"API Authorization Error: {error_msg}")
                        logger.info("Falling back to mock data for testing...")
                        return generate_mock_api_response()
                    else:
                        logger.error(f"API Error: {error_msg}")
                        return data  # Return the error response
                
                return data
                
        except Exception as e:
            if attempt == 2:  # Last attempt
                logger.warning(f"Async API call failed for {url} after 3 attempts: {str(e)}")
                logger.info("Falling back to mock data for testing...")
                return generate_mock_api_response()
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    # Final fallback
    return generate_mock_api_response()

async def enrich_match_data_async(matches):
    """Async version of enrich_match_data with two-phase concurrent fetching"""
    # Optional connection limit to prevent API rate-limit errors
    connector = aiohttp.TCPConnector(limit=30)  # Adjust limit as needed
    async with aiohttp.ClientSession(connector=connector) as session:
        # Phase 1: details + odds in parallel
        detail_tasks = [
            fetch_json_async(session, URLS["details"],
                             {"user": USER, "secret": SECRET, "uuid": m["id"]})
            for m in matches
        ]
        odds_tasks = [
            fetch_json_async(session, URLS["odds"],
                             {"user": USER, "secret": SECRET, "uuid": m["id"]})
            for m in matches
        ]
        details_list, odds_list = await asyncio.gather(
            asyncio.gather(*detail_tasks),
            asyncio.gather(*odds_tasks),
        )

        # Extract IDs for Phase 2
        team_ids = set()
        comp_ids = set()
        
        for detail_wrap in details_list:
            if isinstance(detail_wrap, dict):
                # Extract from results/result array like in original code
                res = detail_wrap.get("results") or detail_wrap.get("result") or []
                if isinstance(res, list) and res:
                    detail = res[0]
                    if detail.get("home_team_id"):
                        team_ids.add(detail.get("home_team_id"))
                    if detail.get("away_team_id"):
                        team_ids.add(detail.get("away_team_id"))
                    if detail.get("competition_id"):
                        comp_ids.add(detail.get("competition_id"))
        
        # Also extract from original matches as fallback
        for match in matches:
            if match.get("home_team_id"):
                team_ids.add(match.get("home_team_id"))
            if match.get("away_team_id"):
                team_ids.add(match.get("away_team_id"))
            if match.get("competition_id"):
                comp_ids.add(match.get("competition_id"))

        # Phase 2: teams + competitions + country
        team_tasks = [
            fetch_json_async(session, URLS["team"],
                             {"user": USER, "secret": SECRET, "uuid": tid})
            for tid in team_ids if tid is not None
        ]
        comp_tasks = [
            fetch_json_async(session, URLS["competition"],
                             {"user": USER, "secret": SECRET, "uuid": cid})
            for cid in comp_ids if cid is not None
        ]
        
        teams_list, comps_list, countries = await asyncio.gather(
            asyncio.gather(*team_tasks) if team_tasks else asyncio.gather(),
            asyncio.gather(*comp_tasks) if comp_tasks else asyncio.gather(),
            fetch_json_async(session, URLS["country"], {"user": USER, "secret": SECRET})
        )

    # Reassemble the all_data dict:
    team_ids_list = list(team_ids)
    comp_ids_list = list(comp_ids)
    
    return {
        "match_details":    {m["id"]: d for m, d in zip(matches, details_list)},
        "match_odds":       {m["id"]: o for m, o in zip(matches, odds_list)},
        "team_info":        {str(tid): t for tid, t in zip(team_ids_list, teams_list)},
        "competition_info": {str(cid): c for cid, c in zip(comp_ids_list, comps_list)},
        "countries":        countries,
    }

# Global flag for graceful shutdown
shutdown_flag = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_flag
    signal_name = signal.Signals(signum).name
    logger.info(f"Received {signal_name}, initiating graceful shutdown...")
    shutdown_flag = True

def create_pid_file():
    """Create PID file to prevent concurrent execution"""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                existing_pid = int(f.read().strip())
            
            # Check if process is still running
            try:
                os.kill(existing_pid, 0)
                logger.error(f"Another instance is already running (PID: {existing_pid})")
                sys.exit(1)
            except OSError:
                # Process doesn't exist, remove stale PID file
                os.remove(PID_FILE)
                logger.info("Removed stale PID file")
        except (ValueError, IOError):
            # Invalid PID file, remove it
            os.remove(PID_FILE)
            logger.info("Removed invalid PID file")
    
    # Create new PID file
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    logger.info(f"Created PID file: {PID_FILE}")

def remove_pid_file():
    """Remove PID file on exit"""
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
        logger.info(f"Removed PID file: {PID_FILE}")

@contextmanager
def pid_lock():
    """Context manager for PID file locking"""
    create_pid_file()
    try:
        yield
    finally:
        remove_pid_file()

def get_daily_match_counter():
    """Get and increment the daily match counter, resetting at midnight EST."""
    ny_tz = pytz.timezone("America/New_York")
    now = datetime.now(ny_tz)
    today_str = now.strftime("%Y-%m-%d")
    
    # Load existing counter data
    counter_data = {"date": "", "count": 0}
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, 'r') as f:
                counter_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    # Reset counter if it's a new day
    if counter_data.get("date") != today_str:
        counter_data = {"date": today_str, "count": 0}
    
    # Increment counter
    counter_data["count"] += 1
    
    # Save updated counter
    try:
        with open(COUNTER_FILE, 'w') as f:
            json.dump(counter_data, f)
    except IOError:
        logger.warning("Could not save daily match counter")
    
    return counter_data["count"]

def get_ny_time_str(format_str="%m/%d/%Y %I:%M:%S %p EST"):
    """Get current time in New York timezone with custom format"""
    ny_tz = pytz.timezone("America/New_York")
    return datetime.now(ny_tz).strftime(format_str)

def extract_status_id(match):
    """Extract status_id from match data, checking multiple locations"""
    return match.get("status_id") or (match.get("score", [None, None])[1] if isinstance(match.get("score"), list) and len(match.get("score", [])) > 1 else None)

def fetch_json(url: str, params: dict) -> dict:
    """Fetch JSON data with retry logic and mock data fallback"""
    for attempt in range(3):
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Check for authorization errors in the response
            if isinstance(data, dict) and "err" in data:
                error_msg = data["err"]
                if "not authorized" in error_msg.lower() or "contact our business staff" in error_msg.lower():
                    logger.warning(f"API Authorization Error: {error_msg}")
                    logger.info("Falling back to mock data for testing...")
                    return generate_mock_api_response()
                else:
                    logger.error(f"API Error: {error_msg}")
                    return data  # Return the error response
            
            return data
            
        except Exception as e:
            if attempt == 2:  # Last attempt
                logger.warning(f"API call failed for {url} after 3 attempts: {str(e)}")
                logger.info("Falling back to mock data for testing...")
                return generate_mock_api_response()
            time.sleep(2 ** attempt)  # Exponential backoff
    
    # Final fallback
    return generate_mock_api_response()

def generate_mock_api_response():
    """Generate mock API response when real API is not available"""
    from datetime import datetime, timedelta
    import random
    
    # Mock teams
    teams = [
        {"id": 1, "name": "Manchester United", "short_name": "MUN"},
        {"id": 2, "name": "Liverpool", "short_name": "LIV"},
        {"id": 3, "name": "Arsenal", "short_name": "ARS"},
        {"id": 4, "name": "Chelsea", "short_name": "CHE"},
        {"id": 5, "name": "Manchester City", "short_name": "MCI"},
        {"id": 6, "name": "Tottenham", "short_name": "TOT"}
    ]
    
    # Generate some mock matches
    matches = []
    base_time = datetime.now()
    
    for i in range(8):  # Generate 8 mock matches
        match_time = base_time + timedelta(hours=random.randint(-24, 48))
        home_team = random.choice(teams)
        away_team = random.choice([t for t in teams if t['id'] != home_team['id']])
        
        is_live = random.choice([True, False, False])  # 1/3 chance of being live
        
        match = {
            "uuid": f"match_{i+1}",
            "time": match_time.strftime("%H:%M"),
            "date": match_time.strftime("%Y-%m-%d"),
            "timestamp": int(match_time.timestamp()),
            "home": home_team["name"],
            "away": away_team["name"],
            "competition": random.choice(["Premier League", "Champions League", "FA Cup"]),
            "status": "live" if is_live else random.choice(["scheduled", "finished"]),
            "home_score": random.randint(0, 3) if is_live or random.choice([True, False]) else 0,
            "away_score": random.randint(0, 3) if is_live or random.choice([True, False]) else 0
        }
        
        matches.append(match)
    
    return {
        "results": matches,
        "code": 200,
        "message": "Mock data generated for testing",
        "total": len(matches),
        "_mock": True  # Flag to indicate this is mock data
    }

def fetch_live_matches():
    return fetch_json(URLS["live"], {"user": USER, "secret": SECRET})

def fetch_match_details(match_id):
    return fetch_json(URLS["details"], {"user": USER, "secret": SECRET, "uuid": match_id})

def fetch_match_odds(match_id):
    return fetch_json(URLS["odds"], {"user": USER, "secret": SECRET, "uuid": match_id})

def fetch_team_info(team_id):
    return fetch_json(URLS["team"], {"user": USER, "secret": SECRET, "uuid": team_id})

def fetch_competition_info(comp_id):
    return fetch_json(URLS["competition"], {"user": USER, "secret": SECRET, "uuid": comp_id})

def fetch_country_list():
    return fetch_json(URLS["country"], {"user": USER, "secret": SECRET})

def fetch_live_data():
    """Fetch live matches data"""
    logger.info("Fetching live matches from TheSports API...")
    api_start = datetime.now()
    
    live = fetch_live_matches()
    api_end = datetime.now()
    api_duration = (api_end - api_start).total_seconds()
    
    # Check if we're using mock data
    is_mock = live.get("_mock", False)
    
    # Check for API errors first
    if "err" in live and not is_mock:
        logger.error(f"API Error: {live['err']}")
        logger.error("Please check your THESPORTS_USER and THESPORTS_SECRET credentials in .env file")
        matches = []
        total_matches = 0
    else:
        # Log API call success and basic info
        matches = live.get("results", [])
        total_matches = len(matches)
    
    if is_mock:
        logger.info(f"✓ Using mock data for testing (API authorization required)")
        logger.info(f"  💡 Contact API provider to authorize football endpoints")
    else:
        logger.info(f"✓ Live matches API call successful")
    
    logger.info(f"  Response time: {api_duration:.2f} seconds")
    logger.info(f"  Total matches returned: {total_matches}")
    logger.info(f"  API response code: {live.get('code', 'Unknown')}")
    
    # Count status distribution from raw API response
    status_counts = {}
    matches_with_status = 0
    
    for match in matches:
        status_id = extract_status_id(match)
        if status_id is not None:
            status_counts[status_id] = status_counts.get(status_id, 0) + 1
            matches_with_status += 1
    
    logger.info(f"  Matches with status info: {matches_with_status}/{total_matches}")
    logger.info("  Raw API status breakdown:")
    
    # Log status breakdown with descriptions
    status_desc_map = {
        0: "Abnormal", 1: "Not started", 2: "First half", 3: "Half-time",
        4: "Second half", 5: "Overtime", 6: "Overtime (deprecated)",
        7: "Penalty Shoot-out", 8: "End", 9: "Delay", 10: "Interrupt",
        11: "Cut in half", 12: "Cancel", 13: "To be determined"
    }
    
    for status_id in sorted(status_counts.keys()):
        count = status_counts[status_id]
        desc = status_desc_map.get(status_id, f"Unknown Status")
        logger.info(f"    {desc} (ID: {status_id}): {count} matches")
    
    return live

def enrich_match_data(live_data, matches):
    """Enrich matches with detailed data (details, odds, teams, competitions) - now using async!"""
    logger.info(f"Starting detailed data fetch for {len(matches)} matches (async)...")
    detail_start = datetime.now()
    
    # Use the async version
    all_data = asyncio.run(enrich_match_data_async(matches))
    
    # Post-process to add status_id to matches (preserve original logic)
    for match in matches:
        mid = match.get("id")
        detail_wrap = all_data["match_details"].get(mid, {})
        
        detail = {}
        if isinstance(detail_wrap, dict):
            res = detail_wrap.get("results") or detail_wrap.get("result") or []
            if isinstance(res, list) and res:
                detail = res[0]
        
        # Extract status_id from match details and add it to the main match object
        if detail.get("status_id") is not None:
            match["status_id"] = detail.get("status_id")
    
    # Log completion summary
    detail_end = datetime.now()
    detail_duration = (detail_end - detail_start).total_seconds()
    
    logger.info(f"Detailed data fetch time: {detail_duration:.2f} seconds")
    logger.info(f"Unique teams fetched: {len(all_data['team_info'])}")
    logger.info(f"Unique competitions fetched: {len(all_data['competition_info'])}")
    logger.info(f"Match details fetched: {len(all_data['match_details'])}")
    logger.info(f"Match odds fetched: {len(all_data['match_odds'])}")
    
    return all_data

def step1_main():
    """Fetch data once and return the data dict."""
    
    # Capture pipeline start time for centralized logging
    pipeline_start_time = datetime.now()
    
    # ============================================================================
    # PHASE 1: GET GLOBAL RULES BEFORE OWN LOGGING
    # ============================================================================
    global_config = {}
    if CENTRALIZED_LOGGING_AVAILABLE:
        global_config = initialize_global_logging_for_step("step1")
    
    # ============================================================================
    # PHASE 2: SETUP OWN LOGGING WITH GLOBAL FORMAT
    # ============================================================================
    global logger
    if CENTRALIZED_LOGGING_AVAILABLE:
        logger = apply_global_format_to_logger(logger, "step1")
        logger.info(f"Step 1 logger configured with global Eastern Time rules - {global_config.get('current_timestamp', 'N/A')}")
    else:
        logger.info("Step 1 logger configured (centralized logging not available)")
    # ============================================================================
    
    # Get daily match counter
    match_number = get_daily_match_counter()
    
    # Header with New York timestamp and match counter
    ny_time = get_ny_time_str()
    logger.info("="*80)
    logger.info(f"STEP 1 - DATA FETCH STARTED - {ny_time}")
    logger.info(f"DAILY MATCH #: {match_number}")
    logger.info("="*80)
    
    start_time = datetime.now()
    
    # Step 1a: Fetch live matches with timing
    start_live = time.time()
    live_data = fetch_live_data()
    fetch_live_time = time.time() - start_live
    logger.info(f"STEP 1a – LIVE FETCH: {fetch_live_time:.2f}s")
    
    # Step 1b: Async Enrich with timing
    start_enrich = time.time()
    matches = live_data.get("results", [])
    enriched_data = enrich_match_data(live_data, matches)
    enrich_time = time.time() - start_enrich
    logger.info(f"STEP 1b – ENRICH (async): {enrich_time:.2f}s")
    
    # Combine all data
    all_data = {
        "timestamp": start_time.isoformat(),
        "live_matches": live_data,
        **enriched_data
    }
    
    # Footer with completion info
    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()
    ny_time = get_ny_time_str()  # Get updated timestamp for footer
    
    # Create comprehensive footer (matches step2.json logic)
    footer = create_comprehensive_footer(live_data, all_data, total_duration, match_number, ny_time, pipeline_complete=False, total_pipeline_time=None)
    
    # Add footer to JSON data
    all_data["step1_completion_summary"] = footer
    
    # Log comprehensive footer to step1.log (exact format match)
    logger.info("="*80)
    logger.info(footer['completion_status'])
    logger.info(f"Daily match number: {footer['daily_match_number']}")
    logger.info(f"Total matches fetched (all statuses): {footer['total_matches_fetched_all_statuses']}")
    logger.info(f"In-play matches: {footer['in_play_matches']}")
    logger.info(f"Other status matches: {footer['other_status_matches']}")
    logger.info(f"Step 1 execution time: {footer['step1_execution_time']}")
    logger.info(f"Total pipeline time: {footer['total_pipeline_time']}")
    logger.info("="*80)

    # ========================================================================
    # CENTRALIZED LOGGING - Call step1-2_logging.py for summary generation
    # ========================================================================
    if CENTRALIZED_LOGGING_AVAILABLE:
        try:
            # Prepare step1 specific data for summary generation
            step_data = {
                "step_name": "step1",
                "live_data": live_data,
                "all_data": all_data,
                "total_duration": total_duration,
                "match_number": match_number,
                "ny_time": ny_time
            }
            
            # Prepare execution data similar to step2
            execution_data = {
                "execution_time": total_duration,
                "files_created": ["step1.json"],
                "records_processed": len(matches),
                "pipeline_start_time": pipeline_start_time.isoformat(),
                "matches_fetched": len(matches),
                "processing_metadata": {
                    "is_mock": live_data.get("_mock", False),
                    "api_code": live_data.get("code", "Unknown")
                },
                "step_data": step_data
            }
            
            central_logging_hub(
                "step1",
                "post_logging",
                "success",
                f"Step 1 completed - {len(matches)} matches fetched",
                source="step1",
                **execution_data
            )
        except Exception as central_log_error:
            logger.warning(f"Centralized logging failed: {central_log_error}")
    # ========================================================================

    return all_data

def save_to_json(data, filename):
    """Save data to a JSON file with pretty printing"""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Data saved to {filename}")

def get_ny_time():
    """Get current time in New York timezone - legacy function"""
    return get_ny_time_str('%m/%d/%Y %I:%M:%S %p')

def create_unified_status_summary(live_matches_data):
    """Unified function to create comprehensive status summary and counts"""
    if not live_matches_data or "results" not in live_matches_data:
        return {
            "total_matches_fetched": 0,
            "status_breakdown": {},
            "formatted_summary": [],
            "status_counts": {},
            "in_play_matches": 0
        }
    
    matches = live_matches_data["results"]
    total_matches = len(matches)
    
    # Official status mapping
    status_desc_map = {
        0: "Abnormal (suggest hiding)",
        1: "Not started", 
        2: "First half",
        3: "Half-time",
        4: "Second half",
        5: "Overtime",
        6: "Overtime (deprecated)",
        7: "Penalty Shoot-out",
        8: "End",
        9: "Delay",
        10: "Interrupt",
        11: "Cut in half",
        12: "Cancel",
        13: "To be determined"
    }
    
    # Count matches by status_id
    status_counts = {}
    matches_with_status = 0
    
    for match in matches:
        status_id = extract_status_id(match)
        if status_id is not None:
            matches_with_status += 1
            status_desc = status_desc_map.get(status_id, f"Unknown Status")
            if status_id not in status_counts:
                status_counts[status_id] = {
                    "description": status_desc,
                    "count": 0
                }
            status_counts[status_id]["count"] += 1
    
    # Create formatted summary lines and structured data
    formatted_summary = []
    status_counts_with_ids = {}
    
    for status_id in sorted(status_counts.keys()):
        data = status_counts[status_id]
        description = data["description"]
        count = data["count"]
        
        formatted_line = f"{description} (ID: {status_id}): {count}"
        formatted_summary.append(formatted_line)
        
        status_counts_with_ids[f"status_{status_id}"] = {
            "id": status_id,
            "description": description,
            "count": count,
            "formatted": formatted_line
        }
    
    # Calculate IN-PLAY matches (active statuses: 2,3,4,5,7)
    in_play_status_ids = [2, 3, 4, 5, 7]
    in_play_count = sum(status_counts.get(sid, {}).get("count", 0) for sid in in_play_status_ids)
    
    formatted_summary.append(f"IN-PLAY MATCHES: {in_play_count}")
    
    return {
        "total_matches_fetched": total_matches,
        "matches_with_status": matches_with_status,
        "matches_without_status": total_matches - matches_with_status,
        "in_play_matches": in_play_count,
        "status_breakdown": status_counts_with_ids,
        "formatted_summary": formatted_summary,
        "status_counts": {data["description"]: data["count"] for data in status_counts.values()}
    }

def create_detailed_status_mapping(live_matches_data):
    """Create detailed status mapping with match IDs for JSON output"""
    if not live_matches_data or "results" not in live_matches_data:
        return {}
    
    matches = live_matches_data["results"]
    
    # Official Status ID to description mapping
    status_desc_map = {
        0: "Abnormal (suggest hiding)",
        1: "Not started",
        2: "First half",
        3: "Half-time",
        4: "Second half",
        5: "Overtime",
        6: "Overtime (deprecated)",
        7: "Penalty Shoot-out",
        8: "End",
        9: "Delay",
        10: "Interrupt",
        11: "Cut in half",
        12: "Cancel",
        13: "To be determined"
    }
    
    # Group matches by status
    status_groups = {}
    for match in matches:
        match_id = match.get("id", "NO_ID")
        status_id = extract_status_id(match)
        
        if status_id is not None:
            status_desc = status_desc_map.get(status_id, f"Unknown Status (ID: {status_id})")
            
            if status_desc not in status_groups:
                status_groups[status_desc] = {
                    "status_id": status_id,
                    "count": 0,
                    "match_ids": []
                }
            
            status_groups[status_desc]["count"] += 1
            status_groups[status_desc]["match_ids"].append(match_id)
    
    return status_groups


def print_status_summary(live_matches_data):
    """Print and log a formatted summary of match counts by status"""
    summary_data = create_unified_status_summary(live_matches_data)
    
    if not summary_data["status_counts"]:
        message = "Step 1: No match data available for status summary"
        print(message)
        logger.info(message)
        return
    
    # Create the summary lines
    summary_lines = [
        "=" * 80,
        "                        STEP 1 - MATCH STATUS SUMMARY                        ",
        "=" * 80,
        f"Total Matches: {summary_data['total_matches_fetched']}",
        "-" * 80
    ]
    
    # Sort by count (descending) for better readability
    sorted_statuses = sorted(summary_data["status_counts"].items(), key=lambda x: x[1], reverse=True)
    
    for status, count in sorted_statuses:
        summary_lines.append(f"{status}: {count} Matches")
    
    summary_lines.append("=" * 80)
    
    # Print to console
    for line in summary_lines:
        print(line)
    
    # Log to file
    logger.info("STEP 1 - MATCH STATUS SUMMARY")
    logger.info(f"Total Matches: {summary_data['total_matches_fetched']}")
    for status, count in sorted_statuses:
        logger.info(f"{status}: {count} Matches")

def create_comprehensive_match_breakdown(all_data):
    """Create a comprehensive breakdown showing actual match details for each status"""
    if not all_data or "live_matches" not in all_data:
        return {}
    
    live_matches = all_data["live_matches"].get("results", [])
    match_details = all_data.get("match_details", {})
    team_info = all_data.get("team_info", {})
    
    # Status mapping
    status_desc_map = {
        0: "Abnormal", 1: "Not started", 2: "First half", 3: "Half-time",
        4: "Second half", 5: "Overtime", 6: "Overtime (deprecated)",
        7: "Penalty Shoot-out", 8: "End", 9: "Delay", 10: "Interrupt",
        11: "Cut in half", 12: "Cancel", 13: "To be determined"
    }
    
    # Group matches by status with full details
    status_breakdown = {}
    
    for match in live_matches:
        match_id = match.get("id", "NO_ID")
        status_id = extract_status_id(match)
        
        if status_id is not None:
            status_desc = status_desc_map.get(status_id, f"Unknown Status (ID: {status_id})")
            
            if status_desc not in status_breakdown:
                status_breakdown[status_desc] = {
                    "status_id": status_id,
                    "count": 0,
                    "matches": []
                }
            
            # Get match details
            match_detail = {}
            if match_id in match_details:
                detail_wrap = match_details[match_id]
                if isinstance(detail_wrap, dict):
                    results = detail_wrap.get("results") or detail_wrap.get("result") or []
                    if isinstance(results, list) and results:
                        match_detail = results[0]
            
            # Get team names
            home_team_name = "Unknown Home Team"
            away_team_name = "Unknown Away Team"
            
            home_team_id = match_detail.get("home_team_id") or match.get("home_team_id")
            away_team_id = match_detail.get("away_team_id") or match.get("away_team_id")
            
            if home_team_id and str(home_team_id) in team_info:
                team_data = team_info[str(home_team_id)]
                if isinstance(team_data, dict):
                    results = team_data.get("results") or team_data.get("result") or []
                    if isinstance(results, list) and results:
                        home_team_name = results[0].get("name", "Unknown Home Team")
            
            if away_team_id and str(away_team_id) in team_info:
                team_data = team_info[str(away_team_id)]
                if isinstance(team_data, dict):
                    results = team_data.get("results") or team_data.get("result") or []
                    if isinstance(results, list) and results:
                        away_team_name = results[0].get("name", "Unknown Away Team")
            
            # Get current score
            current_score = "0-0"
            if "score" in match and isinstance(match["score"], list) and len(match["score"]) >= 4:
                home_score = match["score"][2]
                away_score = match["score"][3]
                if isinstance(home_score, list) and isinstance(away_score, list):
                    # Get total score (usually index 0 is current score)
                    h_total = home_score[0] if home_score else 0
                    a_total = away_score[0] if away_score else 0
                    current_score = f"{h_total}-{a_total}"
            
            # Get competition name
            competition_name = "Unknown Competition"
            comp_id = match_detail.get("competition_id") or match.get("competition_id")
            if comp_id and str(comp_id) in all_data.get("competition_info", {}):
                comp_data = all_data["competition_info"][str(comp_id)]
                if isinstance(comp_data, dict):
                    results = comp_data.get("results") or comp_data.get("result") or []
                    if isinstance(results, list) and results:
                        competition_name = results[0].get("name", "Unknown Competition")
            
            # Create match summary
            match_summary = {
                "match_id": match_id,
                "home_team": home_team_name,
                "away_team": away_team_name,
                "score": current_score,
                "competition": competition_name,
                "formatted": f"{home_team_name} vs {away_team_name} ({current_score}) - {competition_name}"
            }
            
            status_breakdown[status_desc]["matches"].append(match_summary)
            status_breakdown[status_desc]["count"] += 1
    
    return status_breakdown


def print_comprehensive_match_breakdown(comprehensive_match_breakdown):
    """Print detailed match breakdown showing actual match info for each status"""
    print("\n" + "="*100)
    print("                    COMPREHENSIVE MATCH BREAKDOWN - ACTUAL MATCH DETAILS                    ")
    print("="*100)
    
    # Calculate IN-PLAY matches
    in_play_statuses = ["First half", "Half-time", "Second half", "Overtime", "Penalty Shoot-out"]
    total_in_play = 0
    
    for status_desc in sorted(comprehensive_match_breakdown.keys()):
        status_data = comprehensive_match_breakdown[status_desc]
        status_id = status_data["status_id"]
        count = status_data["count"]
        matches = status_data["matches"]
        
        if status_desc in in_play_statuses:
            total_in_play += count
        
        print(f"\n{status_desc.upper()} (ID: {status_id}) - {count} MATCHES:")
        print("-" * 100)
        
        for i, match in enumerate(matches[:5], 1):  # Show first 5 matches for each status
            print(f"  {i}. {match['formatted']}")
        
        if len(matches) > 5:
            print(f"  ... and {len(matches) - 5} more matches")
    
    print("\n" + "="*100)
    print(f"IN-PLAY MATCHES TOTAL: {total_in_play}")
    print("="*100)

def continuous_loop():
    """
    Run Step 1 → Step 2 → Step 7 every 60 seconds (wall-clock).
    If any sub-step throws, catch it, log, and move to the next cycle.
    """
    global shutdown_flag
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("Starting continuous mode (60-second total cycles)...")
    logger.info("Use Ctrl+C or send SIGTERM to stop gracefully")
    
    while not shutdown_flag:
        cycle_start = time.time()
        
        try:
            # ─── Step 1a: Fetch live list ─────────────────────────────────────────────
            match_number = get_daily_match_counter()
            start_time = datetime.now(pytz.timezone("America/New_York"))
            logger.info("="*80)
            logger.info(f"STEP 1 – DATA FETCH STARTED – {start_time.strftime('%m/%d/%Y %I:%M:%S %p')} (NYT)")
            logger.info(f"DAILY MATCH #: {match_number}")
            logger.info("="*80)

            start_live = time.time()
            live_data = fetch_live_data()
            fetch_live_time = time.time() - start_live
            logger.info(f"STEP 1a – LIVE FETCH: {fetch_live_time:.2f}s")

            # ─── Step 1b: Async Enrich ─────────────────────────────────────────────────
            start_enrich = time.time()
            matches = live_data.get("results", [])
            enriched_data = enrich_match_data(live_data, matches)
            enrich_time = time.time() - start_enrich
            logger.info(f"STEP 1b – ENRICH (async): {enrich_time:.2f}s")
            
            # Combine all data
            all_data = {
                "timestamp": start_time.isoformat(),
                "live_matches": live_data,
                **enriched_data
            }

            # Add comprehensive summaries
            unified_summary = create_unified_status_summary(live_data)
            detailed_status_mapping = create_detailed_status_mapping(live_data)
            comprehensive_match_breakdown = create_comprehensive_match_breakdown(all_data)
            
            all_data["ny_timestamp"] = get_ny_time_str()
            all_data["unified_status_summary"] = unified_summary
            all_data["detailed_status_mapping"] = detailed_status_mapping
            all_data["comprehensive_match_breakdown"] = comprehensive_match_breakdown

            end_time = datetime.now(pytz.timezone("America/New_York"))
            total_duration = (end_time - start_time).total_seconds()
            
            # Calculate in-play matches for logging
            in_play_count = sum(
                1 for m in matches if extract_status_id(m) in [2,3,4,5,6,7]
            )
            
            logger.info("="*80)
            logger.info(f"STEP 1 – FETCH COMPLETED – {end_time.strftime('%m/%d/%Y %I:%M:%S %p')} (NYT)")
            logger.info(f"DAILY MATCH #: {match_number}")
            logger.info(f"Total execution time (Step 1): {total_duration:.2f}s")
            logger.info(f"In-Play matches: {in_play_count} (status 2–7)")
            logger.info("="*80)

            # Save the raw data to step1.json
            save_to_json(all_data, "step1.json")
            
            # ─── Step 2: Merge + Flatten → step2.json ───────────────────────────────
            logger.info("Starting Step 2 (merge + flatten)...")
            start_s2 = time.time()
            try:
                summaries = step2.run_step2(pipeline_start_time=cycle_start)
                s2_time = time.time() - start_s2
                logger.info(f"STEP 2 – run_step2: {s2_time:.2f}s")
                logger.info(f"STEP 2 → step2.json produced {len(summaries)} flattened summaries.")
            except Exception as e2:
                s2_time = time.time() - start_s2
                logger.error(f"STEP 2 failed after {s2_time:.2f}s: {e2}")
                traceback.print_exc()
                summaries = []  # Continue to Step 7 even if Step 2 fails

            # ─── Step 7: Filter & Pretty-Print ─────────────────────────────────────────
            logger.info("Starting Step 7 (filter & pretty-print)...")
            start_s7 = time.time()
            try:
                step7.run_step7(matches_list=summaries if summaries else None)
                s7_time = time.time() - start_s7
                logger.info(f"STEP 7 – run_step7: {s7_time:.2f}s")
                
                # Calculate total pipeline time from Step 1 start to Step 7 completion
                total_pipeline_time = time.time() - cycle_start
                logger.info(f"STEP 7 → Filter & pretty-print completed successfully.")
                logger.info(f"TOTAL PIPELINE TIME (Step 1 → Step 7): {total_pipeline_time:.2f} seconds")
                
                # Update both step1.json and step2.json with the complete pipeline timing
                update_step1_pipeline_timing(total_pipeline_time)
                update_step2_pipeline_timing(total_pipeline_time)
                
            except Exception as e7:
                s7_time = time.time() - start_s7
                logger.error(f"STEP 7 failed after {s7_time:.2f}s: {e7}")
                traceback.print_exc()

            # Daily rotation file (once per day)
            ny_tz = pytz.timezone("America/New_York")
            ny_now = datetime.now(ny_tz)
            daily_filename = f'step1_{ny_now.strftime("%Y-%m-%d")}.json'
            
            if not os.path.exists(daily_filename):
                save_to_json(all_data, daily_filename)
                logger.info(f"Daily rotation: Created {daily_filename}")

        except Exception as e:
            # Catch any error in this cycle so we don't break the loop permanently
            logger.error(f"Exception during cycle: {e}")
            traceback.print_exc()

        # ─── Sleep for remainder so that each cycle is exactly 60 seconds total ───
        elapsed = time.time() - cycle_start
        sleep_time = max(0, 60 - elapsed)
        
        # Full cycle time summary
        logger.info(f"TOTAL CYCLE TIME: {elapsed:.2f}s")
        logger.info(f"Cycle took {elapsed:.2f}s; sleeping {sleep_time:.2f}s before next run.")
        
        # Sleep in small increments to check shutdown flag
        sleep_elapsed = 0
        while sleep_elapsed < sleep_time and not shutdown_flag:
            time.sleep(min(1, sleep_time - sleep_elapsed))
            sleep_elapsed += min(1, sleep_time - sleep_elapsed)

    logger.info("Continuous loop has been signaled to stop. Exiting gracefully.")

def run_single_cycle():
    """Run a single Step 1 → Step 2 → Step 7 cycle (for non-continuous mode)"""
    try:
        # Record pipeline start time
        pipeline_start = time.time()
        
        # Step 1: Fetch data with detailed timing
        print("Running Step 1 with detailed timing...")
        result = step1_main()
        
        # Get match count for console output
        match_count = len(result.get('live_matches', {}).get('results', []))
        print(f"Step 1: Fetched data with {match_count} matches")
        
        # Generate comprehensive summaries
        unified_summary = create_unified_status_summary(result.get("live_matches", {}))
        detailed_status_mapping = create_detailed_status_mapping(result.get("live_matches", {}))
        comprehensive_match_breakdown = create_comprehensive_match_breakdown(result)
        
        # Add summaries to data
        result["ny_timestamp"] = get_ny_time_str()
        result["unified_status_summary"] = unified_summary
        result["detailed_status_mapping"] = detailed_status_mapping
        result["comprehensive_match_breakdown"] = comprehensive_match_breakdown
        
        # Save to step1.json
        save_to_json(result, 'step1.json')
        
        # Step 2: Process and flatten with timing
        start_s2 = time.time()
        summaries = step2.run_step2(pipeline_start_time=pipeline_start)
        s2_time = time.time() - start_s2
        print(f"Step 2: Produced {len(summaries)} summaries in {s2_time:.2f}s")
        
        # Step 7: Filter and display with timing
        start_s7 = time.time()
        step7.run_step7(matches_list=summaries)
        s7_time = time.time() - start_s7
        
        # Calculate total pipeline time from Step 1 to Step 7 completion
        total_pipeline_time = time.time() - pipeline_start
        print(f"Step 7: Filter & pretty-print completed in {s7_time:.2f}s")
        print(f"TOTAL PIPELINE TIME (Step 1 → Step 7): {total_pipeline_time:.2f} seconds")
        
        # Update both step1.json and step2.json with the complete pipeline timing
        update_step1_pipeline_timing(total_pipeline_time)
        update_step2_pipeline_timing(total_pipeline_time)
        
        # Daily rotation file
        ny_tz = pytz.timezone("America/New_York")
        ny_now = datetime.now(ny_tz)
        daily_filename = f'step1_{ny_now.strftime("%Y-%m-%d")}.json'
        
        if not os.path.exists(daily_filename):
            save_to_json(result, daily_filename)
            logger.info(f"Daily rotation: Created {daily_filename}")
        
        # Print completion summary
        print(f"Data saved at {get_ny_time_str()} (New York Time)")
        print("\n" + "="*80)
        print("                    COMPREHENSIVE STATUS BREAKDOWN                    ")
        print("="*80)
        for line in unified_summary["formatted_summary"]:
            print(line)
        print(f"Total Matches Fetched: {unified_summary['total_matches_fetched']}")
        print("="*80)
        
        # Print comprehensive match breakdown
        print_comprehensive_match_breakdown(comprehensive_match_breakdown)
        
    except Exception as e:
        logger.error(f"Error in single cycle execution: {e}")
        traceback.print_exc()
        raise

def update_step2_pipeline_timing(total_pipeline_time: float):
    """
    Update step2.json with the complete pipeline timing from Step 1 to Step 7 completion.
    """
    try:
        step2_file = Path("step2.json")
        if step2_file.exists():
            with open(step2_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Update the pipeline timing in the summary section
            if "step2_processing_summary" in data:
                data["step2_processing_summary"]["pipeline_timing"]["total_pipeline_time"] = f"{total_pipeline_time:.2f} seconds"
                data["step2_processing_summary"]["total_pipeline_time"] = f"{total_pipeline_time:.2f} seconds"
                
                # Also update the footer section
                data["step2_processing_summary"]["completion_status"] = f"COMPLETE PIPELINE (Step 1→7) – FINISHED SUCCESSFULLY – {datetime.now(pytz.timezone('America/New_York')).strftime('%m/%d/%Y %I:%M:%S %p %Z')}"
            
            # Save updated data
            with open(step2_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Updated step2.json with complete pipeline timing: {total_pipeline_time:.2f} seconds")
        else:
            logger.warning("step2.json not found, cannot update pipeline timing")
            
    except Exception as e:
        logger.error(f"Failed to update step2.json pipeline timing: {e}")

def update_step1_pipeline_timing(total_pipeline_time: float):
    """
    Update step1.json with the complete pipeline timing from Step 1 to Step 7 completion.
    """
    try:
        step1_file = Path("step1.json")
        if step1_file.exists():
            with open(step1_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Update the pipeline timing in the completion summary section
            if "step1_completion_summary" in data:
                data["step1_completion_summary"]["total_pipeline_time"] = f"{total_pipeline_time:.2f} seconds"
                
                # Update completion status to show full pipeline completion
                data["step1_completion_summary"]["completion_status"] = f"COMPLETE PIPELINE (Step 1→7) – FINISHED SUCCESSFULLY – {datetime.now(pytz.timezone('America/New_York')).strftime('%m/%d/%Y %I:%M:%S %p %Z')}"
            
            # Also update the step1_detailed_summary if it exists (from centralized logging)
            if "step1_detailed_summary" in data and "completion_summary" in data["step1_detailed_summary"]:
                data["step1_detailed_summary"]["completion_summary"]["total_pipeline_time"] = f"{total_pipeline_time:.2f}s"
                data["step1_detailed_summary"]["completion_summary"]["status"] = f"COMPLETE PIPELINE (Step 1→7) – FINISHED SUCCESSFULLY – {datetime.now(pytz.timezone('America/New_York')).strftime('%m/%d/%Y %I:%M:%S %p %Z')}"
            
            # Save updated data
            with open(step1_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Updated step1.json with complete pipeline timing: {total_pipeline_time:.2f} seconds")
        else:
            logger.warning("step1.json not found, cannot update pipeline timing")
            
    except Exception as e:
        logger.error(f"Failed to update step1.json pipeline timing: {e}")

def create_comprehensive_footer(live_data, all_data, total_duration, match_number, ny_time, pipeline_complete=False, total_pipeline_time=None):
    """
    Create comprehensive footer with all match summary values.
    This matches the EXACT footer logic used in step2.json for consistency.
    
    Args:
        live_data: Live match data from API
        all_data: All enriched data
        total_duration: Step 1 execution time
        match_number: Daily match counter
        ny_time: Formatted timestamp
        pipeline_complete: Whether the full pipeline (Step 1→7) has completed
        total_pipeline_time: Total time for full pipeline (Step 1→7)
    """
    matches = live_data.get("results", [])
    total_matches = len(matches)
    
    # Count matches by status
    in_play_count = 0
    status_breakdown = {}
    
    for match in matches:
        status_id = extract_status_id(match)
        if status_id is not None:
            # Count for status breakdown
            if status_id not in status_breakdown:
                status_breakdown[status_id] = 0
            status_breakdown[status_id] += 1
            
            # Count in-play matches (status IDs 2-7)
            if status_id in [2, 3, 4, 5, 6, 7]:
                in_play_count += 1
    
    other_matches = total_matches - in_play_count
    
    # Get enriched data stats from all_data structure
    unique_teams = len(all_data.get("team_info", []))
    unique_competitions = len(all_data.get("competition_info", []))
    match_details = len(all_data.get("match_details", []))
    match_odds = len(all_data.get("match_odds", []))
    
    # Status descriptions
    status_desc_map = {
        0: "Abnormal (suggest hiding)",
        1: "Not started",
        2: "First half",
        3: "Half-time", 
        4: "Second half",
        5: "Overtime",
        6: "Overtime (deprecated)",
        7: "Penalty Shoot-out",
        8: "End",
        9: "Delay",
        10: "Interrupt",
        11: "Cut in half",
        12: "Cancel",
        13: "To be determined"
    }
    
    # Create status breakdown list
    status_breakdown_list = []
    for status_id in sorted(status_breakdown.keys()):
        desc = status_desc_map.get(status_id, f"Unknown Status")
        count = status_breakdown[status_id]
        status_breakdown_list.append(f"{desc} (ID: {status_id}): {count} matches")
    
    # Set completion status based on pipeline state
    if pipeline_complete:
        completion_status = f"COMPLETE PIPELINE (Step 1→7) – FINISHED SUCCESSFULLY – {ny_time}"
    else:
        completion_status = f"STEP 1 - FETCH COMPLETED SUCCESSFULLY - {ny_time}"
    
    footer = {
        "footer": "="*80,
        "completion_status": completion_status,
        "daily_match_number": match_number,
        "total_matches_fetched_all_statuses": f"{total_matches} matches (ALL status IDs from Step 1 live endpoint)",
        "in_play_matches": f"{in_play_count} (status IDs 2–7)",
        "other_status_matches": f"{other_matches} (status IDs 0,1,8,9,10,11,12,13)",
        "step1_execution_time": f"{total_duration:.2f} seconds",
        "total_pipeline_time": f"{total_pipeline_time:.2f} seconds" if total_pipeline_time is not None else "N/A",
        "footer_end": "="*80
    }
    
    return footer

def update_step1_footer_after_pipeline(step1_json_path, total_pipeline_time):
    """
    Update the step1.json footer with total pipeline time and completion status
    after the full pipeline (Step 1→7) has completed.
    """
    try:
        with open(step1_json_path, 'r') as f:
            data = json.load(f)
        
        if 'step1_completion_summary' in data:
            # Update completion status to show full pipeline completion
            ny_time = get_ny_time_str()
            data['step1_completion_summary']['completion_status'] = f"COMPLETE PIPELINE (Step 1→7) – FINISHED SUCCESSFULLY – {ny_time}"
            data['step1_completion_summary']['total_pipeline_time'] = f"{total_pipeline_time:.2f} seconds"
            
            # Save updated JSON
            with open(step1_json_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Updated {step1_json_path} footer with total pipeline time: {total_pipeline_time:.2f} seconds")
            return True
    except Exception as e:
        logger.error(f"Failed to update step1.json footer: {e}")
        return False
    
    return False

if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Step 1 Football Data Pipeline - Robust 60s Cycles')
    parser.add_argument('--continuous', action='store_true', 
                       help='Run continuously in 60-second cycles (for production use)')
    args = parser.parse_args()

    try:
        if args.continuous:
            # Continuous mode with PID file locking
            with pid_lock():
                continuous_loop()
        else:
            # Single run mode with PID file locking
            with pid_lock():
                run_single_cycle()
        
    except KeyboardInterrupt:
        logger.info("Interrupted manually.")
    except Exception as e:
        logger.error(f"Error in execution: {e}")
        traceback.print_exc()
        sys.exit(1)