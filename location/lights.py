import json

import hassapi as hass


class LocationChange(hass.Hass):
    """
    Location change automations. Lights and HVAC.
    """

    def initialize(self) -> None:
        self.hass_api = self.get_plugin_api("HASS")
        self.mqtt_api = self.get_plugin_api("MQTT")

        self._delay = self.args.get("delay", 90)
        self._lights = self.args.get("lights")
        self._location_entity = "device_tracker.pixel_7_pro"
        self._brightness = self.args.get("brightness", 50)
        self._schedule = self.args.get("schedule")

        self.listen_state(self.location_update, "input_boolean.test_boolean")
        # self.listen_state(self.location_update, self._location_entity)

        self.timer_handler = None

        # home detection flags
        self._home_window_timer = None
        self._home_window_active = False

    def location_update(self, entity, attribute, old, new, kwargs):
        self.config = self.get_config()

        if new == "home" and old != "home":
            # if new == "on" and old != "on":
            self.log("Home Location Detected")

            self._home_window_active = True
            self._home_window_timer = self.run_in(self.end_home_window, 300)

            if self.config is not None:
                self.listen_for_door()
                # self.set_lights_to_home()
            else:
                self.log("Not scheduled, bye.")

            self.call_service(
                "notify/gotify",
                title="HOME",
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

            self.call_service(
                "notify/gotify",
                title="AWAY",
                message="Turning off Lights, Setting HVAC.",
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

            self.log("Setting HVAC")
            self.call_service(
                "climate/set_temperature",
                entity_id="climate.nest",
                temperature=85,
            )

    def listen_for_door(self):
        self.log("Listening for door..")
        if self._home_window_active:
            self.mqtt_api.listen_event(
                self.magnet_callback,
                "MQTT_MESSAGE",
                topic="zigbee2mqtt/magnet_back_door",
            )

            self.mqtt_api.listen_event(
                self.magnet_callback,
                "MQTT_MESSAGE",
                topic="zigbee2mqtt/magnet_front_door",
            )

    def magnet_callback(self, event_name, data, kwargs):
        try:
            payload = json.loads(data["payload"])
            if "contact" in payload and payload["contact"] is False:
                self.log("DOOR OPEN")
                self.set_lights_to_home()

        except json.JSONDecodeError:
            self.log("[ERR] Invalid JSON payload")
        except KeyError:
            self.log("[ERR] Missing occupancy key in payload")

    def end_home_window(self, kwargs):
        self._home_window_active = False
        self.log("Home window ended")

    def set_lights_to_away(self):
        self.log("Away lights")
        self.turn_off("input_boolean.lights_all")

    def set_lights_to_home(self):
        self.log("Home lights")
        self.log(self.config)
        for light in self.config["lights"]:
            self.log(f"Turning on {light}")
            self.call_service(
                "light/turn_on",
                entity_id=light,
                brightness=self.config["brightness_adjusted"],
            )

            if self.info_timer(self.timer_handler) is not None:
                self.cancel_timer(self.timer_handler)

            self.timer_handler = self.run_in(
                self.turn_off_home_lights, self.config["delay"]
            )

    def turn_off_home_lights(self, kwargs):
        self.log("Turning off welcome home lights..")
        for light in self.config["lights"]:
            self.turn_off(light)

    def get_config(self):
        for name, config in self._schedule.items():
            config["name"] = name
            if "delay" not in config:
                config["delay"] = self._delay
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
