import appdaemon.plugins.hass.hassapi as hass


class SwitchControl(hass.Hass):
    """
    Generic Scheduled Actions Controller
    """

    def initialize(self):
        self._time = self.args.get("time")
        self._actions = self.args.get("actions", [])

        if not self._time:
            self.error("time not provided in configuration.")
            return

        self.run_daily(self.execute_actions, self._time)

    def execute_actions(self, kwargs):
        for act in self._actions:
            service = act.get("service")
            entity_id = act.get("entity_id")

            if not service or not entity_id:
                self.log(
                    f"Invalid action config: {act}",
                    level="WARNING",
                )
                continue

            self.log(f"Cron executing {service} on {entity_id}")

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
