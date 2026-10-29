#!/usr/bin/env bash
# Recupere les logs du conteneur Cowrie puis recalcule dashboard/stats.json.
# Usage : ./collect.sh   (a mettre dans un cron, par exemple toutes les heures)
set -euo pipefail
cd "$(dirname "$0")"

LOG_DIR="${COWRIE_LOG_DIR:-/cowrie/cowrie-git/var/log/cowrie}"

rm -rf data/logs && mkdir -p data/logs
docker cp "cowrie:${LOG_DIR}/." data/logs/   # copie aussi les logs tournes (cowrie.json.AAAA-MM-JJ)
python3 analyzer/parse.py data/logs/cowrie.json* --out dashboard/stats.json --geo-cache data/geo_cache.json
