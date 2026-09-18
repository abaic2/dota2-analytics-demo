"""Fetch real Dota2 data snapshots from the OpenDota public API.

Saves JSON snapshots into ./data so the Streamlit app ships with real,
reproducible data (and can still attempt a live refresh at runtime).
"""
import json
import os
import sys
import time
import urllib.request

BASE = "https://api.opendota.com/api"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

ENDPOINTS = {
    "heroStats.json": "/heroStats",
    "proMatches.json": "/proMatches",
    "proPlayers.json": "/proPlayers",
    "heroRankings.json": "/heroRankings",
    "patches.json": "/patches",
    "constants.json": "/constants/heroes",
    "publicMmr.json": "/distributions",
    "topPlayersByMMR.json": "/search?rank_tier_account_id=0",  # placeholder, unused
}


def fetch(path: str, retries: int = 3):
    url = BASE + path
    last_err = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "dota2-analytics-demo/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"failed {url}: {last_err}")


def main():
    os.makedirs(OUT, exist_ok=True)
    todo = {
        "heroStats.json": "/heroStats",
        "proMatches.json": "/proMatches",
        "proPlayers.json": "/proPlayers",
        "heroRankings.json": "/heroRankings",
        "patches.json": "/patches",
        "constants.json": "/constants/heroes",
        "distributions.json": "/distributions",
    }
    for fname, path in todo.items():
        dest = os.path.join(OUT, fname)
        print(f"fetching {path} -> {fname} ...", flush=True)
        payload = fetch(path)
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        size = os.path.getsize(dest)
        print(f"  ok, {size/1024:.0f} KB", flush=True)
        time.sleep(1.0)
    print("ALL DONE")


if __name__ == "__main__":
    sys.exit(main())
