"""Fetch T1 (premium-tier) pro match data from the OpenDota API.

Outputs (in ./data):
- leagues.json        : full league list with official tiers
- t1Matches.json      : recent premium-tier matches (paginated, ~800)
- t1Details.json      : slim per-match details for the most recent ~60 T1 matches
"""
import json
import os
import time
import urllib.request

BASE = "https://api.opendota.com/api"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
T1_TARGET = 600          # T1 matches to collect
DETAIL_COUNT = 60        # recent matches to fetch slim details for
MAX_PAGES = 110

# T1 联赛定义：premium 级别 + 主流顶级赛事白名单（professional 级里的大赛）
T1_NAME_PATTERNS = (
    "The International",      # TI 及其区域预选赛
    "Esports World Cup",      # 电竞世界杯
    "BLAST",                  # BLAST Slam 系列
    "Riyadh",                 # 利雅得大师赛
    "ESL One", "DreamLeague", "PGL ", "BetBoom Dacha", "FISSURE",
    "Games of the Future",
)


def is_t1(tier: str, league_name: str) -> bool:
    if tier == "premium":
        return True
    name = (league_name or "").lower()
    return any(p.lower() in name for p in T1_NAME_PATTERNS)


def fetch(path, retries=3, timeout=60):
    url = BASE + path
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "dota2-analytics-demo/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"failed {url}: {last}")


def save(name, payload):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    print(f"saved {name} ({os.path.getsize(os.path.join(OUT, name)) // 1024} KB)", flush=True)


def slim_match(m):
    keep_players = [{
        "account_id": p.get("account_id"),
        "name": p.get("name") or p.get("personaname"),
        "hero_id": p.get("hero_id"),
        "player_slot": p.get("player_slot"),
        "kills": p.get("kills"), "deaths": p.get("deaths"), "assists": p.get("assists"),
        "gold_per_min": p.get("gold_per_min"), "xp_per_min": p.get("xp_per_min"),
        "last_hits": p.get("last_hits"), "denies": p.get("denies"),
        "level": p.get("level"), "net_worth": p.get("net_worth"),
        "hero_damage": p.get("hero_damage"), "tower_damage": p.get("tower_damage"),
        "hero_healing": p.get("hero_healing"),
    } for p in (m.get("players") or [])]
    return {
        "match_id": m.get("match_id"),
        "duration": m.get("duration"),
        "start_time": m.get("start_time"),
        "league_name": (m.get("league") or {}).get("name"),
        "radiant_team": (m.get("radiant_team") or {}).get("name"),
        "dire_team": (m.get("dire_team") or {}).get("name"),
        "radiant_win": m.get("radiant_win"),
        "radiant_score": m.get("radiant_score"),
        "dire_score": m.get("dire_score"),
        "radiant_gold_adv": m.get("radiant_gold_adv"),
        "radiant_xp_adv": m.get("radiant_xp_adv"),
        "picks_bans": m.get("picks_bans"),
        "players": keep_players,
    }


def main():
    os.makedirs(OUT, exist_ok=True)

    print("fetching /leagues ...", flush=True)
    leagues = fetch("/leagues")
    save("leagues.json", leagues)
    tier_map = {l["leagueid"]: l.get("tier") for l in leagues}
    print("league tiers loaded", flush=True)

    print("paginating /proMatches ...", flush=True)
    t1 = []
    less_than = None
    for page in range(MAX_PAGES):
        path = "/proMatches" + (f"?less_than_match_id={less_than}" if less_than else "")
        batch = fetch(path)
        if not batch:
            break
        for m in batch:
            if is_t1(tier_map.get(m.get("leagueid")), m.get("league_name")):
                t1.append(m)
        less_than = batch[-1]["match_id"]
        print(f"  page {page + 1}: total T1 {len(t1)} (scan cursor {less_than})", flush=True)
        if len(t1) >= T1_TARGET:
            break
        time.sleep(1.2)
    save("t1Matches.json", t1)

    print(f"fetching slim details for {DETAIL_COUNT} recent T1 matches ...", flush=True)
    details = []
    for i, m in enumerate(t1[:DETAIL_COUNT]):
        try:
            full = fetch(f"/matches/{m['match_id']}", timeout=90)
            details.append(slim_match(full))
            print(f"  [{i + 1}/{DETAIL_COUNT}] ok {m['match_id']}", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"  [{i + 1}/{DETAIL_COUNT}] skip {m['match_id']}: {e}", flush=True)
        time.sleep(1.15)
    save("t1Details.json", details)
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
