import hassapi as hass


class PicoEvent(hass.Hass):
    """
    Lutron Pico Remote Controls
    """

    def initialize(self):
        """
        Pico Button Events
        """
        # Set in apps.yml
        self._pico = self.args.get("pico")
        self._entities = self.args.get("entities")
        self._motion_sensor = "input_boolean.motion_office"

        self._hass = self.get_plugin_api("HASS")
        self.listen_event(self.callback, "lutron_caseta_button_event")

    def callback(self, event, data, kwargs):
        if data["device_name"] != "sim":
            self.log("not sim, bye")
            return
        if data["action"] == "release":
            return
        if data["button_type"] == "on" and data["action"] == "press":
            self.on_pressed(data, kwargs)
        elif data["button_type"] == "off" and data["action"] == "press":
            self.off_pressed(data, kwargs)
        elif data["button_type"] == "lower" and data["action"] == "press":
            self.lower_pressed(data, kwargs)
        elif data["button_type"] == "raise" and data["action"] == "press":
            self.raised_pressed(data, kwargs)

    def on_pressed(self, data, kwargs):
        self.log("Turning on")
        self.turn_on("input_boolean.activity_sim")

    def off_pressed(self, data, kwargs):
        self.log("Turning off")
        self.turn_off("input_boolean.activity_sim")

    def lower_pressed(self, data, kwargs):
        self.log("Toggle sim fan")
        self.toggle("switch.sim_fan")

    def raised_pressed(self, data, kwargs):
        self.log("Toggle sim spotlight")
        self.toggle("switch.sim_spotlight")
