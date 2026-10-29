#!/usr/bin/env python3
"""Transforme des logs Cowrie (JSON, un evenement par ligne) en stats.json pour le dashboard."""
import argparse
import json
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

GEO_URL = "http://ip-api.com/batch?fields=status,country,countryCode,lat,lon,query"
MAX_LABEL = 80


def read_events(paths):
    for path in paths:
        for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue  # derniere ligne coupee pendant l'ecriture du log
            if isinstance(event, dict):
                yield event


def mask_ip(ip):
    """Les IP sont des donnees personnelles : on ne publie jamais le dernier octet."""
    if ":" in ip:
        return ":".join(ip.split(":")[:3]) + ":x"
    return ".".join(ip.split(".")[:3] + ["x"])


def geolocate(ips, cache_path, offline=False):
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    todo = [ip for ip in sorted(ips) if ip not in cache]
    if todo and not offline:
        # shortcut: ip-api gratuit = HTTP seulement, 45 requetes/min, usage non commercial.
        # A remplacer par une base GeoLite2 locale si le volume augmente.
        for i in range(0, len(todo), 100):
            body = json.dumps(todo[i:i + 100]).encode()
            req = urllib.request.Request(GEO_URL, body, {"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    for e in json.load(resp):
                        if e.get("status") == "success":
                            cache[e["query"]] = {"country": e["country"], "lat": e["lat"], "lon": e["lon"]}
            except OSError as err:
                print(f"geolocalisation indisponible : {err}", file=sys.stderr)
                break
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache))
    return cache


def summarize(events, geo, demo=False):
    sessions = attempts = successes = 0
    usernames, passwords, commands, days, hits = Counter(), Counter(), Counter(), Counter(), Counter()
    for e in events:
        kind = e.get("eventid", "")
        if kind == "cowrie.session.connect" and e.get("src_ip"):
            sessions += 1
            hits[e["src_ip"]] += 1
            days[str(e.get("timestamp", ""))[:10]] += 1
        elif kind in ("cowrie.login.failed", "cowrie.login.success"):
            attempts += 1
            successes += kind.endswith("success")
            usernames[str(e.get("username", ""))] += 1
            passwords[str(e.get("password", ""))] += 1
        elif kind == "cowrie.command.input":
            commands[str(e.get("input", "")).strip()] += 1

    countries, points = Counter(), []
    for ip, n in hits.items():
        g = geo.get(ip)
        if g:
            countries[g["country"]] += n
            points.append({"ip": mask_ip(ip), "country": g["country"], "lat": g["lat"], "lon": g["lon"], "hits": n})

    def top(counter, n=10):
        return [{"label": k[:MAX_LABEL], "count": v} for k, v in counter.most_common(n)]

    return {
        "demo": demo,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "totals": {
            "sessions": sessions,
            "unique_ips": len(hits),
            "login_attempts": attempts,
            "login_successes": successes,
        },
        "top_passwords": top(passwords),
        "top_usernames": top(usernames),
        "top_commands": top(commands),
        "top_countries": top(countries),
        "timeline": [{"day": d, "count": c} for d, c in sorted(days.items()) if d],
        "points": sorted(points, key=lambda p: -p["hits"])[:500],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("logs", nargs="+", help="un ou plusieurs fichiers cowrie.json")
    p.add_argument("--out", default="dashboard/stats.json")
    p.add_argument("--geo-cache", default="data/geo_cache.json")
    p.add_argument("--offline", action="store_true", help="n'appelle aucun service externe")
    p.add_argument("--demo", action="store_true", help="marque les donnees comme synthetiques")
    a = p.parse_args()

    events = list(read_events(a.logs))
    ips = {e["src_ip"] for e in events if e.get("eventid") == "cowrie.session.connect" and e.get("src_ip")}
    stats = summarize(events, geolocate(ips, Path(a.geo_cache), a.offline), a.demo)

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    t = stats["totals"]
    print(f"{out} : {t['sessions']} sessions, {t['unique_ips']} IP, {t['login_attempts']} tentatives")


if __name__ == "__main__":
    main()
