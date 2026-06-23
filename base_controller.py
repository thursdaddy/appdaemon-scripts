import appdaemon.plugins.hass.hassapi as hass


class BaseController(hass.Hass):
    """
    Base controller providing generic action execution helper methods.
    """

    def execute_action(self, action):
        if not action or not isinstance(action, dict):
            self.log(f"Invalid action config: {action}", level="WARNING")
            return

        service = action.get("service")
        entity_id = action.get("entity_id")

        if not service or not entity_id:
            self.log(
                f"Missing service or entity_id in action: {action}",
                level="WARNING",
            )
            return

        self.log(f"Executing {service} on {entity_id}")

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
            # Pass any extra arguments in action
            kwargs = {
                k: v for k, v in action.items() if k not in ["service", "entity_id"]
            }
            self.call_service(service, entity_id=entity_id, **kwargs)

    def execute_actions(self, actions):
        if not actions:
            return
        if not isinstance(actions, list):
            actions = [actions]
        for action in actions:
            self.execute_action(action)
