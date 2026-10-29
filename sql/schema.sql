-- Phase 4 design DDL: SQLite dialect. Run on an empty database.
-- Each application connection must enable foreign_keys before transactions.
PRAGMA foreign_keys = ON;
BEGIN;

CREATE TABLE sources (
    source_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL CHECK (kind IN ('api', 'manual', 'sample'))
);
CREATE TABLE import_batches (
    batch_id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(source_id) ON DELETE RESTRICT,
    capability TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    upstream_updated_at TEXT,
    completeness TEXT NOT NULL CHECK (completeness IN ('partial', 'complete', 'unknown')),
    status TEXT NOT NULL CHECK (status IN ('pending', 'committed', 'failed')),
    error_code TEXT
);
CREATE TABLE countries (
    country_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    code TEXT UNIQUE
);
CREATE TABLE formats (
    format_id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    family TEXT NOT NULL CHECK (family IN ('TEST', 'ODI', 'T20', 'OTHER')),
    level TEXT NOT NULL CHECK (level IN ('international', 'domestic', 'other'))
);
CREATE TABLE playing_roles (
    role_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE teams (
    team_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    country_id INTEGER REFERENCES countries(country_id) ON DELETE RESTRICT,
    is_international INTEGER NOT NULL CHECK (is_international IN (0,1)),
    source_id INTEGER REFERENCES sources(source_id) ON DELETE RESTRICT,
    external_id TEXT,
    UNIQUE (source_id, external_id),
    CHECK ((source_id IS NULL) = (external_id IS NULL))
);
CREATE TABLE players (
    player_id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL CHECK (length(trim(full_name)) > 0),
    role_id INTEGER REFERENCES playing_roles(role_id) ON DELETE RESTRICT,
    batting_style TEXT,
    bowling_style TEXT,
    source_id INTEGER REFERENCES sources(source_id) ON DELETE RESTRICT,
    external_id TEXT,
    last_batch_id INTEGER REFERENCES import_batches(batch_id) ON DELETE RESTRICT,
    ownership TEXT NOT NULL DEFAULT 'manual' CHECK (ownership IN ('api','manual','override')),
    is_deleted INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0,1)),
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    updated_at TEXT NOT NULL,
    UNIQUE (source_id, external_id),
    CHECK ((source_id IS NULL) = (external_id IS NULL)),
    CHECK (ownership = 'manual' OR source_id IS NOT NULL)
);
CREATE TABLE player_team_memberships (
    membership_id INTEGER PRIMARY KEY,
    player_id INTEGER NOT NULL REFERENCES players(player_id) ON DELETE RESTRICT,
    team_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE RESTRICT,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    UNIQUE (player_id, team_id, valid_from),
    CHECK (valid_to IS NULL OR valid_to >= valid_from)
);
CREATE TABLE venues (
    venue_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT,
    country_id INTEGER REFERENCES countries(country_id) ON DELETE RESTRICT,
    capacity INTEGER CHECK (capacity >= 0),
    source_id INTEGER REFERENCES sources(source_id) ON DELETE RESTRICT,
    external_id TEXT,
    UNIQUE (source_id, external_id),
    CHECK ((source_id IS NULL) = (external_id IS NULL))
);
CREATE TABLE series (
    series_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    planned_matches INTEGER CHECK (planned_matches >= 0),
    source_id INTEGER REFERENCES sources(source_id) ON DELETE RESTRICT,
    external_id TEXT,
    UNIQUE (source_id, external_id),
    CHECK ((source_id IS NULL) = (external_id IS NULL)),
    CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);
CREATE TABLE series_hosts (
    series_id INTEGER NOT NULL REFERENCES series(series_id) ON DELETE RESTRICT,
    country_id INTEGER NOT NULL REFERENCES countries(country_id) ON DELETE RESTRICT,
    PRIMARY KEY (series_id, country_id)
);
CREATE TABLE series_formats (
    series_id INTEGER NOT NULL REFERENCES series(series_id) ON DELETE RESTRICT,
    format_id INTEGER NOT NULL REFERENCES formats(format_id) ON DELETE RESTRICT,
    PRIMARY KEY (series_id, format_id)
);
CREATE TABLE matches (
    match_id INTEGER PRIMARY KEY,
    description TEXT NOT NULL,
    series_id INTEGER REFERENCES series(series_id) ON DELETE RESTRICT,
    format_id INTEGER NOT NULL REFERENCES formats(format_id) ON DELETE RESTRICT,
    venue_id INTEGER REFERENCES venues(venue_id) ON DELETE RESTRICT,
    starts_at TEXT,
    completed_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('scheduled','live','completed','abandoned','unknown')),
    status_text TEXT,
    toss_winner_id INTEGER,
    toss_decision TEXT CHECK (toss_decision IN ('bat','bowl')),
    winner_team_id INTEGER,
    result_type TEXT NOT NULL DEFAULT 'pending' CHECK (result_type IN ('pending','win','tie','draw','no_result')),
    margin_value INTEGER CHECK (margin_value > 0),
    margin_unit TEXT CHECK (margin_unit IN ('runs','wickets')),
    source_id INTEGER REFERENCES sources(source_id) ON DELETE RESTRICT,
    external_id TEXT,
    last_batch_id INTEGER REFERENCES import_batches(batch_id) ON DELETE RESTRICT,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    UNIQUE (source_id, external_id),
    CHECK ((source_id IS NULL) = (external_id IS NULL)),
    CHECK ((result_type = 'win' AND winner_team_id IS NOT NULL)
        OR (result_type <> 'win' AND winner_team_id IS NULL)),
    CHECK ((margin_value IS NULL) = (margin_unit IS NULL)),
    CHECK (margin_value IS NULL OR result_type = 'win'),
    FOREIGN KEY (match_id, toss_winner_id) REFERENCES match_teams(match_id, team_id) ON DELETE RESTRICT,
    FOREIGN KEY (match_id, winner_team_id) REFERENCES match_teams(match_id, team_id) ON DELETE RESTRICT
);
CREATE TABLE match_teams (
    match_id INTEGER NOT NULL REFERENCES matches(match_id) ON DELETE RESTRICT,
    team_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE RESTRICT,
    slot INTEGER NOT NULL CHECK (slot IN (1,2)),
    PRIMARY KEY (match_id, team_id),
    UNIQUE (match_id, slot)
);
CREATE TABLE match_players (
    match_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL REFERENCES players(player_id) ON DELETE RESTRICT,
    team_id INTEGER NOT NULL,
    participation TEXT NOT NULL CHECK (participation IN ('confirmed_xi','observed','substitute')),
    PRIMARY KEY (match_id, player_id),
    UNIQUE (match_id, player_id, team_id),
    FOREIGN KEY (match_id, team_id) REFERENCES match_teams(match_id, team_id) ON DELETE RESTRICT
);
CREATE TABLE innings (
    innings_id INTEGER PRIMARY KEY,
    match_id INTEGER NOT NULL REFERENCES matches(match_id) ON DELETE RESTRICT,
    innings_number INTEGER NOT NULL CHECK (innings_number > 0),
    batting_team_id INTEGER NOT NULL,
    bowling_team_id INTEGER NOT NULL,
    is_super_over INTEGER NOT NULL DEFAULT 0 CHECK (is_super_over IN (0,1)),
    total_runs INTEGER CHECK (total_runs >= 0),
    wickets INTEGER CHECK (wickets BETWEEN 0 AND 10),
    legal_balls INTEGER CHECK (legal_balls >= 0),
    last_batch_id INTEGER REFERENCES import_batches(batch_id) ON DELETE RESTRICT,
    UNIQUE (match_id, innings_number),
    UNIQUE (innings_id, match_id, batting_team_id),
    UNIQUE (innings_id, match_id, bowling_team_id),
    CHECK (batting_team_id <> bowling_team_id),
    FOREIGN KEY (match_id, batting_team_id) REFERENCES match_teams(match_id, team_id) ON DELETE RESTRICT,
    FOREIGN KEY (match_id, bowling_team_id) REFERENCES match_teams(match_id, team_id) ON DELETE RESTRICT
);
CREATE TABLE batting_performances (
    innings_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    match_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    batting_position INTEGER CHECK (batting_position BETWEEN 1 AND 11),
    runs INTEGER CHECK (runs >= 0),
    balls_faced INTEGER CHECK (balls_faced >= 0),
    fours INTEGER CHECK (fours >= 0),
    sixes INTEGER CHECK (sixes >= 0),
    is_dismissed INTEGER CHECK (is_dismissed IN (0,1)),
    dismissal_text TEXT,
    ownership TEXT NOT NULL DEFAULT 'manual' CHECK (ownership IN ('api','manual','override')),
    is_deleted INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0,1)),
    last_batch_id INTEGER REFERENCES import_batches(batch_id) ON DELETE RESTRICT,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    PRIMARY KEY (innings_id, player_id),
    UNIQUE (innings_id, batting_position),
    FOREIGN KEY (innings_id, match_id, team_id) REFERENCES innings(innings_id, match_id, batting_team_id) ON DELETE RESTRICT,
    FOREIGN KEY (match_id, player_id, team_id) REFERENCES match_players(match_id, player_id, team_id) ON DELETE RESTRICT,
    CHECK (ownership <> 'api' OR last_batch_id IS NOT NULL)
);
CREATE TABLE bowling_performances (
    innings_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    match_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    legal_balls INTEGER CHECK (legal_balls >= 0),
    runs_conceded INTEGER CHECK (runs_conceded >= 0),
    wickets INTEGER CHECK (wickets BETWEEN 0 AND 10),
    maidens INTEGER CHECK (maidens >= 0),
    ownership TEXT NOT NULL DEFAULT 'manual' CHECK (ownership IN ('api','manual','override')),
    is_deleted INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0,1)),
    last_batch_id INTEGER REFERENCES import_batches(batch_id) ON DELETE RESTRICT,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    PRIMARY KEY (innings_id, player_id),
    FOREIGN KEY (innings_id, match_id, team_id) REFERENCES innings(innings_id, match_id, bowling_team_id) ON DELETE RESTRICT,
    FOREIGN KEY (match_id, player_id, team_id) REFERENCES match_players(match_id, player_id, team_id) ON DELETE RESTRICT,
    CHECK (ownership <> 'api' OR last_batch_id IS NOT NULL)
);
CREATE TABLE fielding_performances (
    innings_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    match_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    catches INTEGER CHECK (catches >= 0),
    stumpings INTEGER CHECK (stumpings >= 0),
    ownership TEXT NOT NULL DEFAULT 'manual' CHECK (ownership IN ('api','manual','override')),
    is_deleted INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0,1)),
    last_batch_id INTEGER REFERENCES import_batches(batch_id) ON DELETE RESTRICT,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    PRIMARY KEY (innings_id, player_id),
    FOREIGN KEY (innings_id, match_id, team_id) REFERENCES innings(innings_id, match_id, bowling_team_id) ON DELETE RESTRICT,
    FOREIGN KEY (match_id, player_id, team_id) REFERENCES match_players(match_id, player_id, team_id) ON DELETE RESTRICT,
    CHECK (ownership <> 'api' OR last_batch_id IS NOT NULL)
);
CREATE TABLE career_stats_snapshots (
    snapshot_id INTEGER PRIMARY KEY,
    player_id INTEGER NOT NULL REFERENCES players(player_id) ON DELETE RESTRICT,
    format_id INTEGER NOT NULL REFERENCES formats(format_id) ON DELETE RESTRICT,
    batch_id INTEGER NOT NULL REFERENCES import_batches(batch_id) ON DELETE RESTRICT,
    scope TEXT NOT NULL DEFAULT 'career' CHECK (scope = 'career'),
    matches_played INTEGER CHECK (matches_played >= 0),
    batting_innings INTEGER CHECK (batting_innings >= 0),
    runs INTEGER CHECK (runs >= 0),
    dismissals INTEGER CHECK (dismissals >= 0),
    balls_faced INTEGER CHECK (balls_faced >= 0),
    centuries INTEGER CHECK (centuries >= 0),
    highest_score INTEGER CHECK (highest_score >= 0),
    bowling_innings INTEGER CHECK (bowling_innings >= 0),
    legal_balls_bowled INTEGER CHECK (legal_balls_bowled >= 0),
    runs_conceded INTEGER CHECK (runs_conceded >= 0),
    wickets INTEGER CHECK (wickets >= 0),
    catches INTEGER CHECK (catches >= 0),
    stumpings INTEGER CHECK (stumpings >= 0),
    reported_batting_average REAL CHECK (reported_batting_average >= 0),
    reported_strike_rate REAL CHECK (reported_strike_rate >= 0),
    reported_bowling_average REAL CHECK (reported_bowling_average >= 0),
    reported_economy REAL CHECK (reported_economy >= 0),
    UNIQUE (player_id, format_id, batch_id),
    CHECK (dismissals IS NULL OR batting_innings IS NULL OR dismissals <= batting_innings)
);
CREATE TABLE dataset_state (
    singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
    mode TEXT NOT NULL CHECK (mode IN ('live','sample')),
    revision INTEGER NOT NULL DEFAULT 0 CHECK (revision >= 0)
);

CREATE INDEX idx_batches_source_time ON import_batches(source_id, fetched_at);
CREATE INDEX idx_players_role ON players(role_id);
CREATE INDEX idx_memberships_team_dates ON player_team_memberships(team_id, valid_from, valid_to);
CREATE INDEX idx_memberships_player_dates ON player_team_memberships(player_id, valid_from, valid_to);
CREATE INDEX idx_venues_country ON venues(country_id);
CREATE INDEX idx_series_start ON series(start_date);
CREATE INDEX idx_matches_start ON matches(starts_at);
CREATE INDEX idx_matches_status_date ON matches(status, completed_at);
CREATE INDEX idx_matches_format_date ON matches(format_id, starts_at);
CREATE INDEX idx_matches_venue ON matches(venue_id);
CREATE INDEX idx_matches_series ON matches(series_id);
CREATE INDEX idx_matches_winner ON matches(winner_team_id);
CREATE INDEX idx_matchteams_team ON match_teams(team_id, match_id);
CREATE INDEX idx_matchplayers_player ON match_players(player_id, match_id);
CREATE INDEX idx_batting_player_match ON batting_performances(player_id, match_id);
CREATE INDEX idx_bowling_player_match ON bowling_performances(player_id, match_id);
CREATE INDEX idx_fielding_player_match ON fielding_performances(player_id, match_id);
CREATE INDEX idx_career_format_player ON career_stats_snapshots(format_id, player_id, batch_id);
COMMIT;
