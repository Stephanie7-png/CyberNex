import paho.mqtt.client as mqtt

REMOTE_BROKER = "broker.hivemq.com"
REMOTE_PORT = 1883

LOCAL_BROKER = "mosquitto"
LOCAL_PORT = 1883

TOPIC_SENSORS = "cybernex/sensors"
TOPIC_COMMANDS = "cybernex/cmd"


# =========================================================
# CLIENT LOCAL : Mosquitto
# =========================================================

local_client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="cybernex-local-client"
)


def on_local_connect(client, userdata, flags, reason_code, properties):
    print("Connecte a Mosquitto local :", reason_code)

    client.subscribe(TOPIC_COMMANDS)

    print("Ecoute commandes locales :", TOPIC_COMMANDS)


def on_local_message(client, userdata, message):

    payload = message.payload.decode()

    print("Mosquitto local -> commande :", payload)

    remote_client.publish(
        TOPIC_COMMANDS,
        payload,
        qos=1
    )

    print("Commande envoyee vers HiveMQ")


local_client.on_connect = on_local_connect
local_client.on_message = on_local_message


# =========================================================
# CLIENT DISTANT : HiveMQ
# =========================================================

remote_client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="cybernex-remote-client"
)


def on_remote_connect(client, userdata, flags, reason_code, properties):

    print("Connecte a HiveMQ :", reason_code)

    client.subscribe(TOPIC_SENSORS)

    print("Ecoute capteurs :", TOPIC_SENSORS)


def on_remote_message(client, userdata, message):

    payload = message.payload.decode()

    print("HiveMQ -> capteurs :", payload)

    local_client.publish(
        TOPIC_SENSORS,
        payload
    )

    print("Capteurs republies vers Mosquitto local")


remote_client.on_connect = on_remote_connect
remote_client.on_message = on_remote_message


# =========================================================
# CONNEXIONS
# =========================================================

local_client.connect(
    LOCAL_BROKER,
    LOCAL_PORT,
    60
)

remote_client.connect(
    REMOTE_BROKER,
    REMOTE_PORT,
    60
)


local_client.loop_start()

remote_client.loop_forever()