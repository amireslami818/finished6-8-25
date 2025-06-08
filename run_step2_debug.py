#!/usr/bin/env python3
import json
import sys
from step2 import merge_and_summarize, save_match_summaries, STEP2_JSON
import time
from datetime import datetime
import pytz

TZ = pytz.timezone("America/New_York")

# Load step1.json
with open('step1.json', 'r') as f:
    step1_data = json.load(f)

print(f"Loaded step1.json with {len(step1_data)} keys")

# Extract data
live_matches = step1_data.get("live_matches", {})
payload_data = {k: v for k, v in step1_data.items() if k != "live_matches"}

print(f"Live matches has {len(live_matches.get('results', []))} results")
print(f"Payload has match_details: {'match_details' in payload_data}")
print(f"Payload has team_info: {'team_info' in payload_data}")
print(f"Number of teams: {len(payload_data.get('team_info', {}))}")

# Run merge
start_time = time.time()
merged_data = merge_and_summarize(live_matches, payload_data)
processing_time = time.time() - start_time

print(f"\nMerge completed in {processing_time:.2f}s")
print(f"Created {len(merged_data['summaries'])} summaries")

# Check first few summaries
for i, summary in enumerate(merged_data['summaries'][:3]):
    print(f"\nSummary {i+1}:")
    print(f"  {summary['home']} vs {summary['away']}")
    print(f"  Competition: {summary['competition']} ({summary['country']})")

# Update processing time
merged_data["metadata"]["processing_time"] = processing_time

# Save
success = save_match_summaries(merged_data, str(STEP2_JSON))
print(f"\nSave successful: {success}")
