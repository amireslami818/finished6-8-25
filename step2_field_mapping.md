# Step2.py Field Mapping and Data Flow Analysis

## 1. DATA SOURCES AND STRUCTURES

### Input Data (from step1.json):
```
step1_data = {
    "live_matches": {
        "results": [
            {
                "id": "match_id",
                "status_id": 2,
                "score": {},
                "incidents": {},
                "stats": {},
                "tlive": {}
            }
        ]
    },
    "match_details": {
        "<match_id>": {
            "results": [...]  # Match detail data with environment, venue etc
        }
    },
    "match_odds": {
        "<match_id>": {
            "results": {
                "<company_id>": {
                    "asia": [],  # Asian Handicap
                    "bs": [],    # Ball Size (Over/Under)
                    "eu": [],    # European (Money Line)
                    "cr": []     # Corners
                }
            }
        }
    },
    "team_info": {
        "<team_id>": {
            "results": [{
                "id": "team_id",
                "name": "Team Name",
                "logo": "url",
                "country_id": "id",
                "market_value": "value"
                // ... other team fields
            }]
        }
    },
    "competition_info": {
        "<competition_id>": {
            "results": [{
                "id": "comp_id",
                "name": "Competition Name",
                "country_id": "id",
                "logo": "url",
                "type": "type"
                // ... other competition fields
            }]
        }
    },
    "countries": {
        "results": []  # List of country objects
    }
}
```

## 2. EXTRACTION FUNCTIONS

### `extract_summary_fields(match)` → dict
**Input:** Merged match object
**Output:** Summary fields
```python
{
    "match_id": str,
    "home": str (team name),
    "away": str (team name),
    "home_id": str,
    "away_id": str,
    "score": str ("home-away"),
    "status_id": int,
    "competition": str (league name),
    "competition_id": str,
    "country": str,
    "match_time": int/str,
    "kickoff": str,
    "venue": str,
    "home_position": str,
    "away_position": str
}
```

### `extract_odds(match)` → dict
**Input:** Match object with odds
**Output:** Odds by company with renamed fields
```python
{
    "<company_id>": {
        "money_line": [],  # Renamed from "eu"
        "spread": [],      # Renamed from "asia"
        "over_under": [],  # Renamed from "bs"
        "corners": []      # Renamed from "cr"
    }
}
```

### `extract_environment(match)` → dict
**Input:** Match object
**Output:** Environment data
```python
{
    "weather": str,
    "temperature": str,
    "humidity": str,
    "wind_speed": str,
    "pressure": str
}
```

### `extract_events(match)` → list
**Input:** Match object
**Output:** List of match events

## 3. PROCESSING FUNCTIONS

### `filter_odds_by_minutes(odds_data)` → dict
**Input:** Odds data with renamed fields
**Output:** Filtered odds (minutes 2-6 only)
```python
{
    "money_line": [...],  # Filtered arrays
    "spread": [...],
    "over_under": [...],
    "corners": [...]
}
```

### `merge_and_summarize()` → list
**Main processing function that:**
1. Iterates through live matches
2. Enriches with team/competition data
3. Extracts and filters odds
4. Creates match summaries

## 4. OUTPUT STRUCTURE (step2.json)

```json
{
    "summaries": [
        {
            // PRIORITIZED NEW FIELDS (come first)
            "money_line": [],      // Renamed from "eu"
            "spread": [],          // Renamed from "asia"
            "over_under": [],      // Renamed from "bs"
            "corners": [],         // Renamed from "cr"
            "odds_company_id": "2",
            "odds_company_name": "BET365",
            
            // ORIGINAL STRUCTURE (after new fields)
            "odds": {
                "<company_id>": {
                    "money_line": [],
                    "spread": [],
                    "over_under": [],
                    "corners": []
                }
            },
            
            // MATCH DETAILS
            "match_id": "...",
            "home": "Team Name",
            "away": "Team Name",
            "home_id": "...",
            "away_id": "...",
            "score": "0-0",
            "status_id": 2,
            "competition": "League Name",
            "competition_id": "...",
            "country": "Country Name",
            "match_time": 1749394800,
            "kickoff": "",
            "venue": "",
            "home_position": "",
            "away_position": "",
            "status": 2,
            
            // ADDITIONAL DATA
            "environment": {
                "weather": "",
                "temperature": "",
                "humidity": "",
                "wind_speed": "",
                "pressure": ""
            },
            "events": []
        }
    ],
    "metadata": {
        "total_matches_processed": 104,
        "processing_time": 0.23,
        "timestamp": "2025-06-08T16:45:05.319086-04:00"
    },
    "step2_processing_summary": {
        "source": "step1.json",
        "input_file": "/root/6-4-2025/step1.json",
        "output_file": "/root/6-4-2025/step2.json",
        "processed_at": "2025-06-08T16:45:05.319148-04:00",
        "pipeline_timing": {
            "total_matches": 104
        }
    }
}
```

## 5. FIELD NAME MAPPINGS

### Odds Field Renaming (API → Our Names):
- `"eu"` → `"money_line"` (European/Money Line odds)
- `"asia"` → `"spread"` (Asian Handicap/Spread betting)
- `"bs"` → `"over_under"` (Ball Size/Over-Under total goals)
- `"cr"` → `"corners"` (Corner kick totals)

### Data Flow:
1. **Step1** fetches from API with original field names
2. **extract_odds()** maps API names to descriptive names
3. **filter_odds_by_minutes()** filters using new names
4. **merge_and_summarize()** outputs both new fields (prioritized) and original structure

## 6. KEY PATHS AND LOOKUPS

### Match Processing:
```python
match.get("id")                              # Match ID
match.get("home", {}).get("name")            # Home team name
match.get("away", {}).get("name")            # Away team name
match.get("league", {}).get("name")          # Competition name
match.get("league", {}).get("country_name")  # Country name
```

### Team Enrichment:
```python
team_info[team_id]["results"][0]["name"]     # Team name from API
team_info[team_id]["results"][0]["logo"]     # Team logo
team_info[team_id]["results"][0]["country"]  # Team country
```

### Competition Enrichment:
```python
competition_info[comp_id]["results"][0]["name"]        # Competition name
competition_info[comp_id]["results"][0]["country_id"]  # Country ID
```

### Countries Lookup:
```python
countries[country_id]["name"]                # Country name by ID
```

## 7. VALIDATION CHECKLIST

✅ **Field Renaming Working:**
- extract_odds() correctly maps eu→money_line, asia→spread, etc.
- filter_odds_by_minutes() uses new field names
- Output JSON shows new fields first, then original structure

✅ **Data Flow Correct:**
- Step1 data loaded properly
- Enrichment data merged correctly
- Odds filtered to minutes 2-6
- Single betting company selected (BET365 preferred)

✅ **Output Structure:**
- New descriptive fields appear FIRST in JSON
- Original "odds" structure maintained for compatibility
- All match details preserved
- Metadata and processing info included
