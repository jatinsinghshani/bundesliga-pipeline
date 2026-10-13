import json  # to save the raw data as a .json file
import time  # to pause between retries
from datetime import datetime, timezone  # to put a timestamp in the file name
from pathlib import Path  # to build file paths that work on Windows

import requests  # to call the API

LEAGUE = "bl1"  # bl1 = 1. Bundesliga
SEASON = 2025  # the season's start year (2025 = 2025/26)
BASE_URL = "https://api.openligadb.de"  # free API, no key needed
RAW_DIR = Path("data/raw")  # folder where raw files get saved


def fetch_season_matches(league, season, retries=3):
    """Download all matches of a season. Retries if the call fails."""
    url = f"{BASE_URL}/getmatchdata/{league}/{season}"  # build the full address
    for attempt in range(1, retries + 1):  # attempt 1, then 2, then 3
        try:
            response = requests.get(url, timeout=30)  # call the API, give up after 30 seconds
            response.raise_for_status()  # turn errors like 404 or 500 into exceptions
            return response.json()  # success: return the data as a Python list
        except requests.RequestException as error:  # something went wrong
            print(f"Attempt {attempt} failed: {error}")  # tell us what happened
            if attempt == retries:  # that was our last try
                raise  # stop and show the error
            time.sleep(2 ** attempt)  # wait 2s, then 4s before trying again


def save_raw(data, league, season):
    """Save the untouched API response to data/raw/."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)  # create the folder if it's missing
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")  # e.g. 20261013T093000Z
    path = RAW_DIR / f"{league}_{season}_{stamp}.json"  # file name with league, season, time
    with open(path, "w", encoding="utf-8") as f:  # open the file for writing
        json.dump(data, f)  # write the data exactly as we got it
    return path  # give back the path so we know where it went


if __name__ == "__main__":  # runs only when you run this file directly
    matches = fetch_season_matches(LEAGUE, SEASON)  # download
    path = save_raw(matches, LEAGUE, SEASON)  # save
    print(f"Fetched {len(matches)} matches, saved to {path}")  # confirm