# src/payload/science.py
import logging
# from sense_hat import SenseHat  # если используешь Sense HAT

logger = logging.getLogger(__name__)

class ScienceCollector:
    def __init__(self):
        # self.sense = SenseHat()  # если подключён
        pass

    def collect_data(self):
        """Собирает 'научные' данные — температура, влажность и т.д."""
        data = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            # "temperature": self.sense.get_temperature() if hasattr(self, 'sense') else 22.5,
            # "humidity": self.sense.get_humidity() if hasattr(self, 'sense') else 45.0,
            "temperature": 23.7,  # заглушка
            "humidity": 52.1,
        }
        logger.debug(f"Собраны научные данные: {data}")
        return data

    # Можно добавить публикацию в MQTT периодически или по запросу