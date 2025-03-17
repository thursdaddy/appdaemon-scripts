import appdaemon.plugins.hass.hassapi as hass


class SwitchControl(hass.Hass):

    def initialize(self):
        self.run_daily(self.turn_on_all_motion, "04:00:00")

    def turn_on_all_motion(self, kwargs):
        self.turn_on("input_boolean.motion_all")
