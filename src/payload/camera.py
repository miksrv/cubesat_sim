from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput
import time
import os
import logging
from threading import Thread, Event
from libcamera import Transform

logger = logging.getLogger(__name__)

class PayloadCamera:
    PHOTO_DIR = "/home/mik/cubesat-sim/data/photos"  # or from config
    def __init__(self):
        os.makedirs(self.PHOTO_DIR, exist_ok=True)
        self.timelapse_running = False
        self.timelapse_thread = None
        self.stop_event = Event()

    def _init_camera(self):
        picam2 = Picamera2()
        config = picam2.create_still_configuration(
            main={"size": (1920, 1080)},  # or (4056, 3040) for full resolution
            lores={"size": (640, 480), "format": "YUV420"},
            transform=Transform(hflip=1, vflip=1)
        )
        picam2.configure(config)
        picam2.start()
        return picam2

    def take_photo(self, overlay=False):
        """Takes a single photo and returns the file path"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"photo_{timestamp}.jpg"
        path = os.path.join(self.PHOTO_DIR, filename)
        picam2 = None
        try:
            picam2 = self._init_camera()
            request = picam2.capture_request()
            request.save("main", path)
            request.release()

            logger.info(f"Photo saved: {path}")

            # If overlay=True — add logic here (see previous answer)
            # For now, just return the path
            return path

        except Exception as e:
            logger.error(f"Photo capture error: {e}")
            return None
        finally:
            if picam2:
                picam2.stop()
                picam2.close()

    def start_timelapse(self, interval_sec=60):
        if self.timelapse_running:
            logger.warning("Timelapse is already running")
            return

        self.timelapse_running = True
        self.stop_event.clear()
        self.timelapse_thread = Thread(target=self._timelapse_loop, args=(interval_sec,))
        self.timelapse_thread.daemon = True
        self.timelapse_thread.start()
        logger.info(f"Timelapse started with interval {interval_sec} sec")

    def _timelapse_loop(self, interval):
        while not self.stop_event.is_set():
            self.take_photo()  # you can add overlay
            time.sleep(interval)

    def stop_timelapse(self):
        if not self.timelapse_running:
            return
        self.stop_event.set()
        if self.timelapse_thread:
            self.timelapse_thread.join(timeout=5)
        self.timelapse_running = False
        logger.info("Timelapse stopped")

    def cleanup(self):
        self.stop_timelapse()
        logger.info("Camera stopped")
