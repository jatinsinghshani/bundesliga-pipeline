import glob  # to find files by pattern
import json  # to read the raw json file

import pandas as pd  # tables in Python (like Excel, but code)

FINAL_RESULT_TYPE_ID = 2  # in this API, result type 2 = final score (1 = half-time)


def load_latest_raw():
    """Read the newest raw file from data/raw/."""
    files = sorted(glob.glob("data/raw/*.json"))  # list all raw files, oldest to newest
    with open(files[-1], encoding="utf-8") as f:  # open the newest one
        return json.load(f)  # turn the json text into Python lists/dicts


def build_teams(raw):
    """One row per team."""
    rows = []  # we'll collect one small dict per team here
    for match in raw:  # go through every match
        for key in ("team1", "team2"):  # home team, then away team
            team = match[key]  # grab that team's info
            rows.append({  # keep only the columns we care about
                "team_id": team["teamId"],  # unique id of the team
                "team_name": team["teamName"],  # full name
                "short_name": team.get("shortName"),  # short name (None if missing)
                "icon_url": team.get("teamIconUrl"),  # logo link
            })
    df = pd.DataFrame(rows)  # turn the list of dicts into a table
    return df.drop_duplicates(subset="team_id").reset_index(drop=True)  # each team appears many times, keep one


def get_final_score(match):
    """Return (home_goals, away_goals), or (None, None) if there's no final score."""
    for result in match.get("matchResults") or []:  # look through half-time and final results
        if result.get("resultTypeID") == FINAL_RESULT_TYPE_ID:  # find the final one
            return result.get("pointsTeam1"), result.get("pointsTeam2")  # home score, away score
    return None, None  # match not played yet


def build_matches(raw, season):
    """One row per match."""
    rows = []  # one dict per match
    for match in raw:  # go through every match
        home, away = get_final_score(match)  # final score if there is one
        finished = bool(match.get("matchIsFinished"))  # True or False
        rows.append({
            "match_id": match["matchID"],  # unique id of the match
            "season": season,  # which season this belongs to
            "matchday": (match.get("group") or {}).get("groupOrderID"),  # round number (1 to 34)
            "kickoff_utc": match.get("matchDateTimeUTC"),  # start time as text for now
            "home_team_id": match["team1"]["teamId"],  # link to the teams table
            "away_team_id": match["team2"]["teamId"],  # link to the teams table
            "is_finished": finished,  # has the match been played?
            "home_goals": home if finished else None,  # only keep scores for finished matches
            "away_goals": away if finished else None,
        })
    df = pd.DataFrame(rows)  # to a table
    df["kickoff_utc"] = pd.to_datetime(df["kickoff_utc"], utc=True).dt.tz_localize(None)  # text -> real timestamp
    for col in ("matchday", "home_goals", "away_goals"):  # these are whole numbers that can be empty
        df[col] = df[col].astype("Int64")  # capital-I Int64 allows empty values (NULL)
    return df


def build_goals(raw):
    """One row per goal. Works out which team scored from the running score."""
    rows = []  # one dict per goal
    for match in raw:  # go through every match
        home_id = match["team1"]["teamId"]  # home team id
        away_id = match["team2"]["teamId"]  # away team id
        prev_home, prev_away = 0, 0  # every match starts 0-0
        goals = sorted(  # put goals in the order they happened
            match.get("goals") or [],  # the goals list (empty if none)
            key=lambda g: g["scoreTeam1"] + g["scoreTeam2"],  # total goals so far = order
        )
        for g in goals:  # go through each goal in order
            if g["scoreTeam1"] > prev_home:  # home score went up
                scoring_team = home_id  # so the home team scored
            elif g["scoreTeam2"] > prev_away:  # away score went up
                scoring_team = away_id  # so the away team scored
            else:  # score didn't change, bad data
                scoring_team = None  # we can't tell who scored
            prev_home, prev_away = g["scoreTeam1"], g["scoreTeam2"]  # remember the score for the next goal
            rows.append({
                "goal_id": g["goalID"],  # unique id of the goal
                "match_id": match["matchID"],  # link to the matches table
                "minute": g.get("matchMinute"),  # minute of the goal
                "scorer_id": g.get("goalGetterID"),  # player id
                "scorer_name": g.get("goalGetterName"),  # player name
                "scoring_team_id": scoring_team,  # the team we worked out above
                "is_penalty": bool(g.get("isPenalty")),  # True if from the spot
                "is_own_goal": bool(g.get("isOwnGoal")),  # True if an own goal
                "is_overtime": bool(g.get("isOvertime")),  # True if in extra time
                "score_home": g["scoreTeam1"],  # home score after this goal
                "score_away": g["scoreTeam2"],  # away score after this goal
            })
    df = pd.DataFrame(rows)  # to a table
    for col in ("minute", "scorer_id", "scoring_team_id"):  # whole numbers that can be empty
        df[col] = df[col].astype("Int64")  # Int64 allows empty values
    return df


if __name__ == "__main__":  # runs only when you run this file directly
    raw = load_latest_raw()  # read the raw file
    teams = build_teams(raw)  # teams table
    matches = build_matches(raw, 2025)  # matches table
    goals = build_goals(raw)  # goals table
    print(f"{len(teams)} teams, {len(matches)} matches, {len(goals)} goals")  # sizes
    print(goals.head(10))  # peek at the first 10 goals