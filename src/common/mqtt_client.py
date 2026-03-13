import paho.mqtt.client as mqtt
import time
import logging
import random

logger = logging.getLogger(__name__)

def get_mqtt_client(
        client_id: str,
        username: str = None,
        password: str = None,
        reconnect_delay_min: int = 1,
        reconnect_delay_max: int = 120
) -> mqtt.Client:
    """
    Creates an MQTT client with automatic reconnection and exponential backoff.
    on_connect and on_disconnect must be set by the caller after this returns.
    """
    client = mqtt.Client(
        client_id=client_id + "_" + str(random.randint(1000, 9999)),
        protocol=mqtt.MQTTv5,
        userdata={"reconnect_delay_min": reconnect_delay_min, "reconnect_delay_max": reconnect_delay_max}
    )

    if username and password:
        client.username_pw_set(username, password)

    client.reconnect_delay_set(min_delay=reconnect_delay_min, max_delay=reconnect_delay_max)

    return client
