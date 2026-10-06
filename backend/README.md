# Sentinel-X — API, Dashboard & Panneau de contrôle

Partie « backend + supervision » du prototype SENTINEL-X (workshop EPSI Bac+4).
Elle tourne sur le **PC Serveur Local** (Raspberry Pi 5 ou laptop) via Docker-Compose.

## Architecture

```
ESP8266 --MQTT(S)--> Mosquitto --> API FastAPI --> SQLite
                                      |  \--WebSocket--> Dashboard (navigateur)
Script IA --HTTP POST /api/v1/alerts, /api/v1/frame--> API
Dashboard --POST /api/v1/commands--> API --MQTT sentinel/cmd--> ESP8266 (buzzer, LEDs)
```

## Prérequis

- Docker + Docker Compose
- (optionnel, pour tester) Python 3 + `pip install paho-mqtt`

## Démarrage

```bash
cp .env.example .env        # puis modifier API_KEY (valeur longue et aléatoire)
docker compose up -d --build
```

- Dashboard : http://IP_SERVEUR:8000
- Documentation interactive de l'API : http://IP_SERVEUR:8000/docs
- Santé : `curl http://IP_SERVEUR:8000/api/v1/health`

## Tester sans matériel

```bash
python tools/simulate.py <API_KEY>
```
Le script simule l'ESP8266 : les courbes bougent et des alertes « gaz » apparaissent.

## Contrat d'interface (à partager avec les autres membres)

### Télémétrie (ESP8266 → MQTT, topic `sentinel/telemetry`)
```json
{"device":"esp-01","temp":22.5,"hum":45.0,"gas":210,"pir":0}
```

### Commandes (API → ESP8266, topic `sentinel/cmd`)
```json
{"target":"buzzer","state":true}
```
`target` ∈ `buzzer`, `led_green`, `led_red`.

### Endpoints REST

| Méthode | Route | Auth | Rôle |
|---|---|---|---|
| POST | `/api/v1/alerts` | X-API-Key | Reçoit une alerte (capteur, IA…) |
| GET | `/api/v1/alerts?limit=50` | non | Historique des alertes |
| GET | `/api/v1/metrics?limit=100` | non | Historique des mesures |
| GET | `/api/v1/status` | non | État en ligne du boîtier |
| POST | `/api/v1/commands` | X-API-Key | Envoie une commande aux actionneurs |
| POST / GET | `/api/v1/frame` | POST: X-API-Key | Dernière image webcam annotée (JPEG) |
| GET | `/api/v1/health` | non | Santé de l'API et du broker |
| WS | `/ws` | non | Flux temps réel (mesures, alertes, commandes) |

Exemple :
```bash
curl -X POST http://localhost:8000/api/v1/alerts \
  -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
  -d '{"device":"esp-01","type":"intrusion","level":"critical","message":"Personne détectée"}'
```

Champs d'une alerte : `device`, `type`, `level` (`info`/`warning`/`critical`), `value` (optionnel), `message` (optionnel), `ts` (optionnel).

## Sécurité (côté API)

- Aucun secret dans le code : configuration par variables d'environnement (`.env` ignoré par Git).
- Écritures protégées par clé (`X-API-Key`), comparaison en temps constant.
- Validation stricte des entrées (Pydantic : types, longueurs, valeurs autorisées).
- Dashboard : affichage via `textContent` (pas d'injection XSS).
- Conteneur exécuté en utilisateur non-root.
- À faire avec Cyber/Infra : MQTTS (variable `MQTT_CA`), HTTPS devant l'API (reverse proxy), authentification Mosquitto, restriction des ports via UFW.

## Structure

```
api/main.py            API FastAPI (REST + WebSocket + client MQTT)
dashboard/index.html   Dashboard temps réel + panneau de contrôle
mosquitto/             Configuration du broker (dev, à durcir)
tools/simulate.py      Simulateur de l'ESP8266
docker-compose.yml     Stack Mosquitto + API
```

## Dépannage

- Pas de courbes : vérifier `docker compose logs api` et `/api/v1/health` (champ `mqtt`).
- Commandes en erreur 401 : saisir la clé API dans le panneau de contrôle.
- Commandes en erreur 503 : le broker MQTT n'est pas joignable.
