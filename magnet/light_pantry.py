import json
from typing import Dict

import hassapi as hass

_MQTT_PLUGIN_NAMESPACE = "mqtt"


class PantryLight(hass.Hass):
    """
    Turn on LED lights when pantry doors open
    """

    def initialize(self) -> None:
        """
        Magnet: Aqara
        LEDs: TP-Link
        """
        self.timer_handler = None

        self._topic = "zigbee2mqtt/magnet_pantry_door"
        self._entity = "light.pantry_leds"

        self._mqtt = self.get_plugin_api("MQTT")
        self._mqtt.listen_event(
            self._parse_json,
            "MQTT_MESSAGE",
            topic=self._topic,
        )

    def _parse_json(self, event: str, data: Dict, unused_kwargs: Dict) -> None:
        try:
            payload = json.loads(data["payload"])
        except json.JSONDecodeError:
            return

        door = payload["contact"]
        if door:
            self.door_closed()
        else:
            self.door_open()

    def door_open(self) -> None:
        self.log(f"{self._topic} -> Pantry door opened")
        if self.timer_handler:
            self.cancel_timer(self.timer_handler)
        self.turn_light_on()

        self._lock_timer = self.run_in(self.door_left_open, 300)

    def door_left_open(self, kwargs: dict) -> None:  # Corrected signature
        if self.get_state(self._entity) == "on":
            self.log(f"{self._topic} -> You Left the Pantry Door Open!!")
            self.turn_light_off()

    def door_closed(self) -> None:
        self.log(f"{self._topic} -> Pantry door closed")
        if self.timer_handler:
            self.timer_handler = None
        self.turn_light_off()

    def turn_light_on(self) -> None:
        if self.timer_handler:
            self.cancel_timer(self.timer_handler)
        current_state = self.get_state(self._entity)
        if current_state == "off":
            self.log(f"{self._topic} -> Turning on: {self._entity}")
            self.turn_on(self._entity)

    def turn_light_off(self) -> None:
        if self.timer_handler:
            self.timer_handler = None
        current_state = self.get_state(self._entity)
        if current_state == "on":
            self.log(f"{self._topic} -> Turning off: {self._entity}")
            self.turn_off(self._entity)
