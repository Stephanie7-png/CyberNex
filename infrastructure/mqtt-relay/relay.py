import paho.mqtt.client as mqtt

REMOTE_BROKER = "broker.hivemq.com"
REMOTE_PORT = 1883

LOCAL_BROKER = "mosquitto"
LOCAL_PORT = 1883

TOPIC = "cybernex/sensors"

local_client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="cybernex-local-publisher"
)

local_client.connect(
    LOCAL_BROKER,
    LOCAL_PORT,
    60
)

local_client.loop_start()


def on_connect(client, userdata, flags, reason_code, properties):
    print("Connecte a HiveMQ :", reason_code)

    client.subscribe(TOPIC)

    print("Abonne a :", TOPIC)


def on_message(client, userdata, message):

    payload = message.payload.decode()

    print("HiveMQ ->", payload)

    local_client.publish(
        TOPIC,
        payload
    )

    print("Republie vers Mosquitto local")


remote_client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="cybernex-wokwi-relay"
)

remote_client.on_connect = on_connect
remote_client.on_message = on_message

remote_client.connect(
    REMOTE_BROKER,
    REMOTE_PORT,
    60
)

remote_client.loop_forever()