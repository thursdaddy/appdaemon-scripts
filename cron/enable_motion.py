import appdaemon.plugins.hass.hassapi as hass


class SwitchControl(hass.Hass):

    def initialize(self):
        self.run_daily(self.turn_on_all_motion, "04:00:00")

    def turn_on_all_motion(self, kwargs):
        self.log("turning OFF all motions")
        self.turn_off("input_boolean.motion_all")
        self.log("turning ON all motions")
        self.turn_on("input_boolean.motion_all")
