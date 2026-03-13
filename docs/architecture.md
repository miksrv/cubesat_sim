# Architecture Overview

## System Purpose

CubeSat Sim is a distributed simulation of a CubeSat satellite's onboard software. Each real-world CubeSat subsystem is represented by an independent Python process. The processes run on a Raspberry Pi (or cluster of boards) and communicate exclusively through MQTT, mirroring how physical subsystems communicate over a spacecraft bus.

---

## Runtime Architecture

```
┌───────────────────────────────────────────────────────────┐
│                      MQTT Broker (mosquitto)               │
│                                                           │
│  cubesat/command          cubesat/obc/status (retain)     │
│                           cubesat/eps/status (retain)     │
│                           cubesat/adcs/status             │
│                           cubesat/payload/data            │
│  cubesat/payload/photo    cubesat/telemetry/data          │
└───────┬──────────────────────────────────────────────────-┘
        │ publish/subscribe
  ┌─────┴──────────────────────────────────────────────┐
  │                                                    │
  ▼                                                    ▼
┌──────┐    ┌──────┐    ┌────────┐    ┌─────────┐    ┌───────────┐
│ OBC  │    │ EPS  │    │  ADCS  │    │ Payload │    │ Telemetry │
│      │    │      │    │        │    │         │    │ Aggregator│
│State │    │Power │    │ IMU    │    │ Camera  │    │           │
│Mach. │    │Mon.  │    │ AHRS   │    │ Science │    │ SQLite DB │
└──────┘    └──────┘    └────────┘    └─────────┘    └───────────┘
   │            │            │              │
   │         I2C/GPIO       I2C           I2C / CSI
   │         MAX17048       QMI8658       LPS22HB
   │         X728 UPS       AK09918       SHTC3
   │                                      Picamera2
   └─────────────────────────────────────────────────
              Raspberry Pi Hardware
```

---

## Subsystems

### OBC — On-Board Computer (`src/obc/`)

The central authority of the simulation. Implements a finite state machine using the `transitions` library and is the only service that can change mission state.

**State machine:**
```
        ┌──────────────────────────────────────────┐
        │                                          │ enter_safe_mode (any state)
        ▼                                          │
      BOOT ──auto_deploy──► DEPLOY ──deployment_complete──► NOMINAL
                                                      │         ▲
                                          start_science│         │end_science
                                                      ▼         │
                                                   SCIENCE ──────┘
                                                      │
                                        enter_low_power│(battery <40%)
                                                      ▼
                                                 LOW_POWER
                                                      │
                                           enter_safe_mode (battery <20%)
                                                      ▼
                                                    SAFE
                                                      │
                                            recover ──┘ (external power restored)
```

**State transition rules (from `handlers.py`):**
- Battery < 40% → `LOW_POWER` (if not already `LOW_POWER` or `SAFE`)
- Battery < 20% → `SAFE` (from any state)
- External power restored while in `LOW_POWER`/`SAFE` → `NOMINAL`
- Ground commands on `cubesat/command`: `science_start`, `science_stop`, `safe_mode`, `recover`

**Files:**
| File | Responsibility |
|---|---|
| `main.py` | MQTT setup, main heartbeat loop (30s) |
| `state_machine.py` | `CubeSatStateMachine` — state definitions, transition callbacks, state publishing |
| `handlers.py` | `OBCMessageHandlers` — EPS status reactions, ground command parsing |

---

### EPS — Electrical Power System (`src/eps/`)

Reads hardware power state via I2C (MAX17048 fuel gauge at `0x36`) and GPIO (X728 UPS PLD pin). Publishes JSON status every 30 seconds.

**Published payload (`cubesat/eps/status`):**
```json
{
  "timestamp": 1700000000.0,
  "battery": 87.5,
  "voltage": 4.123,
  "external_power": true
}
```

**Files:**
| File | Responsibility |
|---|---|
| `main.py` | MQTT setup, publish loop |
| `power_monitor.py` | `EPSMonitor` — I2C reads, GPIO reads, status assembly |

---

### ADCS — Attitude Determination and Control (`src/adcs/`)

Reads the IMU sensor and runs a Mahony-style AHRS algorithm to fuse accelerometer, gyroscope, and magnetometer data into roll/pitch/yaw angles. Publishes orientation at 2 Hz.

**Published payload (`cubesat/adcs/status`):**
```json
{
  "timestamp": 1700000000.0,
  "roll": 1.23,
  "pitch": -0.45,
  "yaw": 178.9,
  "imu_temp": 34.5,
  "accel_g": {"x": 0.01, "y": 0.02, "z": 0.99},
  "gyro_dps": {"x": 0.1, "y": -0.2, "z": 0.05}
}
```

**Files:**
| File | Responsibility |
|---|---|
| `main.py` | MQTT setup, publish loop (0.5 s) |
| `common/imu_qmi8658_ak09918.py` | `IMU` — QMI8658 (accel+gyro) and AK09918 (mag) I2C drivers, Mahony AHRS |

---

### Payload (`src/payload/`)

Two responsibilities combined in one service:
1. **Camera**: Takes single photos on demand (via MQTT command), encodes as Base64, publishes on `cubesat/payload/photo`
2. **Science**: Polls LPS22HB (pressure/temperature) and SHTC3 (humidity/temperature) sensors every 60 seconds, publishes on `cubesat/payload/data`

Photo capture and timelapse start are gated: only allowed when OBC is in `NOMINAL` state (tracked by subscribing to `cubesat/obc/status`). Timelapse stop is permitted from any state.

**Files:**
| File | Responsibility |
|---|---|
| `main.py` | MQTT wiring, OBC state tracking, command routing, science poll loop |
| `camera.py` | `PayloadCamera` — Picamera2 integration, timelapse threading |
| `science.py` | `ScienceCollector` — LPS22HB + SHTC3 I2C reads, data averaging |

---

### Telemetry Aggregator (`src/telemetry/`)

Passive aggregator. Subscribes to all subsystem status topics and maintains a cache of the latest values from each. Periodically (when OBC is in `SCIENCE` state) assembles a full telemetry packet and writes it to SQLite. Also responds to on-demand telemetry requests.

**SQLite schema** (`data/telemetry.db`, table `telemetry_log`):
- Timestamps, EPS fields (battery, voltage, external_power)
- ADCS fields (roll, pitch, yaw, imu_temp, accel x/y/z, gyro x/y/z)
- Payload fields (temperature, humidity, pressure)
- System fields (cpu_percent, ram_percent, swap_percent, disk_percent, uptime_seconds, cpu_temperature)
- OBC state, raw JSON blob

**Files:**
| File | Responsibility |
|---|---|
| `main.py` | Entry point, logging setup |
| `aggregator.py` | `TelemetryAggregator` — MQTT subscriptions, data cache, packet builder, SQLite writer, main loop |

---

### Common (`src/common/`)

Shared infrastructure used by all services.

| File | Responsibility |
|---|---|
| `config.py` | All constants: MQTT broker, port, keepalive, all topic strings (`TOPICS` dict), data paths, intervals |
| `mqtt_client.py` | `get_mqtt_client()` factory — creates MQTTv5 client with exponential backoff reconnect |
| `logging_setup.py` | `setup_logging()` — rotating file handler (10 MB × 5) + optional console, writes to `/var/log/cubesat/` |
| `system_metrics.py` | `SystemMetricsCollector` — CPU/RAM/swap/disk/uptime/temperature via `psutil` and sysfs |
| `utils.py` | `crc16_ccitt()`, `json_dumps_pretty()`, `timestamp_iso()`, `ensure_dir()` |
| `imu_qmi8658_ak09918.py` | `IMU` — hardware driver (see ADCS) |

---

## Data Flow: Typical SCIENCE Mode Cycle

```
1. Ground sends:  {"command": "science_start"} → cubesat/command

2. OBC receives command, transitions NOMINAL → SCIENCE
   Publishes: {"timestamp": <unix_float>, "status": "SCIENCE"} → cubesat/obc/status (retain)

3. Payload reads obc_state = "SCIENCE" (no action — science poll is always running)
   Every 60s: collects T/H/P → cubesat/payload/data

4. ADCS: every 500ms: reads IMU → cubesat/adcs/status

5. EPS: every 30s: reads battery/voltage → cubesat/eps/status

6. Telemetry sees obc_state == "SCIENCE":
   Every 30s: builds packet from cached data + system metrics → writes to SQLite
   Also publishes: → cubesat/telemetry/data

7. Ground sends:  {"command": "science_stop"} → cubesat/command
   OBC: SCIENCE → NOMINAL
```

## Data Flow: Photo Request

```
1. Ground sends: {"command": "take_photo", "request_id": "req_001", "params": {"overlay": false}}
   → cubesat/command

2. Payload checks obc_state:
   - If not NOMINAL → publishes error to cubesat/payload/photo
   - If NOMINAL → captures JPEG via Picamera2

3. Photo encoded as Base64:
   Full response (with photo_base64) → cubesat/payload/photo
```

## Data Flow: Timelapse

```
1. Ground sends: {"command": "start_timelapse", "params": {"interval_sec": 60}}
   → cubesat/command
   Payload: OBC must be NOMINAL; starts background thread capturing every interval_sec seconds.

2. Ground sends: {"command": "stop_timelapse"}
   → cubesat/command
   Payload: stops timelapse thread (allowed from any OBC state).
```

---

## Deployment

Services run as systemd units. Unit files are in `systemd/` and are installed by `scripts/install.sh`.

Each unit:
- Sets `PYTHONPATH` to project root (enables `import src.xxx`)
- Runs `python -m src.<module>.main`
- Restarts automatically on failure (`Restart=always`, `RestartSec=10s`)
- Requires `mosquitto.service` to be up first

**Service startup order:** mosquitto → all CubeSat services (parallel, no defined order between them; they reconnect if broker isn't ready)
