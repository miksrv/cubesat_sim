import json
import time
import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1883

# Топики
COMMAND_TOPIC = "cubesat/command"          # команды извне (Telegram)
OBC_TO_PAYLOAD_TOPIC = "cubesat/obc/commands"  # команды, разрешенные OBC для Payload
OBC_STATE_TOPIC = "cubesat/obc/state"

# Начальное состояние спутника
satellite_state = "NOMINAL"

def on_connect(client, userdata, flags, rc):
    print("OBC connected to broker")
    client.subscribe(COMMAND_TOPIC)

def on_message(client, userdata, msg):
    global satellite_state
    command = msg.payload.decode()
    print(f"OBC received command: {command}")

    # Простейшая логика состояния
    if satellite_state in ["LOW_POWER", "SAFE"]:
        print(f"OBC: cannot execute command in {satellite_state} mode")
        return

    # Разрешаем Payload выполнять команду
    if command == "take_photo":
        print("OBC: forwarding 'take_photo' to Payload")
        client.publish(OBC_TO_PAYLOAD_TOPIC, command)

    # Можно добавить другие команды, например start_science, stop_science
    # client.publish(OBC_STATE_TOPIC, satellite_state)

def main():
    client = mqtt.Client("OBC")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.loop_forever()

if __name__ == "__main__":
    main()