import logging
from src.common import setup_logging

setup_logging(
    log_level = "INFO",
    log_file  = "eps.log",
    console   = True
)

import time
import json
from src.common import get_mqtt_client
from src.common.config import TOPICS, MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE
from src.eps.power_monitor import EPSMonitor

logger = logging.getLogger(__name__)

class EPSService:
    def __init__(self):
        self.mqtt_client = get_mqtt_client("cubesat-eps")
        self.monitor = EPSMonitor()  # can be False for testing without GPIO

    def publish_status(self):
        status = self.monitor.get_status()
        logger.info(f"EPS status: {status}")

        self.mqtt_client.publish(
            TOPICS["eps_status"],
            json.dumps(status),
            qos=1,
            retain=True  # always keep the latest status
        )

    def run(self):
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=MQTT_KEEPALIVE)
        self.mqtt_client.loop_start()

        logger.info("EPS service started")

        try:
            while True:
                self.publish_status()
                time.sleep(30)  # update every 30 seconds — can be reduced to 10–15
        except KeyboardInterrupt:
            logger.info("Stopping EPS service")
        except Exception as e:
            logger.exception("Critical error in main EPS loop")
        finally:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            logger.info("EPS service stopped")

if __name__ == "__main__":
    service = EPSService()
    service.run()