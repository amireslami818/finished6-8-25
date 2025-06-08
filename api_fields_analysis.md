# TheSports API Endpoints - JSON Field Analysis

## 1. LIVE MATCHES ENDPOINT (`/match/detail_live`)
**Fields:**
- `id` - Match ID
- `status_id` - Match status (2=First half, 3=Half-time, etc.)
- `score` - Current scores
- `tlive` - Live timing data
- `stats` - Array of match statistics
  - `type` - Statistic type
  - `home` - Home team value
  - `away` - Away team value
- `incidents` - Array of match events
  - `type` - Event type
  - `time` - Event time
  - `player_id` - Player involved
  - `player_name` - Player name
  - `position` - Position on field
  - `home_score` - Score after event
  - `away_score` - Score after event

## 2. MATCH DETAILS ENDPOINT (`/match/recent/list`)
**Fields:**
- `id` - Match ID
- `home_team_id` - Home team ID
- `away_team_id` - Away team ID
- `competition_id` - Competition ID
- `season_id` - Season ID
- `venue_id` - Venue ID
- `referee_id` - Referee ID
- `match_time` - Match timestamp
- `status_id` - Match status
- `home_scores` - Home team score details
- `away_scores` - Away team score details
- `home_position` - Home team position
- `away_position` - Away team position
- `neutral` - Is neutral venue
- `note` - Match notes
- `updated_at` - Last update time
- `round` - Round information
  - `round_num` - Round number
  - `group_num` - Group number
  - `stage_id` - Stage ID
- `coverage` - Coverage details
  - `mlive` - Live coverage available
  - `lineup` - Lineup coverage available

## 3. ODDS ENDPOINT (`/odds/history`)
**Structure:** Organized by betting company ID
- Each company ID contains:
  - `asia` - Asian handicap odds / SPREAD betting (array of arrays)
  - `bs` - Ball Size / Over-Under (O/U) betting (array of arrays)
  - `eu` - European odds / MONEYLINE betting (array of arrays)

**Company IDs found:** 2, 4, 5, 9, 10, 13, 15, 16, 17, 22

## 4. TEAM ENDPOINT (`/team/additional/list`)
**Fields:**
- `id` - Team ID
- `name` - Full team name
- `short_name` - Abbreviated name
- `logo` - Team logo URL
- `country_id` - Country ID
- `country_logo` - Country flag URL
- `competition_id` - Primary competition
- `venue_id` - Home venue ID
- `coach_id` - Head coach ID
- `foundation_time` - Year founded
- `website` - Official website
- `gender` - Team gender (male/female)
- `national` - Is national team
- `virtual` - Is virtual team
- `total_players` - Total squad size
- `national_players` - Number of national players
- `foreign_players` - Number of foreign players
- `market_value` - Team market value
- `market_value_currency` - Currency code
- `updated_at` - Last update time

## 5. COMPETITION ENDPOINT (`/competition/additional/list`)
**Fields:**
- `id` - Competition ID
- `name` - Full competition name
- `short_name` - Abbreviated name
- `logo` - Competition logo URL
- `type` - Competition type
- `category_id` - Category ID
- `country_id` - Country ID
- `host` - Host information
- `cur_season_id` - Current season ID
- `cur_stage_id` - Current stage ID
- `cur_round` - Current round
- `round_count` - Total rounds
- `divisions` - Number of divisions
- `title_holder` - Current champion
- `most_titles` - Most successful team
- `newcomers` - Newly promoted teams
- `primary_color` - Primary brand color
- `secondary_color` - Secondary brand color
- `updated_at` - Last update time

## 6. COUNTRY ENDPOINT (`/country/list`)
**Note:** Not currently populated in the data

---

## Key Observations:
1. All endpoints return results wrapped in a `results` field
2. IDs are string format throughout
3. Timestamps use Unix timestamp format
4. Logo/image fields contain full URLs to TheSports CDN
5. The odds endpoint has a unique nested structure organized by betting company
