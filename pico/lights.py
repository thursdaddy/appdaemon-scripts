import hassapi as hass


class PicoOffice(hass.Hass):
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
        if data["device_name"] != "office":
            self.log("not office, bye")
            return
        if data["action"] == "release":
            return
        if data["button_type"] == "on" and data["action"] == "press":
            self.on_pressed(data, kwargs)
        elif data["button_type"] == "off" and data["action"] == "press":
            self.off_pressed(data, kwargs)
        elif data["button_type"] == "stop" and data["action"] == "press":
            self.stop_pressed(data, kwargs)

    def on_pressed(self, data, kwargs):
        for entity in self._entities:
            self.turn_on(entity)

    def off_pressed(self, data, kwargs):
        for entity in self._entities:
            self.turn_off(entity)

    def stop_pressed(self, data, kwargs):
        self.toggle(self._motion_sensor)
        state = self.get_state(self._motion_sensor)
        self.log(f"Toggle motion control to {state}")

    def blink_twice(self, data, kwargs):
        self.log("blinking")


class PicoLivingRoom(hass.Hass):
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
        if data["device_name"] != "livingroom":
            self.log("not livingroom, bye")
            return
        if data["action"] == "release":
            return
        if data["button_type"] == "on" and data["action"] == "press":
            self.on_pressed(data, kwargs)
        elif data["button_type"] == "off" and data["action"] == "press":
            self.off_pressed(data, kwargs)
        elif data["button_type"] == "stop" and data["action"] == "press":
            self.on_pressed(data, kwargs)

    def on_pressed(self, data, kwargs):
        self.log(self._entities)
        for entity in self._entities:
            state = self.get_state(entity)
            self.log(state)

    def off_pressed(self, data, kwargs):
        for entity in self._entities:
            self.turn_off(entity)

    def stop_pressed(self, data, kwargs):
        self.log("Turning off")
        self.log(self._entities)
        self.set_state(self._motion_sensor, state="on")
        for entity in self._entities:
            state = self.get_state(entity)
        self.log(state)

    def blink_twice(self, data, kwargs):
        self.log("blinking")
