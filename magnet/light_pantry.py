import json
from typing import Dict

import hassapi as hass


class PantryLight(hass.Hass):
    """
    Turn on lights when door opens, and turn off when closed.
    Includes a safety timeout to turn off the light if left open.
    """

    def initialize(self) -> None:
        self._topic = self.args.get("sensor_topic", "zigbee2mqtt/magnet_pantry_door")
        self._entity = self.args.get("light_entity", "light.pantry_leds")
        self._timeout = int(self.args.get("timeout", 300))

        self.timer_handler = None

        self._mqtt = self.get_plugin_api("MQTT")
        self._mqtt.listen_event(
            self._parse_json,
            "MQTT_MESSAGE",
            topic=self._topic,
        )

        self.log(f"Pantry Light Initialized. Sensor: {self._topic}, Light: {self._entity}, Timeout: {self._timeout}s")

    def _parse_json(self, event: str, data: Dict, unused_kwargs: Dict) -> None:
        try:
            payload = json.loads(data["payload"])
        except (json.JSONDecodeError, TypeError, KeyError):
            return

        if "contact" in payload:
            door_closed = payload["contact"]
            if door_closed:
                self.door_closed()
            else:
                self.door_open()

    def door_open(self) -> None:
        self.log("Pantry door opened")
        if self.timer_handler:
            self.cancel_timer(self.timer_handler)
            self.timer_handler = None

        self.turn_light_on()

        # Schedule the "left open" safety turn-off
        self.timer_handler = self.run_in(self.door_left_open, self._timeout)

    def door_left_open(self, kwargs: dict) -> None:
        self.timer_handler = None
        if self.get_state(self._entity) == "on":
            self.log("Pantry door was left open! Safety turning off light.")
            self.turn_light_off()

    def door_closed(self) -> None:
        self.log("Pantry door closed")
        if self.timer_handler:
            self.cancel_timer(self.timer_handler)
            self.timer_handler = None
        self.turn_light_off()

    def turn_light_on(self) -> None:
        current_state = self.get_state(self._entity)
        if current_state == "off":
            self.log(f"Turning on: {self._entity}")
            self.turn_on(self._entity)

    def turn_light_off(self) -> None:
        current_state = self.get_state(self._entity)
        if current_state == "on":
            self.log(f"Turning off: {self._entity}")
            self.turn_off(self._entity)
