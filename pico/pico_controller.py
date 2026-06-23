import hassapi as hass


class PicoEvent(hass.Hass):
    """
    Generic Lutron Pico Remote Controller
    """

    def initialize(self):
        self._device_name = self.args.get("device_name")
        self._actions = self.args.get("actions", {})

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
        if button_type in self._actions:
            actions = self._actions[button_type]
            if not isinstance(actions, list):
                actions = [actions]

            for act in actions:
                service = act.get("service")
                entity_id = act.get("entity_id")

                if not service or not entity_id:
                    self.log(
                        f"Invalid action config for {button_type}: {act}",
                        level="WARNING",
                    )
                    continue

                self.log(
                    f"Executing {service} on {entity_id} for button {button_type}"
                )

                if service == "turn_on":
                    self.turn_on(entity_id)
                elif service == "turn_off":
                    self.turn_off(entity_id)
                elif service == "toggle":
                    self.toggle(entity_id)
                elif service == "set_state_on":
                    self.set_state(entity_id, state="on")
                elif service == "set_state_off":
                    self.set_state(entity_id, state="off")
                else:
                    self.call_service(service, entity_id=entity_id)
        else:
            self.log(f"No actions defined for button_type: {button_type}")
