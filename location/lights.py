import hassapi as hass


class LocationChange(hass.Hass):
    """
    Lock and Unlock Doors via Location + Camera
    """

    def initialize(self) -> None:
        self.hass_api = self.get_plugin_api("HASS")

        self._lights = self.args.get("lights")
        self._location_entity = "device_tracker.pixel_7_pro"
        self._brightness = self.args.get("brightness", 100)
        self._schedule = self.args.get("schedule")

        self.listen_state(self.location_update, "input_boolean.test_boolean")
        self.listen_state(self.location_update, self._location_entity)

    def location_update(self, entity, attribute, old, new, kwargs):
        # if new == "home" and old != "home":
        self.config = self.get_config()

        if new == "on" and old != "on":
            self.log("Home Location Detected")
            self.set_lights_to_home()

        # elif new == "away" and old != "away":
        elif new == "off" and old != "off":
            self.log("Detected Away..")
            self.set_lights_to_away()

    def set_lights_to_away(self):
        self.log(self.config)
        for light in self.config:
            self.log("away lights")
            self.log(light)

    def set_lights_to_home(self):
        self.log(self.config)
        for light in self.config:
            self.log("home lights")
            self.log(light)

    def get_config(self):
        for name, config in self._schedule.items():
            config["name"] = name
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

    # def end_home_window(self, kwargs):
    #     self._home_window_active = False
    #     self.log("Home window ended")
    #
    # def person_detected(self, entity, attribute, old, new, kwargs):
    #     if new == "on":
    #         self.log("Person Detected")
    #         self._person_detected_flag = True
    #         self.check_unlock_conditions()
    #     else:
    #         self._person_detected_flag = False
    #
    # def check_unlock_conditions(self):
    #     self.log("checking unlock conditions")
    #     self.log(self._person_detected_flag)
    #     self.log(self.get_state(self._location_entity))
    #     self.log(self._home_window_active)
    #     self.unlock_door()
    #     if (
    #         self._person_detected_flag
    #         and self.get_state(self._location_entity) == "home"
    #         and self._home_window_active
    #     ):
    #         self.log("trueee")
    #         self.unlock_door()
    #     else:
    #         self.log("falseeeee")
    #
    # def unlock_door(self):
    #     self.log("checking lock state")
    #     lock_state = self.get_state("lock.front_door")
    #     self.log("lock.front_door")
    #     if lock_state == "locked":
    #         self.log("Unlocked via Cameras")
    #         self.call_service(
    #             "mqtt/publish",
    #             topic=f"{self._lock_topic}/set",
    #             payload="UNLOCK",
    #         ),
    #
    # def lock_door(self):
    #     lock_state = self.get_state(self._lock)
    #     if lock_state == "unlocked":
    #         self.log("Locked via Location")
    #         self.call_service(
    #             "mqtt/publish",
    #             topic=f"{self._lock_topic}/set",
