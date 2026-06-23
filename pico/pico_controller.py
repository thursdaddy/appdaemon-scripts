from base_controller import BaseController


class PicoEvent(BaseController):
    """
    Generic Lutron Pico Remote Controller
    """

    def initialize(self):
        self._device_name = self.args.get("device_name")
        raw_actions = self.args.get("actions", {})

        # Normalize keys to strings to handle YAML parsing of on/off/yes/no as booleans
        self._actions = {}
        for key, val in raw_actions.items():
            if isinstance(key, bool):
                str_key = "on" if key else "off"
            else:
                str_key = str(key).lower()
            self._actions[str_key] = val

        if not self._device_name:
            self.error("device_name not provided in configuration.")
            return

        self._hass = self.get_plugin_api("HASS")
        self.listen_event(self.callback, "lutron_caseta_button_event")

    def callback(self, event, data, kwargs):
        if data.get("device_name") != self._device_name:
            return

        if data.get("action") == "release":
            return

        button_type = data.get("button_type")
        action_type = data.get("action")

        if action_type == "press":
            self.execute_actions(button_type)

    def execute_actions(self, button_type):
        normalized_button = str(button_type).lower()
        if normalized_button in self._actions:
            self.log(f"Pico remote button pressed: {normalized_button}")
            super().execute_actions(self._actions[normalized_button])
        else:
            self.log(f"No actions defined for button_type: {normalized_button}")
