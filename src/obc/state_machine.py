from transitions import Machine
import logging
import json
import time
from src.common import TOPICS

logger = logging.getLogger(__name__)

class CubeSatStateMachine:
    """CubeSat On-Board Computer (OBC) state machine"""

    states = [
        'BOOT',       # Initialization after power-on
        'DEPLOY',     # Deployment (antenna, calibration)
        'NOMINAL',    # Nominal mode
        'SCIENCE',    # Science mode (intensive payload operation)
        'LOW_POWER',  # Power saving
        'SAFE'        # Emergency minimal mode
    ]

    transitions = [
        # Automatic transition after successful boot
        {'trigger': 'auto_deploy', 'source': 'BOOT', 'dest': 'DEPLOY'},

        # Successful deployment → nominal mode
        {'trigger': 'deployment_complete', 'source': 'DEPLOY', 'dest': 'NOMINAL'},

        # Commands / normal transitions
        {'trigger': 'start_science', 'source': 'NOMINAL', 'dest': 'SCIENCE'},
        {'trigger': 'end_science',   'source': 'SCIENCE', 'dest': 'NOMINAL'},

        # Power-related transitions (usually triggered by EPS)
        {'trigger': 'enter_low_power', 'source': ['NOMINAL', 'SCIENCE', 'DEPLOY'], 'dest': 'LOW_POWER'},
        {'trigger': 'enter_safe_mode', 'source': '*', 'dest': 'SAFE'},

        # Recovery
        {'trigger': 'recover', 'source': ['LOW_POWER', 'SAFE'], 'dest': 'NOMINAL'},
    ]

    def __init__(self, obc):
        self.obc = obc  # ссылка на родительский OBC для вызова методов
        self.machine = Machine(
            model=self,
            states=CubeSatStateMachine.states,
            transitions=CubeSatStateMachine.transitions,
            initial='BOOT'
        )

        self.on_enter_BOOT()

    # ────────────── State entry callbacks ──────────────
    def on_enter_BOOT(self):
        logger.info("OBC → BOOT: starting self-test...")
        self.publish_state({"step": "self_test_started"})
        # Hardware checks can be added here
        # After tests:
        self.auto_deploy()

    def on_enter_DEPLOY(self):
        logger.info("OBC → DEPLOY: deploying systems...")
        self.publish_state({"step": "antenna_deploying"})
        # Simulation: 5–15 seconds
        # In reality: antenna deployment, ADCS calibration, etc.
        # After completion:
        self.deployment_complete()

    def on_enter_NOMINAL(self):
        logger.info("OBC → NOMINAL: nominal mode")
        self.publish_state()
        # self.obc.publish_control("telegram/start", "")   # if needed
        # self.obc.publish_control("wifi/on", "")
        # self.obc.publish_control("payload/on", "")

    def on_enter_SCIENCE(self):
        logger.info("OBC → SCIENCE: science mode")
        self.publish_state()

    def on_enter_LOW_POWER(self):
        logger.warning("OBC → LOW_POWER: power saving mode")
        self.publish_state()
        # self.obc.publish_control("telegram/stop", "")
        # self.obc.publish_control("wifi/off", "")
        # self.obc.publish_control("payload/off", "")
        # self.obc.publish_control("adcs/reduce_frequency", "60")  # example

    def on_enter_SAFE(self):
        logger.critical("OBC → SAFE: emergency mode!")
        self.publish_state()
        # self.obc.publish_control("all/non_critical/off", "")
        # Only EPS and rare telemetry remain active

    def publish_state(self, extra=None):
        """
        Publishes the current state to MQTT.
        Format: {"timestamp": <unix_float>, "status": <state>, ...extra}
        Silently skips if MQTT is not yet connected (e.g. during boot sequence).
        """
        if not self.obc._mqtt_connected:
            logger.debug(f"MQTT not connected; state publish skipped (state={self.state})")
            return
        payload = {"timestamp": time.time(), "status": self.state}
        if extra:
            payload.update(extra)
        self.obc.mqtt_client.publish(
            TOPICS["obc_status"],
            json.dumps(payload),
            retain=True
        )
