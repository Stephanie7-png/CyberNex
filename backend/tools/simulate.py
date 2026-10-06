"""Simule l'ESP8266 (telemetrie MQTT) + une alerte de temps en temps.
Usage : pip install paho-mqtt ; python tools/simulate.py [cle_api]"""
import json, math, random, sys, time, urllib.request
import paho.mqtt.client as mqtt

KEY = sys.argv[1] if len(sys.argv) > 1 else ""
c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
c.connect("localhost", 1883)
c.loop_start()
t = 0
while True:
    t += 1
    d = {"device": "esp-01",
         "temp": round(22 + 3 * math.sin(t / 15) + random.random(), 1),
         "hum": round(45 + 5 * math.cos(t / 20) + random.random(), 1),
         "gas": round(200 + 40 * random.random() + (250 if t % 40 > 34 else 0)),
         "pir": int(random.random() > 0.9)}
    c.publish("sentinel/telemetry", json.dumps(d))
    if d["gas"] > 400:
        body = json.dumps({"device": "esp-01", "type": "gas", "level": "critical",
                           "value": d["gas"], "message": "Fuite de gaz suspectee"}).encode()
        req = urllib.request.Request("http://localhost:8000/api/v1/alerts", body,
                                     {"Content-Type": "application/json", "X-API-Key": KEY})
        urllib.request.urlopen(req)
    time.sleep(2)
