import time
import requests
from sklearn.ensemble import IsolationForest
import os



# =====================================================
# CONFIGURATION
# =====================================================

API_BASE = "http://api:8000/api/v1"

# Mets exactement la même clé que dans CyberNex/.env
API_KEY = os.getenv("API_KEY", "")

DEVICE_NAME = "CYBERNEX-AI-ANOMALY"

# Nombre minimum de mesures avant d'entraîner le modèle
MIN_SAMPLES = 30

# Nombre de mesures récupérées depuis FastAPI
HISTORY_LIMIT = 100

# Vérification toutes les 5 secondes
CHECK_INTERVAL = 5

# Évite les alertes IA répétitives
ALERT_COOLDOWN = 30

last_alert_time = 0


# =====================================================
# RECUPERATION DES MESURES
# =====================================================

def get_metrics():

    try:

        response = requests.get(
            f"{API_BASE}/metrics?limit={HISTORY_LIMIT}",
            timeout=5
        )

        response.raise_for_status()

        data = response.json()

        # Garder uniquement les lignes complètes
        clean_data = []

        for row in data:

            if (
                row.get("temp") is not None
                and row.get("hum") is not None
                and row.get("gas") is not None
            ):

                clean_data.append(row)

        # Remettre les données dans l'ordre chronologique
        clean_data.sort(
            key=lambda x: x.get("ts", 0)
        )

        return clean_data

    except Exception as error:

        print(
            "Erreur récupération métriques :",
            error
        )

        return []


# =====================================================
# ENVOI D'UNE ALERTE IA
# =====================================================

def send_anomaly_alert(row, score):

    payload = {

        "device": DEVICE_NAME,

        "type": "ai_anomaly",

        "level": "warning",

        "value": float(score),

        "message":
            (
                "Anomalie IA détectée : "
                f"temperature={row['temp']}, "
                f"humidite={row['hum']}, "
                f"gaz={row['gas']}"
            )
    }

    try:

        response = requests.post(
            f"{API_BASE}/alerts",
            json=payload,
            headers={
                "X-API-Key": API_KEY
            },
            timeout=5
        )

        if response.ok:

            print(
                "Alerte IA envoyée au backend"
            )

        else:

            print(
                "Erreur API :",
                response.status_code
            )

    except Exception as error:

        print(
            "Erreur envoi alerte IA :",
            error
        )


# =====================================================
# BOUCLE IA
# =====================================================

print(
    "CyberNex - Isolation Forest démarré"
)

print(
    f"Minimum requis : {MIN_SAMPLES} mesures"
)


while True:

    metrics = get_metrics()

    if len(metrics) < MIN_SAMPLES:

        print(
            f"Pas assez de données : "
            f"{len(metrics)}/{MIN_SAMPLES}"
        )

        time.sleep(
            CHECK_INTERVAL
        )

        continue


    # -------------------------------------------------
    # Séparer historique et dernière mesure
    # -------------------------------------------------

    training_rows = metrics[:-1]

    latest = metrics[-1]


    X_train = [

        [
            row["temp"],
            row["hum"],
            row["gas"]
        ]

        for row in training_rows
    ]


    latest_values = [[

        latest["temp"],
        latest["hum"],
        latest["gas"]

    ]]


    # -------------------------------------------------
    # Modèle Isolation Forest
    # -------------------------------------------------

    model = IsolationForest(

        n_estimators=100,

        contamination=0.05,

        random_state=42
    )


    model.fit(
        X_train
    )


    prediction = model.predict(
        latest_values
    )[0]


    score = model.decision_function(
        latest_values
    )[0]


    print(
        f"T={latest['temp']} "
        f"H={latest['hum']} "
        f"G={latest['gas']} "
        f"score={score:.4f}"
    )


    # =================================================
    # ANOMALIE
    # =================================================

    if prediction == -1:

        print(
            "ANOMALIE IA DETECTEE"
        )

        now = time.time()

        if (
            now - last_alert_time
            >= ALERT_COOLDOWN
        ):

            send_anomaly_alert(
                latest,
                score
            )

            last_alert_time = now


    else:

        print(
            "Comportement normal"
        )


    print(
        "-----------------------------"
    )


    time.sleep(
        CHECK_INTERVAL
    )