import xml.etree.ElementTree as ET

import appdaemon.plugins.hass.hassapi as hass
import requests


class ComputerStateMonitor(hass.Hass):

    def initialize(self):
        self._ip = self.args.get("ip")
        self._boolean = self.args.get("boolean")
        self._threshold = 2
        self._count = 0
        self._last_detected_state = None

        self.run_every(self.check_computer, "now", 20)
        self.log(f"Monitor started. Target: {self._ip}, Boolean: {self._boolean}")

    def check_computer(self, kwargs):
        current_real_state = None

        try:
            # Replaced 127.0.0.1 with self._ip for flexibility
            response = requests.get(f"http://{self._ip}:8009/state/local", timeout=5)
            root = ET.fromstring(response.text)
            state_text = root.find("state").text
            current_real_state = "on" if state_text == "online" else "off"
        except Exception:
            current_real_state = "off"

        self.process_state_logic(current_real_state)

    def process_state_logic(self, detected_state):
        if detected_state == self._last_detected_state:
            self._count += 1
        else:
            # Only log the "Observation" if it's different from the last time
            self.log(f"Observation: PC looks {detected_state.upper()}. Verifying...")
            self._count = 1
            self._last_detected_state = detected_state

        if self._count >= self._threshold:
            current_ha_state = self.get_state(self._boolean)

            # Update HA only if there is a mismatch
            if detected_state == "on" and current_ha_state == "off":
                self.log(f"Confidence High: PC is ONLINE. Syncing {self._boolean} to ON.")
                self.turn_on(self._boolean)

            elif detected_state == "off" and current_ha_state == "on":
                self.log(f"Confidence High: PC is OFFLINE. Syncing {self._boolean} to OFF.")
                self.turn_off(self._boolean)
