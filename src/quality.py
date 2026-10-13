from src.transform import load_latest_raw, build_teams, build_matches, build_goals  # reuse our transform code


class DataQualityError(Exception):
    """Our own error type, raised when a blocking check fails."""


def run_checks(teams, matches, goals):
    """Check the tables. Stops on errors, only prints warnings."""
    errors = []  # serious problems that must stop the pipeline
    warnings = []  # small problems we just want to know about

    if matches["match_id"].duplicated().any():  # same match twice?
        errors.append("duplicate match_id in matches")
    if goals["goal_id"].duplicated().any():  # same goal twice?
        errors.append("duplicate goal_id in goals")
    if teams["team_id"].duplicated().any():  # same team twice?
        errors.append("duplicate team_id in teams")

    finished = matches[matches["is_finished"]]  # only matches that were played
    if finished[["home_goals", "away_goals"]].isna().any().any():  # played but no score?
        errors.append("finished matches with a missing score")

    if not set(matches["home_team_id"]).issubset(set(teams["team_id"])):  # every home team must exist in teams
        errors.append("matches use a home team that is not in teams")
    if not set(matches["away_team_id"]).issubset(set(teams["team_id"])):  # every away team must exist in teams
        errors.append("matches use an away team that is not in teams")
    if not set(goals["match_id"]).issubset(set(matches["match_id"])):  # every goal must belong to a match
        errors.append("goals belong to a match that is not in matches")

    minutes = goals["minute"].dropna()  # ignore goals with no minute
    if ((minutes < 0) | (minutes > 130)).any():  # no goal before 0 or after 130 minutes
        errors.append("goal minute outside 0-130")

    expected = finished.set_index("match_id")[["home_goals", "away_goals"]].sum(axis=1)  # goals each match should have
    actual = goals.groupby("match_id").size()  # goal rows each match really has
    bad = [m for m, n in expected.items() if actual.get(m, 0) != n]  # matches where they differ
    if bad:  # a mismatch is odd but not fatal
        warnings.append(f"{len(bad)} finished matches where goal rows != final score")

    for w in warnings:  # show each warning
        print("WARNING:", w)
    if errors:  # any serious problem?
        raise DataQualityError("; ".join(errors))  # stop everything
    print(f"All checks passed ({len(warnings)} warnings)")  # all good


if __name__ == "__main__":  # runs only when you run this file directly
    raw = load_latest_raw()  # read the raw file
    run_checks(build_teams(raw), build_matches(raw, 2025), build_goals(raw))  # run all checks