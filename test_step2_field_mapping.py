#!/usr/bin/env python3
"""
Test script to verify Step2.py field mappings and data paths
"""

import json
import os
import sys

def test_field_mappings():
    """Test the field mappings in step2.py"""
    
    print("=== STEP2 FIELD MAPPING TEST ===\n")
    
    # Check if step1.json exists
    if not os.path.exists("step1.json"):
        print("ERROR: step1.json not found")
        return
    
    # Load step1 data
    with open("step1.json", "r") as f:
        step1_data = json.load(f)
    
    print("1. STEP1 DATA STRUCTURE:")
    print(f"   - live_matches: {type(step1_data.get('live_matches'))}")
    print(f"   - match_details: {type(step1_data.get('match_details'))}")
    print(f"   - match_odds: {type(step1_data.get('match_odds'))}")
    print(f"   - team_info: {type(step1_data.get('team_info'))}")
    print(f"   - competition_info: {type(step1_data.get('competition_info'))}")
    print(f"   - countries: {type(step1_data.get('countries'))}")
    
    print("\n2. SAMPLE MATCH STRUCTURE:")
    if step1_data.get("live_matches", {}).get("results"):
        match = step1_data["live_matches"]["results"][0]
        print(f"   Match keys: {sorted(match.keys())}")
        
        # Check nested structures
        if "home" in match:
            print(f"   Home team keys: {sorted(match['home'].keys())}")
        if "away" in match:
            print(f"   Away team keys: {sorted(match['away'].keys())}")
        if "league" in match:
            print(f"   League keys: {sorted(match['league'].keys())}")
    
    print("\n3. SAMPLE ODDS STRUCTURE:")
    # Find a match with odds
    for match_id, odds_data in step1_data.get("match_odds", {}).items():
        if odds_data.get("results"):
            print(f"   Match ID: {match_id}")
            for company_id, company_odds in odds_data["results"].items():
                print(f"   Company {company_id} odds keys: {sorted(company_odds.keys())}")
                # Check if arrays have data
                for odds_type in ["eu", "asia", "bs", "cr"]:
                    if company_odds.get(odds_type):
                        print(f"     - {odds_type}: {len(company_odds[odds_type])} entries")
                break
            break
    
    print("\n4. TEAM INFO STRUCTURE:")
    team_ids = list(step1_data.get("team_info", {}).keys())[:2]
    for team_id in team_ids:
        team_data = step1_data["team_info"][team_id]
        if team_data.get("results"):
            team = team_data["results"][0]
            print(f"   Team {team_id} keys: {sorted(team.keys())}")
            break
    
    print("\n5. COMPETITION INFO STRUCTURE:")
    comp_ids = list(step1_data.get("competition_info", {}).keys())[:2]
    for comp_id in comp_ids:
        comp_data = step1_data["competition_info"][comp_id]
        if comp_data.get("results"):
            comp = comp_data["results"][0]
            print(f"   Competition {comp_id} keys: {sorted(comp.keys())}")
            break
    
    print("\n6. COUNTRY STRUCTURE:")
    countries = step1_data.get("countries", {}).get("results", [])
    if countries:
        # Countries are stored in a dict with numeric keys
        country_keys = sorted(countries.keys()) if isinstance(countries, dict) else []
        print(f"   Countries type: {type(countries)}")
        if country_keys:
            sample_country = countries[country_keys[0]]
            print(f"   Sample country keys: {sorted(sample_country.keys())}")
    
    # Now check step2.json
    if os.path.exists("step2.json"):
        print("\n7. STEP2 OUTPUT VERIFICATION:")
        with open("step2.json", "r") as f:
            step2_data = json.load(f)
        
        if step2_data.get("summaries"):
            summary = step2_data["summaries"][0]
            print(f"   Summary keys: {sorted(summary.keys())}")
            
            # Check if renamed odds fields are present
            print("\n   Renamed odds fields:")
            for field in ["money_line", "spread", "over_under", "corners"]:
                if field in summary:
                    print(f"   ✓ {field}: {type(summary[field])}")
                else:
                    print(f"   ✗ {field}: NOT FOUND")
            
            # Check odds company fields
            print("\n   Company fields:")
            for field in ["odds_company_id", "odds_company_name"]:
                if field in summary:
                    print(f"   ✓ {field}: {summary[field]}")
                else:
                    print(f"   ✗ {field}: NOT FOUND")
            
            # Check original odds structure
            if "odds" in summary:
                print(f"\n   Original odds structure: {type(summary['odds'])}")
                for company_id, odds in summary["odds"].items():
                    print(f"   Company {company_id} has odds fields: {sorted(odds.keys())}")
                    break

if __name__ == "__main__":
    test_field_mappings()
