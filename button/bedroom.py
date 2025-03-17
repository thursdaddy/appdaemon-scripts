import json

import hassapi as hass


class ButtonPress(hass.Hass):
    """
    Bedroom Button Control
    """

    def initialize(self):
        """
        Button: Aqara Button
        """
        # Set in apps.yml
        self._topic = "zigbee2mqtt/button_bedroom"

        self._mqtt = self.get_plugin_api("MQTT")
        self._mqtt.listen_event(
            self.callback,
            "MQTT_MESSAGE",
            topic=self._topic,
        )

    def callback(self, event_name, data, kwargs):
        try:
            payload = json.loads(data["payload"])
            if payload["action"] == "single":
                self.press_single()
            if payload["action"] == "double":
                self.press_double()
        except json.JSONDecodeError:
            return

    def press_single(self):
        self.log(f"{self._topic} -> Turn off All Lights")
        for entity in self._entities:
            self.turn_off("input_boolean.lights_all")

    def press_double(self):
        self.log(f"{self._topic} -> Turn on Espresso")
        self.turn_on("switch.kitchen_espresso")
