#!/usr/bin/env python3
"""
🚨 WARNING FOR FUTURE AI CODING AGENTS 🚨
==========================================
DO NOT CREATE DUPLICATE SUMMARY KEYS IN JSON OUTPUTS!
THIS PROJECT SUFFERED FROM "KEY UNIFORMITY PROBLEMS":

❌ NEVER CREATE: step1_completion_summary, step1_detailed_summary, step2_completion_summary, etc.
✅ ALWAYS USE: Single standardized "completion_summary" key across ALL JSON outputs
✅ USE SHARED: create_completion_summary() function from step1.py

KEY UNIFORMITY PROBLEM TERMS:
- "Duplicate Summary Keys" - Multiple different key names for the same purpose  
- "Legacy Summary Key Structures" - Old inconsistent naming patterns
- "completion_summary Standardization" - Ensuring all files use the same key structure

THIS IS THE BIGGEST PROBLEM WITH AI CODING AGENTS - AVOID RECREATING THIS ISSUE!
==================================================================================

STEP 2 - DATA MERGE AND FLATTEN
==============================

PURPOSE:
--------
Merges and flattens match data from step1.json, creating compact summaries
and saving them to step2.json with historical tracking.

LOGGING AND OUTPUT FILES:
------------------------
- **LOG OUTPUT**: Console logging via StreamHandler (no file logging)
- **JSON OUTPUT**: step2.json (flattened match summaries with standardized completion_summary)
- **INPUT SOURCE**: step1.json (from Step 1 processing)

CURRENT LOGGER IMPLEMENTATION:
-----------------------------
- **INDEPENDENT LOGGING**: Uses StreamHandler for console output only
- **LOG SUMMARY**: Printed to console AFTER JSON dump (not included in JSON)
- **JSON STRUCTURE**: Single standardized "completion_summary" as last element
- **NO DUPLICATES**: Uses shared create_completion_summary() function from step1.py
- **HISTORY MANAGEMENT**: Limits to 10 entries to prevent memory issues

USAGE:
------
Can be called directly or imported by step1.py for automatic pipeline execution.

OUTPUT:
-------
- step2.json: Contains flattened match summaries with historical data and standardized completion_summary
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
import pytz

# Import the standardized completion_summary function from step1
from step1 import create_completion_summary

# Centralized logging removed - using simplified approach

# Constants
TZ = pytz.timezone("America/New_York")
BASE_DIR = Path(__file__).resolve().parent
STEP1_JSON = BASE_DIR / "step1.json"
STEP2_JSON = BASE_DIR / "step2.json"

# CRITICAL: History limit to prevent memory issues
MAX_HISTORY_ENTRIES = 10  # Keep only last 10 entries instead of 100+

def extract_summary_fields(match: dict) -> dict:
    """Return a compact summary structure for a single match."""
    home_live = home_ht = away_live = away_ht = 0
    sd = match.get("score", [])
    if isinstance(sd, list) and len(sd) > 3:
        hs, as_ = sd[2], sd[3]
        if isinstance(hs, list) and len(hs) > 1:
            home_live, home_ht = hs[0], hs[1]
        if isinstance(as_, list) and len(as_) > 1:
            away_live, away_ht = as_[0], as_[1]

    home_scores = match.get("home_scores", [])
    away_scores = match.get("away_scores", [])
    if home_scores and home_live == 0:
        home_live = sum(home_scores)
    if away_scores and away_live == 0:
        away_live = sum(away_scores)

    # Calculate corner kicks
    corners_home = corners_away = 0
    stats = match.get("stats", [])
    if stats and len(stats) > 9:
        corners_data = stats[9]
        if isinstance(corners_data, list) and len(corners_data) >= 2:
            corners_home = corners_data[0] if corners_data[0] is not None else 0
            corners_away = corners_data[1] if corners_data[1] is not None else 0

    return {
        "match_id": match.get("id"),
        "id": match.get("id"),  # Keep both for compatibility
        "home": match.get("home", {}).get("name", "Unknown"),
        "away": match.get("away", {}).get("name", "Unknown"),
        "status_id": match.get("status_id", 0),
        "minute": match.get("minute", ""),
        "score_home": home_live,
        "score_away": away_live,
        "score_ht_home": home_ht,
        "score_ht_away": away_ht,
        "corners_home": corners_home,
        "corners_away": corners_away,
        "competition": match.get("league", {}).get("name", "Unknown"),
        "country": match.get("league", {}).get("country_name", "Unknown"),
        "start_time": match.get("start_time", ""),
        "priority": match.get("priority", 0)
    }

def extract_odds(match: dict) -> dict:
    """Extract betting odds in a structured format."""
    odds_data = match.get("odds", [])
    betting_odds = {}
    
    for odds_entry in odds_data:
        if not isinstance(odds_entry, list) or len(odds_entry) < 2:
            continue
            
        odds_type = odds_entry[0]
        
        if odds_type == "1x2":  # Match Result
            betting_odds["match_result"] = {
                "home": odds_entry[2] if len(odds_entry) > 2 else None,
                "draw": odds_entry[4] if len(odds_entry) > 4 else None,
                "away": odds_entry[3] if len(odds_entry) > 3 else None,
                "time": odds_entry[1] if len(odds_entry) > 1 else "0"
            }
        elif odds_type == "ou":  # Over/Under
            line = odds_entry[5] if len(odds_entry) > 5 else "0"
            if line not in betting_odds.get("over_under", {}):
                if "over_under" not in betting_odds:
                    betting_odds["over_under"] = {}
                betting_odds["over_under"][line] = {
                    "over": odds_entry[2] if len(odds_entry) > 2 else None,
                    "line": line,
                    "under": odds_entry[4] if len(odds_entry) > 4 else None
                }
    
    return betting_odds

def extract_environment(match: dict) -> dict:
    """Extract environmental/venue information."""
    return {
        "venue": match.get("venue"),
        "weather": match.get("weather"),
        "temperature": match.get("temperature"),
        "humidity": match.get("humidity"),
        "wind_speed": match.get("wind_speed"),
        "pitch_condition": match.get("pitch_condition")
    }

def extract_events(match: dict) -> list:
    """Extract and format match events."""
    events = match.get("events", [])
    formatted_events = []
    
    for event in events:
        if isinstance(event, dict):
            formatted_events.append({
                "minute": event.get("minute"),
                "type": event.get("type"),
                "player": event.get("player"),
                "team": event.get("team"),
                "description": event.get("description")
            })
    
    return formatted_events

def merge_and_summarize(live_data: dict, payload_data: dict) -> dict:
    """Merge live data with payload data and create comprehensive summary."""
    
    # Extract matches from live data
    matches = live_data.get("results", [])
    
    summaries = []
    for match in matches:
        summary = extract_summary_fields(match)
        summary["odds"] = extract_odds(match)
        summary["environment"] = extract_environment(match)
        summary["events"] = extract_events(match)
        summaries.append(summary)
    
    # Create comprehensive summary
    total_matches = len(summaries)
    in_play_matches = [s for s in summaries if s["status_id"] in {2, 3, 4, 5, 6, 7}]
    
    return {
        "timestamp": datetime.now(TZ).isoformat(),
        "ny_timestamp": datetime.now(TZ).strftime("%m/%d/%Y %I:%M:%S %p %Z"),
        "total_matches": total_matches,
        "in_play_count": len(in_play_matches),
        "summaries": summaries,
        "metadata": {
            "source": "step1.json",
            "processed_by": "step2.py",
            "total_live_matches": total_matches,
            "processing_time": 0  # Will be updated
        }
    }

def save_match_summaries(summaries_data: dict, output_file: str = "step2.json") -> bool:
    """Save summaries with history management to prevent memory issues."""
    try:
        output_path = Path(output_file)
        existing_data = {"history": []}
        
        # Load existing data if file exists
        if output_path.exists():
            try:
                with open(output_path, 'r') as f:
                    existing_data = json.load(f)
                    if not isinstance(existing_data, dict):
                        existing_data = {"history": []}
                    if "history" not in existing_data:
                        existing_data["history"] = []
            except (json.JSONDecodeError, Exception) as e:
                logging.warning(f"Could not load existing {output_file}: {e}")
                existing_data = {"history": []}
        
        # Add current data to history
        existing_data["history"].append(summaries_data)
        
        # CRITICAL: Limit history to prevent memory issues
        if len(existing_data["history"]) > MAX_HISTORY_ENTRIES:
            # Keep only the most recent entries
            existing_data["history"] = existing_data["history"][-MAX_HISTORY_ENTRIES:]
            logging.info(f"Trimmed history to {MAX_HISTORY_ENTRIES} entries to prevent memory issues")
        
        # Update metadata
        existing_data["last_updated"] = datetime.now(TZ).isoformat()
        existing_data["total_entries"] = len(existing_data["history"])
        
        # Add standardized completion_summary 
        current_data = summaries_data
        total_summaries = len(current_data.get("summaries", []))
        in_play_summaries = len([s for s in current_data.get("summaries", []) if s.get("status_id") in {2, 3, 4, 5, 6, 7}])
        processing_time = current_data.get("metadata", {}).get("processing_time", 0.0)
        
        completion_summary = create_completion_summary(
            step_name="MERGE/FLATTEN",
            step_number=2,
            matches_count=total_summaries,
            in_play_count=in_play_summaries,
            processing_time=processing_time,
            daily_number="N/A",
            endpoint_type="summaries"
        )
        existing_data["completion_summary"] = completion_summary
        
        # Save to file
        with open(output_path, 'w') as f:
            json.dump(existing_data, f, indent=2)
        
        logging.info(f"Saved step2 data to {output_file} (history: {len(existing_data['history'])} entries)")
        
        # Print log summary AFTER JSON dump (not included in JSON)
        print_step2_log_summary(total_summaries, in_play_summaries, processing_time, output_file)
        
        return True
        
    except Exception as e:
        logging.error(f"Failed to save step2 data: {e}")
        return False

def run_step2(pipeline_start_time: float = None) -> list:
    """
    Main entry point for Step 2 processing.
    Called by step1.py during pipeline execution.
    
    Returns:
        list: Summaries data for use in step7
    """
    
    # ============================================================================
    # SIMPLIFIED LOGGING SETUP
    # ============================================================================
    logger = logging.getLogger("step2")
    if not logger.handlers:
        # Add handlers if not already present
        handler = logging.StreamHandler()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    logger.info("Step 2 logger configured with simplified logging")
    # ============================================================================
    
    try:
        start_time = time.time()
        
        # Load step1.json data
        if not STEP1_JSON.exists():
            logger.error(f"Step1 data file not found: {STEP1_JSON}")
            return []
        
        with open(STEP1_JSON, 'r') as f:
            step1_data = json.load(f)
        
        # Extract live matches and other payload data
        live_matches = step1_data.get("live_matches", {})
        payload_data = {k: v for k, v in step1_data.items() if k != "live_matches"}
        
        # Process and merge data
        merged_data = merge_and_summarize(live_matches, payload_data)
        
        # Update processing time
        processing_time = time.time() - start_time
        merged_data["metadata"]["processing_time"] = processing_time
        
        # Save to step2.json
        success = save_match_summaries(merged_data, str(STEP2_JSON))
        
        if success:
            logger.info(f"Step2 completed successfully in {processing_time:.2f}s")
            
            return merged_data.get("summaries", [])
        else:
            logger.error("Step2 failed to save data")
            return []
            
    except Exception as e:
        logger.error(f"Step2 processing failed: {e}")
        return []

def get_ny_time_str():
    """Get New York time as formatted string"""
    return datetime.now(TZ).strftime("%m/%d/%Y %I:%M:%S %p %Z")

def print_step2_log_summary(total_summaries, in_play_summaries, processing_time, output_file):
    """Print step2 log summary after JSON dump (not included in JSON)"""
    print("\n" + "="*60)
    print("STEP 2 EXECUTION SUMMARY")
    print("="*60)
    print(f"Total summaries created: {total_summaries}")
    print(f"In-play summaries: {in_play_summaries} (status IDs 2-7)")
    print(f"Other status summaries: {total_summaries - in_play_summaries} (status IDs 0,1,8+)")
    print(f"Processing time: {processing_time:.2f}s")
    print(f"JSON output: {output_file}")
    print(f"Input source: step1.json")
    print(f"Timestamp: {get_ny_time_str()}")
    print("="*60)

def main():
    """Standalone execution for testing."""
    logging.basicConfig(level=logging.INFO)
    
    print("Step 2: Starting data merge and flatten...")
    summaries = run_step2()
    print(f"Step 2: Completed with {len(summaries)} summaries")

if __name__ == "__main__":
    main()
