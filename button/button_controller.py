import json
import hassapi as hass


class ButtonPress(hass.Hass):
    """
    Generic MQTT Button Controller
    """

    def initialize(self):
        self._topic = self.args.get("topic")
        self._actions = self.args.get("actions", {})

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
                self.execute_actions(action_type)
        except json.JSONDecodeError:
            self.log(f"Invalid JSON payload: {payload_raw}", level="WARNING")

    def execute_actions(self, action_type):
        if action_type in self._actions:
            actions = self._actions[action_type]
            if not isinstance(actions, list):
                actions = [actions]

            for act in actions:
                service = act.get("service")
                entity_id = act.get("entity_id")

                if not service or not entity_id:
                    self.log(
                        f"Invalid action config for {action_type}: {act}",
                        level="WARNING",
                    )
                    continue

                self.log(
                    f"Executing {service} on {entity_id} for button action {action_type}"
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
            self.log(f"No actions defined for action_type: {action_type}")
