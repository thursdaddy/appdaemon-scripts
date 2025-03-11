import json
from typing import Dict

import hassapi as hass

_MQTT_PLUGIN_NAMESPACE = "mqtt"


class ButtonPress(hass.Hass):
    """
    Bedroom Button Control
    """

    def initialize(self) -> None:
        """
        Button: Aqara Button
        """
        # Set in apps.yml
        self._topic = "zigbee2mqtt/button_bedroom"
        self._entities = [
            "light.printer_upper",
            "light.printer_lower",
            "light.upstairs_light_1",
            "light.upstairs_light_2",
            "light.office_desk",
            "switch.living_room_tv_lights",
            "switch.sim_desk_light",
        ]

        self._mqtt = self.get_plugin_api("MQTT")
        self._mqtt.listen_event(
            self._parse_json,
            "MQTT_MESSAGE",
            topic=self._topic,
        )

    def _parse_json(self, event: str, data: Dict, unused_kwargs: Dict) -> None:
        try:
            payload = json.loads(data["payload"])
            if payload["action"] == "single":
                self.press_single()
            if payload["action"] == "double":
                self.press_double()
        except json.JSONDecodeError:
            return

    def press_single(self) -> None:
        self.log(f"{self._topic} -> Turn off All Lights")
        for entity in self._entities:
            self.turn_off(entity)

    def press_double(self) -> None:
        self.log(f"{self._topic} -> Turn on Espresso")
        self.turn_on("switch.kitchen_espresso")
