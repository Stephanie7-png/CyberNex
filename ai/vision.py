import cv2
import time
import requests

API_BASE = "http://localhost:8000/api/v1"
API_KEY = "35hR_DXHUXlRm6fy-QLL-c2vhAez3swIEXDrCw1XQKo"
DEVICE_NAME = "CYBERNEX-CAM-01"

ALERT_COOLDOWN = 15

# Nombre d'images consécutives nécessaires
DETECTION_FRAMES = 5
CLEAR_FRAMES = 10

hog = cv2.HOGDescriptor()
hog.setSVMDetector(
    cv2.HOGDescriptor_getDefaultPeopleDetector()
)

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Erreur : camera non detectee")
    raise SystemExit

print("Camera detectee")
print("Surveillance anti-intrusion demarree")
print("Appuie sur Q pour quitter")

last_alert_time = 0
state = "normal"

detected_count = 0
clear_count = 0


def send_alert(message):
    payload = {
        "device": DEVICE_NAME,
        "type": "intrusion",
        "level": "critical",
        "value": 1,
        "message": message
    }

    try:
        response = requests.post(
            f"{API_BASE}/alerts",
            json=payload,
            headers={"X-API-Key": API_KEY},
            timeout=3
        )

        if response.ok:
            print("Alerte envoyee au backend")
        else:
            print("Erreur API :", response.status_code)

    except Exception as error:
        print("Erreur API :", error)


def send_frame(frame):
    ok, buffer = cv2.imencode(".jpg", frame)

    if not ok:
        return

    try:
        requests.post(
            f"{API_BASE}/frame",
            data=buffer.tobytes(),
            headers={
                "Content-Type": "image/jpeg",
                "X-API-Key": API_KEY
            },
            timeout=2
        )
    except Exception:
        pass


while True:

    ret, frame = cap.read()

    if not ret:
        break

    frame = cv2.resize(frame, (640, 480))

    boxes, weights = hog.detectMultiScale(
        frame,
        winStride=(8, 8),
        padding=(8, 8),
        scale=1.05
    )

    raw_detection = len(boxes) > 0

    # =========================
    # Stabilisation
    # =========================

    if raw_detection:
        detected_count += 1
        clear_count = 0

    else:
        clear_count += 1
        detected_count = 0

    # Passage en mode intrusion
    if detected_count >= DETECTION_FRAMES:
        state = "intrusion"

    # Retour en mode normal
    if clear_count >= CLEAR_FRAMES:
        state = "normal"

    # =========================
    # Affichage
    # =========================

    if state == "intrusion":

        for (x, y, w, h) in boxes:
            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (0, 0, 255),
                3
            )

        cv2.putText(
            frame,
            "ALERTE INTRUSION",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 0, 255),
            2
        )

        now = time.time()

        if now - last_alert_time >= ALERT_COOLDOWN:
            print("ALERTE : intrusion detectee")

            send_alert(
                "Intrusion detectee par la camera"
            )

            last_alert_time = now

    else:

        cv2.putText(
            frame,
            "ZONE SECURISEE",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 0),
            2
        )

    send_frame(frame)

    cv2.imshow(
        "CyberNex - Detection intrusion",
        frame
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


cap.release()
cv2.destroyAllWindows()