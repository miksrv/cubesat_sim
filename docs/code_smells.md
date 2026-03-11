# Code Smells & Issues

This document catalogs issues found in the current codebase, ordered roughly by severity.

---

## Bugs

### B1 — Signed 16-bit conversion is a no-op (`imu_qmi8658_ak09918.py:85`)

```python
# Current (broken)
for v in (ax, ay, az, gx, gy, gz):
    if v >= 32768: v -= 65536  # 'v' is a loop-local copy — originals unchanged!

return ax, ay, az, gx, gy, gz  # still unsigned
```

The loop variable `v` is a rebinding of the loop target, not a reference to the tuple element. The original variables `ax`, `ay`, `az`, `gx`, `gy`, `gz` are never modified. Raw readings from the IMU that exceed 32767 (i.e., any negative sensor value) are returned as large positive integers, producing garbage orientation data.

---

### B2 — AHRS quaternion state is a class variable, not instance variable (`imu_qmi8658_ak09918.py:116`)

```python
class IMU:
    q0 = 1.0          # class variable!
    q1 = q2 = q3 = 0.0
    exInt = eyInt = ezInt = 0.0
```

These are shared across all instances of `IMU`. The first write to `self.q0` inside `update_ahrs` will create an instance shadow, so in practice with one instance this works. But it's fragile, and it breaks if two `IMU` objects are ever created (e.g. in tests).

---

### B3 — `get_uptime_seconds` returns boot epoch, not uptime (`system_metrics.py:56`)

```python
@staticmethod
def get_uptime_seconds() -> int:
    return int(psutil.boot_time())  # returns Unix timestamp of boot, not seconds since boot!
```

`psutil.boot_time()` returns the system boot time as a Unix timestamp (e.g., `1700000000`). Uptime in seconds is `time.time() - psutil.boot_time()`. The `collect()` method computes this correctly, but the standalone `get_uptime_seconds()` method is wrong.

---

### B4 — `Path` not imported in `utils.py` (`utils.py:34`)

```python
def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)  # NameError: Path is not defined
```

`from pathlib import Path` is missing. The function raises `NameError` at runtime if called.

---

## Design Issues

### D1 — No hardware abstraction layer

Every subsystem directly imports hardware-specific libraries at the top of the module:

- `EPSMonitor` → `import RPi.GPIO as GPIO` (module level)
- `ScienceCollector` → `import lgpio as sbc`
- `IMU` → `from smbus2 import SMBus`
- `PayloadCamera` → `from picamera2 import Picamera2`

**Consequences:**
- The entire service fails to import on any non-Raspberry Pi machine
- Unit testing is impossible without physical hardware
- No simulation mode for CI or development

There are no interface definitions, no dependency injection, and no mock implementations.

---

### D2 — IMU driver misplaced in `common/`

`src/common/imu_qmi8658_ak09918.py` is a hardware driver for a specific IMU chip. It belongs in `src/adcs/` — nothing else uses it, and it has no business being shared infrastructure. The `common/` package is for cross-cutting concerns (MQTT, logging, config).

---

### D3 — Hardcoded user path in `camera.py`

```python
class PayloadCamera:
    PHOTO_DIR = "/home/mik/cubesat-sim/data/photos"  # hardcoded!
```

`config.py` already defines `PHOTOS_DIR = DATA_DIR / "photos"`. The camera ignores it and hardcodes a user-specific absolute path. This breaks on any other machine or user.

---

### D4 — `TelemetryAggregator` violates Single Responsibility

The `TelemetryAggregator` class handles:
1. MQTT connection lifecycle
2. Subscribing to 5 different topics
3. Maintaining a cache of subsystem data
4. Building telemetry packets
5. Calling `psutil` to collect system metrics
6. Managing a SQLite connection
7. Creating database schema
8. Writing rows to the database
9. Running the main loop

This is a classic God Object. Each responsibility should be a separate class.

---

### D5 — Module-level `setup_logging()` in `main.py` files

Each `main.py` calls `setup_logging()` as a side effect of import, before other imports:

```python
# src/obc/main.py
import logging
from src.common import setup_logging

setup_logging(log_level="INFO", log_file="obc.log", console=True)

import time  # ← other imports come AFTER
```

While this ensures logging is configured before anything else logs, it's a fragile pattern. The call at module import time makes the module non-reusable as a library and complicates testing.

---

### D6 — Camera is reinitialised on every photo

```python
def take_photo(self, overlay=False):
    picam2 = self._init_camera()  # start() called here
    request = picam2.capture_request()
    ...
    finally:
        picam2.stop()
        picam2.close()
```

`Picamera2` has a significant startup cost (sensor warm-up, AE/AWB convergence). Initializing and tearing down the camera on every single photo adds seconds of latency and unnecessary hardware wear.

---

### D7 — Mixed I2C libraries in `science.py`

`ScienceCollector` uses two different I2C libraries for different sensors:
- `smbus2` for LPS22HB (pressure sensor)
- `lgpio` for SHTC3 (humidity sensor)

Both sensors are on the same I2C bus. Using a single library would be simpler and more consistent.

---

### D8 — `print()` used for errors instead of `logger` (`science.py:59,67`)

```python
except Exception as e:
    print(f"LPS22HB init error: {e}")  # should be logger.error(...)
```

Errors in `_lps_init` and `_shtc_init` use `print()` instead of the logger. These messages will not appear in log files and will be lost in systemd journal if stdout is not configured.

---

### D9 — Dead code in `mqtt_client.py`

```python
def on_connect(client, userdata, flags, rc, properties=None):
    ...
def on_disconnect(client, userdata, rc, properties=None):
    ...

def get_mqtt_client(...) -> mqtt.Client:
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
```

Every service that uses `get_mqtt_client()` immediately overwrites `client.on_connect` with its own callback. The module-level `on_connect` and `on_disconnect` are set by the factory and then replaced, making them effectively dead code in all services except EPS (which doesn't override `on_connect`).

---

### D10 — No tests exist

`README.md` documents a `tests/` directory with `test_state_machine.py`, `test_mqtt.py`, and `test_eps.py`, but the directory does not exist. There are zero tests in the repository.

---

### D11 — `comm/` module documented but not implemented

The README describes a `comm/` subsystem for WiFi/MQTT and LoRa communication. It does not exist in `src/`. `utils.py` includes a `crc16_ccitt()` function for "LoRa packets" but nothing uses it.

---

### D12 — No config file, only environment variables and hardcoded constants

The README documents `config/config.yaml` and `config/secrets.yaml` as the configuration mechanism. Neither exists. Configuration is split between:
- Hardcoded constants in `src/common/config.py`
- Environment variables (`MQTT_BROKER`, `MQTT_PORT`)
- Hardcoded paths in individual modules (see D3)

---

### D13 — MQTTv5 `reason_code` vs `rc` inconsistency

With MQTTv5, paho-mqtt passes a `ReasonCode` object, not an integer. Services are inconsistent:
- `obc/main.py` and `payload/main.py`: use `rc != 0` (int comparison — may work if paho coerces, but fragile)
- `telemetry/aggregator.py`: uses `reason_code != 0` (more correct naming)

The correct check with MQTTv5 is `reason_code.is_failure` or `reason_code == 0` (paho does support `==` comparison).

---

### D14 — `payload/main.py` has a malformed f-string

```python
self.mqtt_client.publish(
    TOPICS["payload_status"],
    f'{"state": "IDLE", "alive": true, "ts": {time.time()}}',  # invalid f-string
    ...
)
```

The braces `{"state": ...}` are interpreted as a Python dict expression in an f-string, but this is not valid Python inside an f-string without proper escaping. This will either raise a `SyntaxError` or produce unexpected output. Should use `json.dumps(...)`.

---

## Summary Table

| ID | Severity | Category | File |
|---|---|---|---|
| B1 | High | Bug | `common/imu_qmi8658_ak09918.py` |
| B2 | Medium | Bug | `common/imu_qmi8658_ak09918.py` |
| B3 | Medium | Bug | `common/system_metrics.py` |
| B4 | Medium | Bug | `common/utils.py` |
| D1 | High | Design | All hardware modules |
| D2 | Medium | Design | `common/imu_qmi8658_ak09918.py` |
| D3 | Medium | Design | `payload/camera.py` |
| D4 | Medium | Design | `telemetry/aggregator.py` |
| D5 | Low | Design | All `main.py` files |
| D6 | Low | Design | `payload/camera.py` |
| D7 | Low | Design | `payload/science.py` |
| D8 | Low | Design | `payload/science.py` |
| D9 | Low | Design | `common/mqtt_client.py` |
| D10 | High | Missing | — |
| D11 | Low | Missing | — |
| D12 | Medium | Design | `common/config.py` |
| D13 | Low | Design | Multiple `main.py` |
| D14 | High | Bug | `payload/main.py` |
