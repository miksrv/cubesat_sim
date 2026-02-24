import paho.mqtt.client as mqtt
from pathlib import Path

BROKER = "localhost"
PORT = 1883

# Топики
PAYLOAD_PHOTO_TOPIC = "cubesat/payload/photo"   # подписка на фото от Payload
UPLINK_TOPIC = "cubesat/comm/uplink"           # публикация для Telegram/LoRa

def on_connect(client, userdata, flags, rc):
    print("Comm Service connected to broker")
    client.subscribe(PAYLOAD_PHOTO_TOPIC)

def on_message(client, userdata, msg):
    """Получаем путь к фото и отправляем его в uplink"""
    photo_path = msg.payload.decode()
    photo_file = Path(photo_path)

    if not photo_file.exists():
        print(f"Comm: file not found {photo_file}")
        return

    try:
        with open(photo_file, "rb") as f:
            photo_bytes = f.read()

        # Здесь можно добавить разбиение на пакеты, CRC и packet_id
        client.publish(UPLINK_TOPIC, photo_bytes)
        print(f"Comm: sent photo {photo_file.name} to uplink")

    except Exception as e:
        print(f"Comm: error sending photo: {e}")

def main():
    client = mqtt.Client("CommService")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.loop_forever()

if __name__ == "__main__":
    main()