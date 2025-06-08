# STEP1.JSON Data Structure

## Top-Level Dictionaries Created by Step1

### 1. **live_matches**
Direct API response from `/match/detail_live` endpoint
```json
{
  "code": 0,
  "results": [
    {
      "id": "match_id",
      "status_id": 2,
      "score": [current_score, status_id, ...],
      "tlive": "45+2",
      "incidents": {...},
      "stats": {...}
    }
  ]
}
```

**Fields in each match:**
- `id` - Match UUID
- `status_id` - Match status (2=First half, 3=Half-time, etc.)
- `score` - Array with current score and other info
- `tlive` - Live time string
- `incidents` - Match events
- `stats` - Match statistics

### 2. **match_details** 
Dictionary keyed by match_id, each containing API response from `/match/recent/list`
```json
{
  "match_id": {
    "code": 0,
    "results": [
      {
        "id": "match_id",
        "home_team_id": "team_uuid",
        "away_team_id": "team_uuid",
        "competition_id": "comp_uuid",
        "status_id": 2,
        "match_time": 1749385800,
        "home_scores": [1, 1, 0, ...],
        "away_scores": [0, 0, 0, ...],
        // ... more fields
      }
    ]
  }
}
```

**Fields in match details:**
- `id` - Match UUID
- `season_id` - Season identifier
- `competition_id` - Competition UUID
- `home_team_id` - Home team UUID
- `away_team_id` - Away team UUID
- `status_id` - Match status
- `match_time` - Unix timestamp
- `venue_id` - Venue identifier
- `referee_id` - Referee identifier
- `neutral` - Neutral venue flag
- `note` - Match notes
- `home_scores` - Array of home scores by period
- `away_scores` - Array of away scores by period
- `home_position` - League position
- `away_position` - League position
- `coverage` - Coverage info
- `round` - Round/matchday
- `updated_at` - Last update timestamp

### 3. **match_odds**
Dictionary keyed by match_id, each containing API response from `/odds/history`
```json
{
  "match_id": {
    "code": 0,
    "results": {
      "2": { // Company ID
        "asia": [...],  // Spread betting odds
        "bs": [...],    // Over/Under odds
        "eu": [...]     // Moneyline odds
      },
      "4": { ... },
      "5": { ... }
    }
  }
}
```

**Structure:**
- Results contains company IDs (2, 4, 5, 9, 10, 13, 15, 16, 17, 22)
- Each company has:
  - `asia` - Asian handicap (spread) odds array
  - `bs` - Ball size (over/under) odds array  
  - `eu` - European (moneyline) odds array

**Each odds entry is an array:**
`[timestamp, event, home_odds, draw_odds, away_odds, status, ?, score]`

### 4. **team_info**
Dictionary keyed by team_id, each containing API response from `/team/additional/list`
```json
{
  "team_id": {
    "code": 0,
    "results": [
      {
        "id": "team_uuid",
        "competition_id": "comp_uuid",
        "name": "Team Name",
        "short_name": "SHORT",
        "logo": "url",
        // ... more fields
      }
    ]
  }
}
```

**Fields in team info:**
- `id` - Team UUID
- `competition_id` - Primary competition
- `name` - Full team name
- `short_name` - Abbreviated name
- `logo` - Logo URL
- `national` - National team flag
- Additional team metadata

### 5. **competition_info**
Dictionary keyed by competition_id, each containing API response from `/competition/additional/list`
```json
{
  "competition_id": {
    "code": 0,
    "results": [
      {
        "id": "comp_uuid",
        "country_id": "country_id",
        "name": "Competition Name",
        "short_name": "SHORT",
        // ... more fields
      }
    ]
  }
}
```

**Fields in competition info:**
- `id` - Competition UUID
- `country_id` - Country identifier
- `name` - Full competition name
- `short_name` - Abbreviated name
- Competition metadata

### 6. **countries**
Direct API response from `/country/list` (not keyed by ID)
```json
{
  "code": 0,
  "results": [
    {
      "id": "country_id",
      "name": "Country Name",
      // ... more fields
    }
  ]
}
```

**Fields in country info:**
- `id` - Country identifier
- `name` - Country name
- Country metadata

### 7. **Other Metadata Dictionaries**

- **timestamp** - ISO timestamp of when data was fetched
- **ny_timestamp** - New York timezone timestamp
- **unified_status_summary** - Summary of match counts by status
- **detailed_status_mapping** - Detailed breakdown by status with match IDs
- **comprehensive_match_breakdown** - Formatted match info by status
- **step1_completion_summary** - Execution metadata and timing
