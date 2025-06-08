#!/usr/bin/env python3
import json

# Load step1 data
with open('step1.json', 'r') as f:
    step1_data = json.load(f)

# Extract data
live_matches = step1_data.get("live_matches", {})
matches = live_matches.get("results", [])
match_details = step1_data.get("match_details", {})
team_info = step1_data.get("team_info", {})
competition_info = step1_data.get("competition_info", {})

# Debug first match
if matches:
    match = matches[0]
    match_id = str(match.get("id", ""))
    print(f"Debugging match ID: {match_id}")
    print(f"Match object keys: {list(match.keys())}")
    print()
    
    # Check details
    details_wrapper = match_details.get(match_id, {})
    if details_wrapper and "results" in details_wrapper:
        details = details_wrapper["results"][0]
        print(f"Found details:")
        print(f"  home_team_id: {details.get('home_team_id')}")
        print(f"  away_team_id: {details.get('away_team_id')}")
        print(f"  competition_id: {details.get('competition_id')}")
        
        # Check team lookup
        home_id = str(details.get('home_team_id', ''))
        print(f"\nChecking home team ID: '{home_id}'")
        print(f"  Type: {type(home_id)}")
        print(f"  In team_info? {home_id in team_info}")
        
        # List some team_info keys
        print(f"\nFirst 5 team_info keys: {list(team_info.keys())[:5]}")
        
        # Try to find the team
        for tid, tdata in list(team_info.items())[:3]:
            print(f"\nTeam ID: '{tid}' (type: {type(tid)})")
            if "results" in tdata and tdata["results"]:
                print(f"  Name: {tdata['results'][0].get('name')}")
