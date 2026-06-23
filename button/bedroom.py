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
        self._topic = self.args.get("topic", "zigbee2mqtt/button_bedroom")
        self._debug_mode = self.args.get("debug", False)

        # Mapping actions to entities for cleaner logging and logic
        self._actions = {
            "single": "input_boolean.lights_all",
            "double": "input_boolean.motion_all",
            "hold": "input_boolean.computer_c137",
        }

        # --- Configuration Output (Readable Top-Down) ---
        self.log("============================")
        for action, entity in self._actions.items():
            self.log(f"  {action.capitalize() + ':':<10} Turn off -> {entity}")
        self.log(f"  Topic:         {self._topic}")
        self.log(f"  Debug Mode:    {'ENABLED' if self._debug_mode else 'DISABLED'}")
        self.log("=== Configuration Loaded ===")

        self._mqtt = self.get_plugin_api("MQTT")
        self._mqtt.listen_event(
            self.callback,
            "MQTT_MESSAGE",
            topic=self._topic,
        )

    def debug_log(self, message):
        """Helper to only log if debug is enabled in apps.yaml"""
        if self._debug_mode:
            self.log(f"[DEBUG] {message}")

    def callback(self, event_name, data, kwargs):
        self.debug_log(f"Received MQTT data: {data}")

        try:
            # json is assumed to be available globally
            payload = json.loads(data["payload"])
            action = payload.get("action")

            if not action:
                self.debug_log("No 'action' key found in payload.")
                return

            if action == "single":
                self.press_single()
            elif action == "double":
                self.press_double()
            elif action == "hold":
                self.press_hold()
            else:
                self.debug_log(f"Unhandled action received: {action}")

        except Exception as e:
            self.log(f"[ERR] Failed to parse payload: {e}")

    def press_single(self):
        entity = self._actions["single"]
        self.log(f"Button Action: Single -> Turning off {entity}")
        self.turn_off(entity)

    def press_double(self):
        entity = self._actions["double"]
        self.log(f"Button Action: Double -> Turning off {entity}")
        self.turn_off(entity)

    def press_hold(self):
        entity = self._actions["hold"]
        self.log(f"Button Action: Hold -> Turning off {entity}")
        self.turn_off(entity)
