import json
from base_controller import BaseController


class ButtonPress(BaseController):
    """
    Generic MQTT Button Controller
    """

    def initialize(self):
        self._topic = self.args.get("topic")
        raw_actions = self.args.get("actions", {})

        # Normalize keys to strings to handle YAML parsing of on/off/yes/no as booleans
        self._actions = {}
        for key, val in raw_actions.items():
            if isinstance(key, bool):
                str_key = "on" if key else "off"
            else:
                str_key = str(key).lower()
            self._actions[str_key] = val

        if not self._topic:
            self.error("topic not provided in configuration.")
            return

        self._mqtt = self.get_plugin_api("MQTT")
        self._mqtt.listen_event(
            self.callback,
            "MQTT_MESSAGE",
            topic=self._topic,
        )

    def callback(self, event_name, data, kwargs):
        payload_raw = data.get("payload")
        if not payload_raw:
            return

        try:
            payload = json.loads(payload_raw)
            action_type = payload.get("action")
            
            if action_type:
                self.execute_button_actions(action_type)
        except json.JSONDecodeError:
            self.log(f"Invalid JSON payload: {payload_raw}", level="WARNING")

    def execute_button_actions(self, action_type):
        normalized_action = str(action_type).lower()
        if normalized_action in self._actions:
            self.log(f"Button action triggered: {normalized_action}")
            super().execute_actions(self._actions[normalized_action])
        else:
            self.log(f"No actions defined for action_type: {normalized_action}")
