# CubeSat Sim

CubeSat Sim is an educational simulation platform for CubeSat systems. It is designed for learning, prototyping, and testing distributed satellite software architectures. The project simulates the onboard computer (OBC), payload, telemetry, power, attitude control, and communication subsystems, using Python and MQTT for inter-service communication.

## Features
- Modular structure for each CubeSat subsystem
- State machine logic for OBC
- MQTT-based command and telemetry exchange
- Logging and configuration management
- Example scripts for testing and simulation

## Directory Structure

```
cubesat/
├── src/                          # main code for all services
│   ├── obc/                      # On-Board Computer — main brain
│   │   ├── __init__.py
│   │   ├── main.py               # OBC service entry point
│   │   ├── state_machine.py      # transitions logic + states
│   │   └── handlers.py           # command and event handlers
│   │
│   ├── eps/                      # Electrical Power System
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── power_monitor.py      # X728 reading, discharge simulation
│   │
│   ├── adcs/                     # Attitude Determination and Control
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── sensors.py            # Sense HAT orientation logic
│   │
│   ├── payload/                  # camera, science data, etc.
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── camera.py             # photo / timelapse logic
│   │   └── science.py            # "science" data collection
│   │
│   ├── telemetry/                # telemetry aggregator
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── aggregator.py
│   │
│   ├── comm/                     # Communication (WiFi MQTT + LoRa)
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── mqtt_handler.py
│   │   └── lora_handler.py       # serial / LoRa module logic
│   │
│   └── common/                   # shared code used by multiple services
│       ├── __init__.py
│       ├── mqtt_client.py        # paho-mqtt wrapper with reconnect
│       ├── config.py             # settings, constants, topics
│       ├── logging_setup.py
│       └── utils.py              # helpers (json, crc, time, etc.)
│
├── scripts/                      # auxiliary scripts (not services)
│   ├── test_mqtt.py              # simple publisher/subscriber for debugging
│   ├── simulate_low_battery.py   # force battery discharge for tests
│   ├── deploy_antena_sim.py      # DEPLOY simulation
│   └── check_all_services.sh     # check status of all .service
│
├── config/                       # configuration files
│   ├── config.yaml               # main settings (topics, intervals, paths)
│   ├── logging.yaml              # logging config (if using dictConfig)
│   └── secrets.yaml              # mqtt credentials, serial ports (git ignore!)
│
├── systemd/                      # ready-to-use unit files for copying
│   ├── cubesat-obc.service
│   ├── cubesat-eps.service
│   ├── cubesat-adcs.service
│   ├── cubesat-payload.service
│   ├── cubesat-telemetry.service
│   └── cubesat-comm.service
│
├── logs/                         # log files (can be .gitignore)
│   └── (empty, created automatically)
│
├── data/                         # temporary and persistent data
│   ├── photos/                   # saved camera images
│   ├── telemetry_archive/        # archive of json packets (optional)
│   └── lora_packets/             # logs / saved LoRa packets (optional)
│
├── tests/                        # unit tests (pytest)
│   ├── test_state_machine.py
│   ├── test_mqtt.py
│   └── test_eps.py
│
├── .gitignore
├── README.md
├── requirements.txt              # or pyproject.toml / poetry.lock
└── setup.sh                      # initial setup script (apt, pip, copy service)
```

## Getting Started

1. Clone the repository
2. Install dependencies from `requirements.txt`
3. Run individual subsystem services from `src/`
4. Use scripts in `scripts/` for testing and simulation

## License

See LICENSE file for details.

