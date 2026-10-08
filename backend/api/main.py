"""CyberNex - API REST + WebSocket (PC Serveur Local)."""
import asyncio
import json
import os
import secrets
import sqlite3
import threading
import time
from contextlib import asynccontextmanager
from typing import Literal, Optional

import paho.mqtt.client as mqtt

from fastapi import (Depends, FastAPI, Header, HTTPException, Request,
                     WebSocket, WebSocketDisconnect)
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ---------- Configuration (variables d'environnement, jamais de secret en dur) ----------
MQTT_HOST = os.getenv("MQTT_HOST", "172.20.10.11")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_CA = os.getenv("MQTT_CA", "")          # chemin du CA => active MQTTS
API_KEY = os.getenv("API_KEY", "")           # vide = pas d'auth (dev uniquement)
DB_PATH = os.getenv("DB_PATH", "/data/cybernex.db")
TOPIC_TELEMETRY = "cybernex/sensors"
TOPIC_CMD = "cybernex/cmd"

# ---------- Base de donnees ----------
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
db = sqlite3.connect(DB_PATH, check_same_thread=False)
db_lock = threading.Lock()
db.executescript("""
CREATE TABLE IF NOT EXISTS metrics(
  id INTEGER PRIMARY KEY, ts REAL, device TEXT,
  temp REAL, hum REAL, gas REAL, pir INTEGER);
CREATE TABLE IF NOT EXISTS alerts(
  id INTEGER PRIMARY KEY, ts REAL, device TEXT, type TEXT,
  level TEXT, value REAL, message TEXT);
""")

# ---------- Etat partage ----------
clients: set = set()
loop: Optional[asyncio.AbstractEventLoop] = None
mqtt_client: Optional[mqtt.Client] = None
last_frame: bytes = b""
last_seen: dict = {}


async def broadcast(msg: dict):
    dead = []
    for ws in list(clients):
        try:
            await ws.send_json(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        clients.discard(ws)


def push(msg: dict):
    if loop:
        asyncio.run_coroutine_threadsafe(broadcast(msg), loop)


def num(d: dict, k: str):
    try:
        return float(d[k])
    except (KeyError, TypeError, ValueError):
        return None


# ---------- MQTT ----------
def on_connect(c, userdata, flags, reason_code, properties=None):
    c.subscribe(TOPIC_TELEMETRY)


def on_message(c, userdata, msg):
    try:
        d = json.loads(msg.payload)
        if not isinstance(d, dict):
            return
    except ValueError:
        return
    row = {
      "ts": time.time(),
      "device": str(
        d.get("device_id", "CYBERNEX-EDGE-01")
      )[:32],

     "temp": num(d, "temperature"),
     "hum": num(d, "humidity"),
     "gas": num(d, "gaz"),

      "pir": int(
        bool(d.get("presence", 0))
      ),
    }
    with db_lock:
        db.execute("INSERT INTO metrics(ts,device,temp,hum,gas,pir) VALUES(?,?,?,?,?,?)",
                   (row["ts"], row["device"], row["temp"], row["hum"], row["gas"], row["pir"]))
        db.commit()
    last_seen[row["device"]] = row["ts"]
    push({"kind": "metric", **row})


def start_mqtt():
    global mqtt_client
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if MQTT_USER:
        c.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    if MQTT_CA:
        c.tls_set(ca_certs=MQTT_CA)
    c.on_connect, c.on_message = on_connect, on_message
    c.reconnect_delay_set(1, 10)
    c.connect_async(MQTT_HOST, MQTT_PORT)
    c.loop_start()
    mqtt_client = c


@asynccontextmanager
async def lifespan(app: FastAPI):
    global loop
    loop = asyncio.get_running_loop()
    start_mqtt()
    yield
    if mqtt_client:
        mqtt_client.loop_stop()


app = FastAPI(title="CyberNex API", version="1.0", lifespan=lifespan)


# ---------- Authentification simple par cle ----------
def check_key(x_api_key: str = Header(default="")):
    if API_KEY and not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Cle API invalide")


# ---------- Modeles ----------
class Alert(BaseModel):
    device: str = Field(max_length=32)
    type: str = Field(max_length=32)            # gas | temperature | intrusion | anomaly ...
    level: Literal["info", "warning", "critical"] = "info"
    value: Optional[float] = None
    message: Optional[str] = Field(default=None, max_length=200)
    ts: Optional[float] = None


class Command(BaseModel):
    target: Literal["buzzer", "led_green", "led_red"]
    state: bool


# ---------- Endpoints ----------
@app.get("/api/v1/health")
def health():
    return {"status": "ok", "mqtt": bool(mqtt_client and mqtt_client.is_connected())}


@app.post("/api/v1/alerts", status_code=201, dependencies=[Depends(check_key)])
def create_alert(a: Alert):
    ts = a.ts or time.time()
    with db_lock:
        cur = db.execute("INSERT INTO alerts(ts,device,type,level,value,message) VALUES(?,?,?,?,?,?)",
                         (ts, a.device, a.type, a.level, a.value, a.message))
        db.commit()
    alert = {"id": cur.lastrowid, "ts": ts, **a.model_dump(exclude={"ts"})}
    push({"kind": "alert", **alert})
    return alert


@app.get("/api/v1/alerts")
def list_alerts(limit: int = 50):
    limit = max(1, min(limit, 500))
    with db_lock:
        rows = db.execute("SELECT id,ts,device,type,level,value,message FROM alerts "
                          "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    keys = ["id", "ts", "device", "type", "level", "value", "message"]
    return [dict(zip(keys, r)) for r in rows]


@app.get("/api/v1/metrics")
def list_metrics(limit: int = 100):
    limit = max(1, min(limit, 1000))
    with db_lock:
        rows = db.execute("SELECT ts,device,temp,hum,gas,pir FROM metrics "
                          "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    keys = ["ts", "device", "temp", "hum", "gas", "pir"]
    return [dict(zip(keys, r)) for r in reversed(rows)]


@app.get("/api/v1/status")
def status():
    now = time.time()
    return {dev: {"last_seen": t, "online": now - t < 15} for dev, t in last_seen.items()}


@app.post("/api/v1/commands", dependencies=[Depends(check_key)])
def send_command(cmd: Command):
    if not mqtt_client or not mqtt_client.is_connected():
        raise HTTPException(status_code=503, detail="Broker MQTT indisponible")
    mqtt_client.publish(TOPIC_CMD, json.dumps(cmd.model_dump()), qos=1)
    push({"kind": "command", **cmd.model_dump(), "ts": time.time()})
    return {"sent": cmd.model_dump()}


@app.post("/api/v1/frame", status_code=204, dependencies=[Depends(check_key)])
async def post_frame(request: Request):
    """Le script IA envoie ici la derniere image (JPEG) annotee."""
    global last_frame
    data = await request.body()
    if len(data) > 2_000_000:
        raise HTTPException(status_code=413, detail="Image trop grande")
    last_frame = data


@app.get("/api/v1/frame")
def get_frame():
    if not last_frame:
        raise HTTPException(status_code=404, detail="Pas d'image")
    return Response(content=last_frame, media_type="image/jpeg",
                    headers={"Cache-Control": "no-store"})


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        while True:
            await ws.receive_text()      # garde la connexion ouverte
    except WebSocketDisconnect:
        pass
    finally:
        clients.discard(ws)


# Le dashboard est servi par l'API (doit etre monte en dernier)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
