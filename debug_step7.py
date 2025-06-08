#!/usr/bin/env python3
import json

# Load step2.json the way step7 does
with open("step2.json", "r", encoding="utf-8") as f:
    all_data = json.load(f)

history = all_data.get("history", [])
print(f"History entries: {len(history)}")

if history:
    last_batch = history[-1]
    print(f"Last batch keys: {list(last_batch.keys())}")
    
    raw_matches = last_batch.get("matches", {})
    print(f"Number of matches: {len(raw_matches)}")
    
    # Filter for status 2-7
    filtered = {
        mid: mdata
        for mid, mdata in raw_matches.items()
        if mdata.get("status_id") in [2, 3, 4, 5, 6, 7]
    }
    print(f"Filtered matches (status 2-7): {len(filtered)}")
    
    # Show first few
    for i, (mid, match) in enumerate(list(filtered.items())[:3]):
        print(f"\n{i+1}. Match ID: {mid}")
        print(f"   Teams: {match.get('teams', {})}")
        print(f"   Status: {match.get('status_id')}")
