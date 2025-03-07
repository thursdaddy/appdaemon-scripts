import appdaemon.plugins.hass.hassapi as hass


class EspressoSwitchOff(hass.Hass):

    def initialize(self):
        self.run_daily(self.turn_off_switch, "12:00:00")

    def turn_off_switch(self, kwargs):
        self.turn_off("switch.kitchen_espesso")
