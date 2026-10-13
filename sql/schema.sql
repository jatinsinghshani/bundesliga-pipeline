-- dimension table: one row per team
CREATE TABLE IF NOT EXISTS teams (
    team_id     INTEGER PRIMARY KEY,  -- unique team id
    team_name   VARCHAR NOT NULL,     -- full name
    short_name  VARCHAR,              -- short name
    icon_url    VARCHAR               -- logo link
);

-- fact table: one row per match
CREATE TABLE IF NOT EXISTS matches (
    match_id      INTEGER PRIMARY KEY,  -- unique match id
    season        INTEGER NOT NULL,     -- season start year
    matchday      INTEGER,              -- round number
    kickoff_utc   TIMESTAMP,            -- start time
    home_team_id  INTEGER NOT NULL,     -- links to teams.team_id
    away_team_id  INTEGER NOT NULL,     -- links to teams.team_id
    is_finished   BOOLEAN NOT NULL,     -- played or not
    home_goals    INTEGER,              -- empty until finished
    away_goals    INTEGER,
    loaded_at     TIMESTAMP DEFAULT current_timestamp  -- when we loaded this row
);

-- fact table: one row per goal
CREATE TABLE IF NOT EXISTS goals (
    goal_id          INTEGER PRIMARY KEY,  -- unique goal id
    match_id         INTEGER NOT NULL,     -- links to matches.match_id
    minute           INTEGER,
    scorer_id        INTEGER,
    scorer_name      VARCHAR,
    scoring_team_id  INTEGER,              -- worked out from the running score
    is_penalty       BOOLEAN,
    is_own_goal      BOOLEAN,
    is_overtime      BOOLEAN,
    score_home       INTEGER,              -- score after this goal
    score_away       INTEGER
);
