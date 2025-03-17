import appdaemon.plugins.hass.hassapi as hass


class BooleanControlLights(hass.Hass):

    def initialize(self):
        self._boolean = self.args.get("boolean")
        self._entities = self.args.get("entities")

        self.listen_state(self.callback, self._boolean)

    def callback(self, entity, attribute, old, new, kwargs):
        if new == "off":
            self.turn_off_all_lights()
            self.turn_on(self._boolean)  # no-op

    def turn_off_all_lights(self):
        self.log("Running lights off")
        for entity in self._entities:
            self.log(f"turning off {entity}")
            self.turn_off(entity)


class BooleanControlMotion(hass.Hass):

    def initialize(self):
        self._boolean = self.args.get("boolean")
        self._entities = self.args.get("entities")

        self.listen_state(self.callback, self._boolean)

    def callback(self, entity, attribute, old, new, kwargs):
        if new == "on":
            self.turn_on_motion_automations()
        if new == "off":
            self.turn_off_motion_automations()

    def turn_on_motion_automations(self):
        self.log("running on")
        for switch in self._motion_control_booleans:
            self.log(f"Turning on {switch}".replace("input_boolean.", ""))
            self.turn_on(switch)

    def turn_off_motion_automations(self):
        self.log("running off")
        for switch in self._motion_control_booleans:
            self.log(f"Turning off {switch}".replace("input_boolean.", ""))
            self.turn_off(switch)
