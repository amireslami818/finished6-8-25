#!/usr/bin/env python3
import json

# Load step1.json to analyze the data structure
with open('step1.json', 'r') as f:
    data = json.load(f)

def extract_fields(obj, prefix=""):
    """Recursively extract all field names from a JSON object"""
    fields = set()
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            if prefix:
                field_path = f"{prefix}.{key}"
            else:
                field_path = key
            fields.add(field_path)
            
            # Recurse into nested objects but not arrays
            if isinstance(value, dict):
                fields.update(extract_fields(value, field_path))
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                # Sample first item of array
                fields.update(extract_fields(value[0], field_path + "[0]"))
    
    return fields

# Analyze each endpoint's data
print("=== API ENDPOINTS AND THEIR JSON FIELDS ===\n")

# 1. LIVE MATCHES ENDPOINT (/match/detail_live)
print("1. LIVE MATCHES ENDPOINT (/match/detail_live)")
print("-" * 50)
if "live_matches" in data and "results" in data["live_matches"]:
    matches = data["live_matches"]["results"]
    if matches:
        fields = extract_fields(matches[0])
        for field in sorted(fields):
            print(f"  {field}")
print()

# 2. MATCH DETAILS ENDPOINT (/match/recent/list)
print("2. MATCH DETAILS ENDPOINT (/match/recent/list)")
print("-" * 50)
if "match_details" in data:
    # Get first match detail
    for match_id, detail_data in data["match_details"].items():
        if "results" in detail_data and detail_data["results"]:
            fields = extract_fields(detail_data["results"][0])
            for field in sorted(fields):
                print(f"  {field}")
        break
print()

# 3. ODDS ENDPOINT (/odds/history)
print("3. ODDS ENDPOINT (/odds/history)")
print("-" * 50)
if "match_odds" in data:
    for match_id, odds_data in data["match_odds"].items():
        if "results" in odds_data:
            results = odds_data["results"]
            if isinstance(results, list) and results:
                # It's an array, process first item
                fields = extract_fields(results[0])
            elif isinstance(results, dict):
                # It's a dict, process it directly
                fields = extract_fields(results)
            else:
                continue
                
            for field in sorted(fields):
                print(f"  {field}")
            break
print()

# 4. TEAM ENDPOINT (/team/additional/list)
print("4. TEAM ENDPOINT (/team/additional/list)")
print("-" * 50)
if "team_info" in data:
    for team_id, team_data in data["team_info"].items():
        if "results" in team_data and team_data["results"]:
            fields = extract_fields(team_data["results"][0])
            for field in sorted(fields):
                print(f"  {field}")
        break
print()

# 5. COMPETITION ENDPOINT (/competition/additional/list)
print("5. COMPETITION ENDPOINT (/competition/additional/list)")
print("-" * 50)
if "competition_info" in data:
    for comp_id, comp_data in data["competition_info"].items():
        if "results" in comp_data and comp_data["results"]:
            fields = extract_fields(comp_data["results"][0])
            for field in sorted(fields):
                print(f"  {field}")
        break
print()

# 6. COUNTRY ENDPOINT (/country/list) - if present
print("6. COUNTRY ENDPOINT (/country/list)")
print("-" * 50)
if "country_info" in data:
    if isinstance(data["country_info"], dict):
        for country_id, country_data in data["country_info"].items():
            if isinstance(country_data, dict):
                fields = extract_fields(country_data)
                for field in sorted(fields):
                    print(f"  {field}")
            break
    elif isinstance(data["country_info"], list) and data["country_info"]:
        fields = extract_fields(data["country_info"][0])
        for field in sorted(fields):
            print(f"  {field}")
else:
    print("  (No country data found)")
