import os  # to read the SEASON setting
import sys  # to exit with an error code on failure

from src.extract import LEAGUE, fetch_season_matches, save_raw  # stage 1: extract
from src.load import connect, create_schema, filter_new, get_finished_ids, upsert  # stage 4: load
from src.quality import run_checks  # stage 3: quality gate
from src.transform import build_goals, build_matches, build_teams  # stage 2: transform

SEASON = int(os.environ.get("SEASON", 2026))  # which season to load (change with SEASON=2025)


def run():
    """Run the whole pipeline once, from API to database."""
    print(f"--- Extract (season {SEASON}) ---")  # stage banner
    raw = fetch_season_matches(LEAGUE, SEASON)  # call the API
    path = save_raw(raw, LEAGUE, SEASON)  # keep the untouched copy
    print(f"{len(raw)} matches fetched, raw copy at {path}")  # confirm

    print("--- Transform ---")  # stage banner
    teams = build_teams(raw)  # teams table
    matches = build_matches(raw, SEASON)  # matches table
    goals = build_goals(raw)  # goals table

    print("--- Load ---")  # stage banner
    con = connect()  # open the database
    try:
        create_schema(con)  # make sure the tables exist
        new_matches, new_goals = filter_new(matches, goals, get_finished_ids(con))  # only what's new
        print(f"{len(new_matches)} of {len(matches)} matches to load")  # show the delta
        run_checks(teams, new_matches, new_goals)  # stop here if the data is bad
        upsert(con, teams, new_matches, new_goals)  # write to the database
        print(f"Done: {len(new_matches)} matches and {len(new_goals)} goals loaded")  # summary
    finally:
        con.close()  # always close the database, even on failure


if __name__ == "__main__":  # runs only when you run this file directly
    try:
        run()  # go
    except Exception as error:  # anything went wrong
        print(f"PIPELINE FAILED: {error}")  # say what happened
        sys.exit(1)  # non-zero exit code so schedulers and Docker see the failure
