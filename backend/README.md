# Sentinel-X - Backend, API & Dashboard

Partie backend + supervision du prototype SENTINEL-X réalisé dans le cadre du workshop EPSI Bac+4.

Cette partie regroupe une API FastAPI, un dashboard web, un broker MQTT Mosquitto et un simulateur permettant de tester le système sans matériel physique.

## Fonctionnalités réalisées

- API REST avec FastAPI
- Dashboard web de supervision
- Communication MQTT avec Mosquitto
- Stockage des données dans SQLite
- Affichage des mesures en temps réel
- WebSocket pour les mises à jour du dashboard
- Gestion et affichage des alertes
- Envoi de commandes depuis le dashboard
- Test de commande du buzzer
- Simulateur Python de données capteurs
- Documentation API avec Swagger
- Protection des écritures par clé API

## Architecture

    Simulateur / ESP8266
            |
            | MQTT
            v
        Mosquitto
            |
            v
        API FastAPI
          /    \
         /      \
      SQLite   WebSocket
                  |
                  v
              Dashboard

Le simulateur permet de reproduire les données d'un ESP8266 afin de tester le backend sans matériel physique.

## Prérequis

- Docker
- Docker Compose
- Python 3
- paho-mqtt pour le simulateur

Installation du module Python :

    pip install paho-mqtt

## Configuration

Créer le fichier .env à partir de .env.example et définir une clé API personnelle.

    cp .env.example .env

Le fichier .env contient des informations sensibles et est exclu du dépôt Git.

## Démarrage

Depuis le dossier backend :

    docker compose up -d --build

Vérifier les conteneurs :

    docker compose ps

## Accès

Dashboard :

    http://localhost:8000

Documentation Swagger :

    http://localhost:8000/docs

Vérification de l'API :

    http://localhost:8000/api/v1/health

## Simulateur

Le simulateur Python permet d'envoyer des données de capteurs vers le backend via MQTT.

Depuis le dossier backend :

    python tools/simulate.py <API_KEY>

Le simulateur envoie notamment des données de température, humidité, gaz et présence.

## MQTT

Topic utilisé pour les données de télémétrie :

    sentinel/telemetry

Exemple de message :

    {
      "device": "esp-01",
      "temperature": 20.5,
      "humidity": 46.2,
      "gas": 210,
      "pir": false
    }

Topic utilisé pour les commandes :

    sentinel/cmd

Exemple de commande :

    {
      "device": "esp-01",
      "buzzer": true
    }

## API REST

Principaux endpoints disponibles :

    GET  /api/v1/health
    GET  /api/v1/status
    GET  /api/v1/metrics
    GET  /api/v1/alerts
    POST /api/v1/alerts
    POST /api/v1/commands
    WS   /ws

L'endpoint POST /api/v1/alerts permet notamment de créer une alerte.

Exemple :

    {
      "device": "esp-01",
      "type": "intrusion",
      "level": "critical",
      "message": "Test manuel"
    }

## Test du buzzer

Le dashboard permet d'envoyer une commande au backend.

La commande est transmise via l'API puis publiée sur le topic MQTT de commande.

Le test réalisé permet notamment d'envoyer une commande buzzer ON depuis le dashboard.

## Sécurité actuelle

Les mesures de sécurité actuellement mises en place sont :

- clé API stockée dans .env
- fichier .env exclu du dépôt Git
- protection des écritures par clé API
- validation des données avec Pydantic
- utilisation de textContent pour l'affichage des données dans le dashboard
- conteneur API exécuté sans privilèges root

## Structure

    backend/
    ├── api/
    ├── dashboard/
    ├── mosquitto/
    ├── tools/
    ├── .env.example
    ├── .gitignore
    ├── docker-compose.yml
    └── README.md

## Évolutions prévues

Les éléments suivants ne sont pas encore intégrés dans cette version :

- intégration avec le matériel ESP8266 réel
- intégration de la caméra et de l'analyse IA
- MQTTS / TLS
- HTTPS
- sécurisation avancée de Mosquitto
- durcissement réseau et infrastructure
- supervision et sécurité avancées
