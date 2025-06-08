#!/usr/bin/env python3
import json

# Load step1 data
with open('step1.json', 'r') as f:
    step1_data = json.load(f)

# Extract data like step2 does
live_matches = step1_data.get("live_matches", {})
payload_data = {k: v for k, v in step1_data.items() if k != "live_matches"}

# Get the collections
matches = live_matches.get("results", [])
match_details = payload_data.get("match_details", {})
team_info = payload_data.get("team_info", {})
competition_info = payload_data.get("competition_info", {})

print(f"Found {len(matches)} matches")
print(f"Found {len(match_details)} match details")
print(f"Found {len(team_info)} teams")
print(f"Found {len(competition_info)} competitions")
print()

# Test with first match
if matches:
    match = matches[0]
    match_id = str(match.get("id", ""))
    print(f"Testing match ID: {match_id}")
    
    # Get enriched match details
    details_wrapper = match_details.get(match_id, {})
    print(f"Details wrapper type: {type(details_wrapper)}")
    print(f"Has 'results' key: {'results' in details_wrapper}")
    
    details = {}
    if isinstance(details_wrapper, dict) and "results" in details_wrapper:
        detail_list = details_wrapper.get("results", [])
        print(f"Detail list length: {len(detail_list)}")
        if detail_list and isinstance(detail_list, list) and len(detail_list) > 0:
            details = detail_list[0]
            print(f"Got details: home_team_id={details.get('home_team_id')}, away_team_id={details.get('away_team_id')}")
    
    # Check team lookup
    if details:
        home_team_id = str(details.get("home_team_id", ""))
        print(f"\nLooking up home team ID: {home_team_id}")
        if home_team_id in team_info:
            team_data = team_info[home_team_id]
            print(f"Found team data: {team_data.get('results', [{}])[0].get('name', 'NOT FOUND')}")
        else:
            print(f"Team ID {home_team_id} NOT in team_info")
            print(f"Available team IDs (first 5): {list(team_info.keys())[:5]}")
