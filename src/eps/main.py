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
        self.monitor = EPSMonitor(use_gpio=True)  # можно False для теста без GPIO

    def publish_status(self):
        status = self.monitor.get_status()
        logger.info(f"EPS статус: {status}")

        self.mqtt_client.publish(
            TOPICS["eps_status"],
            json.dumps(status),
            qos=1,
            retain=True  # чтобы всегда был последний статус
        )

    def run(self):
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=MQTT_KEEPALIVE)
        self.mqtt_client.loop_start()

        logger.info("EPS сервис запущен")

        try:
            while True:
                self.publish_status()
                time.sleep(30)  # обновление каждые 30 секунд — можно уменьшить до 10–15
        except KeyboardInterrupt:
            logger.info("Остановка EPS сервиса")
        except Exception as e:
            logger.exception("Критическая ошибка в главном цикле EPS")
        finally:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            logger.info("EPS сервис завершил работу")

if __name__ == "__main__":
    service = EPSService()
    service.run()