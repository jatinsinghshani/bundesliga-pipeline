import os  # to read the MotherDuck token from the environment
from pathlib import Path  # file paths

import duckdb  # the database engine

from src.quality import run_checks  # our data quality gate
from src.transform import load_latest_raw, build_teams, build_matches, build_goals  # our tables

SCHEMA_PATH = Path("sql/schema.sql")  # where the table definitions live
LOCAL_DB = Path("data/bundesliga.duckdb")  # local database file (used if no token)


def connect():
    """Use MotherDuck if a token is set, otherwise a local DuckDB file."""
    token = os.environ.get("MOTHERDUCK_TOKEN")  # None if you haven't set it
    if token:  # cloud mode
        os.environ["motherduck_token"] = token  # the driver looks for this name
        con = duckdb.connect("md:")  # connect to MotherDuck
        con.execute("CREATE DATABASE IF NOT EXISTS bundesliga")  # make sure our database exists
        con.execute("USE bundesliga")  # switch to it
        print("Connected to MotherDuck")  # tell us where we are
        return con  # ready
    LOCAL_DB.parent.mkdir(parents=True, exist_ok=True)  # make sure data/ exists
    print(f"No token set, using local file {LOCAL_DB}")  # tell us where we are
    return duckdb.connect(str(LOCAL_DB))  # local database


def create_schema(con):
    """Create the tables if they don't exist yet (safe to run every time)."""
    con.execute(SCHEMA_PATH.read_text())  # run everything in schema.sql


def get_finished_ids(con):
    """Match ids that are already stored AND finished. We never reload these."""
    rows = con.execute("SELECT match_id FROM matches WHERE is_finished").fetchall()  # list of tuples
    return {r[0] for r in rows}  # turn into a set for fast lookup


def filter_new(matches, goals, finished_ids):
    """Keep only matches we haven't stored as finished yet."""
    keep = ~matches["match_id"].isin(finished_ids)  # True for matches that still need loading
    new_matches = matches[keep].copy()  # those matches
    new_goals = goals[goals["match_id"].isin(new_matches["match_id"])].copy()  # and their goals
    return new_matches, new_goals


def upsert(con, teams, matches, goals):
    """Insert new rows and overwrite existing ones (no duplicates on re-runs)."""
    con.register("stg_teams", teams)  # let SQL see the pandas table as "stg_teams"
    con.register("stg_matches", matches)
    con.register("stg_goals", goals)
    con.execute("""
        INSERT OR REPLACE INTO teams (team_id, team_name, short_name, icon_url)
        SELECT team_id, team_name, short_name, icon_url FROM stg_teams
    """)  # new teams are added, existing ones overwritten
    con.execute("""
        INSERT OR REPLACE INTO matches
            (match_id, season, matchday, kickoff_utc, home_team_id, away_team_id,
             is_finished, home_goals, away_goals)
        SELECT match_id, season, matchday, kickoff_utc, home_team_id, away_team_id,
               is_finished, home_goals, away_goals FROM stg_matches
    """)  # same for matches
    con.execute("DELETE FROM goals WHERE match_id IN (SELECT match_id FROM stg_matches)")  # remove old goals of these matches
    con.execute("""
        INSERT INTO goals
            (goal_id, match_id, minute, scorer_id, scorer_name, scoring_team_id,
             is_penalty, is_own_goal, is_overtime, score_home, score_away)
        SELECT goal_id, match_id, minute, scorer_id, scorer_name, scoring_team_id,
               is_penalty, is_own_goal, is_overtime, score_home, score_away FROM stg_goals
    """)  # insert the fresh goals
    for name in ("stg_teams", "stg_matches", "stg_goals"):  # clean up
        con.unregister(name)


if __name__ == "__main__":  # quick test run (we'll add a proper pipeline.py next)
    raw = load_latest_raw()  # read the raw file
    teams, matches, goals = build_teams(raw), build_matches(raw, 2025), build_goals(raw)  # clean tables
    con = connect()  # open the database
    create_schema(con)  # make sure the tables exist
    new_matches, new_goals = filter_new(matches, goals, get_finished_ids(con))  # only what's new
    print(f"{len(matches)} matches in file, {len(new_matches)} to load")  # show the delta
    run_checks(teams, new_matches, new_goals)  # block bad data
    upsert(con, teams, new_matches, new_goals)  # write to the database
    print(con.execute("SELECT COUNT(*) FROM matches").fetchone())  # how many matches stored
    print(con.execute("SELECT COUNT(*) FROM goals").fetchone())  # how many goals stored
    con.close()  # done
