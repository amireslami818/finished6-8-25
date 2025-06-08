#!/usr/bin/env python3
import json
from step2 import merge_and_summarize

# Load step1 data
with open('step1.json', 'r') as f:
    step1_data = json.load(f)

live_matches = step1_data.get("live_matches", {})
payload_data = {k: v for k, v in step1_data.items() if k != "live_matches"}

# Test the merge
result = merge_and_summarize(live_matches, payload_data)

# Check first summary
if result["summaries"]:
    summary = result["summaries"][0]
    print(f"First summary:")
    print(f"  ID: {summary['match_id']}")
    print(f"  Home: {summary['home']}")
    print(f"  Away: {summary['away']}")
    print(f"  Competition: {summary['competition']}")
    print(f"  Country: {summary['country']}")
    print(f"  Status: {summary['status_id']}")
    
    # Check the raw match data before summary extraction
    matches = live_matches.get("results", [])
    if matches:
        match = matches[0]
        print(f"\nFirst match after merge (before summary extraction):")
        print(f"  home object: {match.get('home', {})}")
        print(f"  away object: {match.get('away', {})}")
        print(f"  league object: {match.get('league', {})}")
