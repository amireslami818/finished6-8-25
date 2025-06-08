#!/usr/bin/env python3
"""
Fix the step2 merge logic to properly merge all enriched data from step1
"""
import json

# Read the step2.py file
with open('step2.py', 'r') as f:
    step2_code = f.read()

# The issue is in the merge_and_summarize function
# We need to fix how it merges the enriched data

# Replace the merge_and_summarize function with a fixed version
fixed_merge_function = '''def merge_and_summarize(live_data: dict, payload_data: dict) -> dict:
    """Merge live data with payload data and create comprehensive summary."""
    
    # Extract matches from live data
    matches = live_data.get("results", [])
    
    # Extract enriched data from payload
    match_details = payload_data.get("match_details", {})
    match_odds = payload_data.get("match_odds", {})
    team_info = payload_data.get("team_info", {})
    competition_info = payload_data.get("competition_info", {})
    
    summaries = []
    for match in matches:
        match_id = str(match.get("id", ""))
        
        # Get enriched match details
        details_wrapper = match_details.get(match_id, {})
        details = {}
        if isinstance(details_wrapper, dict) and "results" in details_wrapper:
            detail_list = details_wrapper.get("results", [])
            if detail_list and isinstance(detail_list, list) and len(detail_list) > 0:
                details = detail_list[0]
        
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
            odds_list = odds_wrapper.get("results", [])
            if odds_list and isinstance(odds_list, list):
                match["odds"] = odds_list
        
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
        if comp_id and comp_id in competition_info:
            comp_wrapper = competition_info[comp_id]
            if isinstance(comp_wrapper, dict) and "results" in comp_wrapper:
                comp_results = comp_wrapper.get("results", [])
                if comp_results and isinstance(comp_results, list) and len(comp_results) > 0:
                    comp_data = comp_results[0]
                    match["league"]["name"] = comp_data.get("name", "Unknown")
                    match["league"]["short_name"] = comp_data.get("short_name", "")
                    match["league"]["logo"] = comp_data.get("logo", "")
                    # Get country info from competition
                    country_info = comp_data.get("country", {})
                    if isinstance(country_info, dict):
                        match["league"]["country_name"] = country_info.get("name", "Unknown")
                        match["league"]["country_code"] = country_info.get("code", "")
        
        # Set default values if still missing
        if not match.get("home", {}).get("name"):
            match["home"]["name"] = "Unknown"
        if not match.get("away", {}).get("name"):
            match["away"]["name"] = "Unknown"
        if not match.get("league", {}).get("name"):
            match["league"]["name"] = "Unknown"
        if not match.get("league", {}).get("country_name"):
            match["league"]["country_name"] = "Unknown"
            
        # Now extract summary with fully enriched data
        summary = extract_summary_fields(match)
        summary["odds"] = extract_odds(match)
        summary["environment"] = extract_environment(match)
        summary["events"] = extract_events(match)
        summaries.append(summary)'''

# Find the start of the merge_and_summarize function
import re
pattern = r'def merge_and_summarize\(live_data: dict, payload_data: dict\) -> dict:.*?(?=\ndef\s|\nclass\s|\Z)'
match = re.search(pattern, step2_code, re.DOTALL)

if match:
    # Replace the function
    new_code = step2_code[:match.start()] + fixed_merge_function + step2_code[match.end():]
    
    # Write the fixed code
    with open('step2.py', 'w') as f:
        f.write(new_code)
    
    print("Successfully updated step2.py with fixed merge logic!")
else:
    print("ERROR: Could not find merge_and_summarize function!")
