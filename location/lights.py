import hassapi as hass


class LocationChange(hass.Hass):
    """
    Lock and Unlock Doors via Location + Camera
    """

    def initialize(self) -> None:
        self.hass_api = self.get_plugin_api("HASS")

        self._lights = self.args.get("lights")
        self._location_entity = "device_tracker.pixel_7_pro"
        self._brightness = self.args.get("brightness", 50)
        self._schedule = self.args.get("schedule")

        # self.listen_state(self.location_update, "input_boolean.test_boolean")
        self.listen_state(self.location_update, self._location_entity)

    def location_update(self, entity, attribute, old, new, kwargs):
        self.config = self.get_config()

        if new == "home" and old != "home":
            # if new == "on" and old != "on":
            self.log("Home Location Detected")

            if self.config is not None:
                self.log("Not scheduled, bye.")
                self.set_lights_to_home()

            self.call_service(
                "notify/gotify",
                title="I AM HOME",
                message="Commence Automations",
                data={
                    "extras": {
                        "client::display": {"contentType": "text/plain"},
                        "client::notification": {
                            "click": {"url": "https://home.thurs.pw/dashboard-home/0"}
                        },
                    },
                    "priority": 5,
                },
            )

        elif new == "away" and old != "away":
            # elif new == "off" and old != "off":
            self.log("Detected Away..")
            self.set_lights_to_away()

    def set_lights_to_away(self):
        self.log("Away lights")
        self.turn_off("input_boolean.lights_all")

    def set_lights_to_home(self):
        self.log("Home lights")
        self.log(self.config)
        for light in self.config["lights"]:
            self.turn_on(light)

    def get_config(self):
        for name, config in self._schedule.items():
            config["name"] = name
            if "lights" not in config:
                config["lights"] = self._lights
            if "brightness" not in config:
                config["brightness"] = self._brightness
            config["brightness_adjusted"] = self.convert_brightness_value(
                value=config["brightness"]
            )

            if self.now_is_between(config["start"], config["end"]):
                return config

    # represent brightness value as
    # percentage between 1-100, translate to values 3-255
    def convert_brightness_value(self, value):
        value = (value - 1) / 99
        value_adjusted = int(round(value * (255 - 3) + 3))
        return value_adjusted
