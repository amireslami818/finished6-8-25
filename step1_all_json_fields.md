# Complete List of JSON Fields Fetched by Step1

## 1. LIVE MATCHES Fields
From `/match/detail_live` endpoint:
- `id` - Match UUID
- `status_id` - Current match status
- `score` - Array with score data
- `tlive` - Live time string (e.g., "45+2")
- `incidents` - Array of match events
  - `incidents[].type` - Event type
  - `incidents[].time` - Event time
  - `incidents[].position` - Position/player
  - `incidents[].home_score` - Home score after event
  - `incidents[].away_score` - Away score after event
- `stats` - Array of match statistics
  - `stats[].type` - Stat type
  - `stats[].home` - Home team value
  - `stats[].away` - Away team value

## 2. MATCH DETAILS Fields
From `/match/recent/list` endpoint:
- `id` - Match UUID
- `season_id` - Season identifier
- `competition_id` - Competition UUID
- `home_team_id` - Home team UUID
- `away_team_id` - Away team UUID
- `status_id` - Match status
- `match_time` - Unix timestamp of kickoff
- `venue_id` - Venue identifier
- `referee_id` - Referee identifier
- `neutral` - Neutral venue flag (0/1)
- `note` - Match notes
- `home_scores` - Array of home scores by period
- `away_scores` - Array of away scores by period
- `home_position` - Home team league position
- `away_position` - Away team league position
- `coverage` - Coverage information object
  - `coverage.mlive` - Match live coverage
  - `coverage.lineup` - Lineup availability
- `round` - Round information object
  - `round.round_num` - Round number
  - `round.stage_id` - Stage identifier
  - `round.group_num` - Group number
- `updated_at` - Last update timestamp

## 3. MATCH ODDS Fields
From `/odds/history` endpoint:
- Keyed by Company IDs: 2, 9, 17 (varies by match)
- Each company contains three odds types:
  - `asia` - Asian Handicap (Spread) betting
  - `bs` - Ball Size (Over/Under) betting
  - `eu` - European (Moneyline) betting
- Each odds entry is an array: `[timestamp, event, home_odds, draw_odds, away_odds, status, unknown, score]`

## 4. TEAM INFO Fields
From `/team/additional/list` endpoint:
- `id` - Team UUID
- `competition_id` - Primary competition
- `name` - Full team name
- `short_name` - Abbreviated name
- `logo` - Team logo URL
- `country_id` - Country identifier
- `country_logo` - Country flag URL
- `national` - National team flag (0/1)
- `virtual` - Virtual team flag (0/1)
- `gender` - Team gender
- `venue_id` - Home venue ID
- `coach_id` - Head coach ID
- `website` - Team website
- `foundation_time` - Year founded
- `total_players` - Total squad size
- `foreign_players` - Number of foreign players
- `national_players` - Number of national team players
- `market_value` - Team market value
- `market_value_currency` - Currency for market value
- `updated_at` - Last update timestamp

## 5. COMPETITION INFO Fields
From `/competition/additional/list` endpoint:
- `id` - Competition UUID
- `category_id` - Category identifier
- `country_id` - Country identifier
- `name` - Full competition name
- `short_name` - Abbreviated name
- `logo` - Competition logo URL
- `type` - Competition type
- `cur_season_id` - Current season ID
- `cur_stage_id` - Current stage ID
- `cur_round` - Current round
- `round_count` - Total rounds
- `divisions` - Number of divisions
- `host` - Host country/organization
- `primary_color` - Primary brand color
- `secondary_color` - Secondary brand color
- `title_holder` - Current champion
- `most_titles` - Record holder
- `newcomers` - Newly promoted teams
- `updated_at` - Last update timestamp

## 6. COUNTRIES Fields
From `/country/list` endpoint:
- `id` - Country identifier
- `category_id` - Category identifier
- `name` - Country name
- `logo` - Country flag/logo URL
- `updated_at` - Last update timestamp

## Additional Metadata Fields
Step1 also creates these metadata fields:
- `timestamp` - ISO timestamp of data fetch
- `ny_timestamp` - New York timezone timestamp
- `unified_status_summary` - Match count summaries
- `detailed_status_mapping` - Status breakdown with match IDs
- `comprehensive_match_breakdown` - Formatted match details by status
- `step1_completion_summary` - Execution metadata
