# SSH Honeypot Dashboard

Un faux serveur SSH ([Cowrie](https://github.com/cowrie/cowrie)) ouvert sur Internet, et un tableau de bord qui montre ce que les bots y font : d'où ils viennent, quels mots de passe ils testent, quelles commandes ils tapent quand le leurre les laisse entrer.

## Essayer en 30 secondes, sans honeypot

```bash
python3 analyzer/demo.py
python3 -m http.server -d dashboard 8000
```

Ouvre http://localhost:8000. Les données de démo sont synthétiques (adresses de la plage de documentation RFC 5737, positions approximatives) et la page affiche un bandeau pour le dire.

## Comment ça marche

```
Internet -> port 22 -> Cowrie (conteneur Docker) -> cowrie.json
                                                        |
                              collect.sh + analyzer/parse.py : agrégation, géoloc, IP masquées
                                                        |
                                    dashboard/stats.json -> dashboard/index.html
```

- **Cowrie** simule un shell SSH, accepte certaines connexions et enregistre tout : identifiants testés, commandes, fichiers téléchargés.
- **analyzer/parse.py** lit les logs et produit un seul fichier `stats.json` : totaux, top mots de passe, identifiants, commandes, pays, sessions par jour, points de la carte.
- **dashboard/** est une page statique (HTML, CSS, JS, carte Leaflet). Pas de base de données, pas de serveur applicatif.

## Déployer le vrai honeypot

Il te faut un petit VPS **dédié et jetable** (jamais ton réseau perso) avec Docker.

1. **Déplace ton vrai SSH** pour ne pas te bloquer : mets `Port 2200` dans `/etc/ssh/sshd_config`, ouvre le port 2200 dans le pare-feu, redémarre `sshd`, puis vérifie dans un second terminal que `ssh -p 2200 toi@serveur` fonctionne avant de fermer la session en cours.
2. Lance le leurre : `docker compose -f honeypot/docker-compose.yml up -d`
3. Laisse tourner. Les premiers bots arrivent souvent en quelques minutes à quelques heures.
4. Génère les stats : `./collect.sh`, puis sers le dossier `dashboard/` (ou publie-le).
5. Pour garder le tableau à jour, ajoute une ligne de cron : `0 * * * * cd /chemin/du/repo && ./collect.sh`

## Choix de sécurité

- **Isolation** : serveur dédié, conteneur sans aucune capability Linux (`cap_drop: ALL`, `no-new-privileges`), rien de sensible sur la machine.
- **Pas d'injection** : mots de passe et commandes affichés viennent des attaquants. Le dashboard utilise uniquement `textContent`, jamais `innerHTML`.
- **RGPD** : une adresse IP est une donnée personnelle. `stats.json` ne contient que des adresses au dernier octet masqué, et les logs bruts (`data/`) sont exclus de Git.
- **Géolocalisation** : `parse.py` envoie les IP à ip-api.com (service gratuit, HTTP, usage non commercial). `--offline` désactive tout appel externe et n'utilise que le cache local.
- **Observation seulement** : le honeypot ne sert jamais à riposter ou à scanner en retour.

## Tests

```bash
python3 -m unittest discover -s tests
```

## Limites connues

- Les positions sont approximatives : elles viennent d'une base IP, pas d'un vrai emplacement.
- Cowrie est repérable par un attaquant expérimenté. On observe surtout des bots automatiques.
- Le chemin des logs dans le conteneur peut changer selon la version de l'image. Si `collect.sh` ne trouve rien : `COWRIE_LOG_DIR=/chemin ./collect.sh`.
- Leaflet est chargé depuis unpkg et les tuiles viennent d'OpenStreetMap : la carte demande une connexion à Internet.

## Pistes pour aller plus loin

- Remplacer ip-api par une base GeoLite2 locale.
- Alerter (mail, Discord) quand une IP tape des commandes après une connexion acceptée.
- Analyser en sandbox les fichiers que les bots téléchargent dans le leurre.
- Envoyer les logs vers Grafana ou Prometheus.

## Licence

MIT, voir [LICENSE](LICENSE).
