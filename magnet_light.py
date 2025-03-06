import json
from typing import Dict

import hassapi as hass

_MQTT_PLUGIN_NAMESPACE = "mqtt"


class MotionDetectLight(hass.Hass):
    """
    Turn on lights when doors open
    """

    def initialize(self) -> None:
        """
        Magnet: Aqara
        """
        # Set in apps.yml
        self._entities = self.args["lights"]
        self._topic = self.args["topic"]

        # Store timers per light
        self.timer_handlers: Dict[str, hass.timer_handle_type] = {}
        for entity in self._entities:
            self.timer_handlers[entity] = None

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

        occupancy = payload["occupancy"]
        if occupancy:
            self.occupancy_detected()
        else:
            self.occupancy_cleared()

    def occupancy_detected(self) -> None:
        self.log(f"{self._topic} -> Occupancy detected")
        for entity in self._entities:
            if self.timer_handlers[entity]:
                self.cancel_timer(self.timer_handlers[entity])
                self.timer_handlers[entity] = None
            self.turn_light_on(entity)

    def occupancy_cleared(self) -> None:
        self.log(f"{self._topic} -> Occupancy cleared")
        for entity in self._entities:
            if self.timer_handlers[entity]:
                self.cancel_timer(self.timer_handlers[entity])
            self.timer_handlers[entity] = self.run_in(
                self.turn_light_off, self._delay, entity=entity
            )

    def turn_light_on(self, entity: str) -> None:
        if self.timer_handlers[entity]:
            self.cancel_timer(self.timer_handlers[entity])
        current_state = self.get_state(entity)
        if current_state == "off":
            self.log(f"{self._topic} -> Turning on: {entity}")
            self.turn_on(entity)

    def turn_light_off(self, kwargs) -> None:
        entity = kwargs["entity"]
        self.timer_handlers[entity] = None
        current_state = self.get_state(entity)
        if current_state == "on":
            self.log(f"{self._topic} -> Turning off: {entity}")
            self.turn_off(entity)
