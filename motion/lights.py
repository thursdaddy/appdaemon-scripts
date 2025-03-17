import json

import appdaemon.plugins.hass.hassapi as hass


class MotionLight(hass.Hass):

    def initialize(self):
        self.hass_api = self.get_plugin_api("HASS")
        self.mqtt_api = self.get_plugin_api("MQTT")

        # set in apps.yaml
        self._motion_sensor = self.args.get("motion_sensor")
        self._lights = self.args.get("lights", None)
        self._schedule = self.args.get("schedule", None)
        self._brightness = self.args.get("brightness", 75)
        self.motion_control = self._motion_sensor.replace(
            "zigbee2mqtt/", "input_boolean."
        )

        self.timer_handler = None

        if not self._motion_sensor:
            self.log(
                f"[ERR] Set a light or scene to use with \
                        {self._motion_sensor}"
            )
            return

        self.mqtt_api.listen_event(
            self.mqtt_callback, "MQTT_MESSAGE", topic=self._motion_sensor
        )

    def mqtt_callback(self, event_name, data, kwargs):
        motion_control = self.get_state(self.motion_control)
        if motion_control == "off":
            self.log("Motion Disabled, bye.")
            return
        try:
            payload = json.loads(data["payload"])
            self.config = self.get_config()
            if "occupancy" in payload and payload["occupancy"] is True:
                self.log("Motion Detected!")

                if self.info_timer(self.timer_handler) is not None:
                    self.cancel_timer(self.timer_handler)

                self.turn_on_lights()

            elif "occupancy" in payload and payload["occupancy"] is False:
                self.log("Motion Cleared!")
                self.timer_handler = self.run_in(
                    self.turn_off_lights, self.config["delay"]
                )

        except json.JSONDecodeError:
            self.log("[ERR] Invalid JSON payload")
        except KeyError:
            self.log("[ERR] Missing occupancy key in payload")

    def get_config(self):
        for name, config in self._schedule.items():
            config["name"] = name
            if "brightness" not in config:
                config["brightness"] = self._brightness
            config["brightness_adjusted"] = self.convert_brightness_value(
                value=config["brightness"]
            )
            if "delay" not in config:
                config["delay"] = self._delay
            if "lights" not in config:
                config["lights"] = self._lights
            if self.now_is_between(config["start"], config["end"]):
                return config

    # represent brightness value as
    # percentage between 1-100, translate to values 3-255
    def convert_brightness_value(self, value):
        value = (value - 1) / 99
        value_adjusted = int(round(value * (255 - 3) + 3))
        return value_adjusted

    def state_and_config_values(self, state_all, light):
        brightness = state_all["attributes"]["brightness"]
        # config_brightness = self.config["brightness_adjusted"]
        if self.config["brightness_adjusted"] == brightness:
            return True

    def turn_on_lights(self):
        for light in self.config["lights"]:
            state_all = self.get_entity(light).get_state(attribute="all")

            matching = self.state_and_config_values(state_all, light)
            if state_all["state"] == "off" or not matching:
                self.log(f"Turning on light: {light}")
                self.call_service(
                    "light/turn_on",
                    entity_id=light,
                    brightness=self.config["brightness_adjusted"],
                )

    def turn_off_lights(self, kwargs):
        for light in self.config["lights"]:
            self.log(f"Turning off light: {light}")
            self.turn_off(light)
