import appdaemon.plugins.hass.hassapi as hass
import json

class MotionRGBLight(hass.Hass):

    def initialize(self):
        self.hass_api = self.get_plugin_api("HASS")
        self.mqtt_api = self.get_plugin_api("MQTT")

        # set in apps.yaml
        self._motion_sensor = self.args.get("motion_sensor")
        self._lights = self.args.get("lights", None)
        self._schedule = self.args.get("schedule", None)
        self._color = self.args.get("color", [0, 255, 0])
        self._delay = self.args.get("delay", 30)
        self._brightness = self.args.get("brightness", 75)

        self.timer_handler = None

        if not self._motion_sensor:
            self.log(f"[ERR] Set a light or scene to use with {self._motion_sensor}")
            return

        self.mqtt_api.listen_event(
            self.mqtt_callback, "MQTT_MESSAGE", topic=self._motion_sensor
        )

    def mqtt_callback(self, event_name, data, kwargs):
        try:
            payload = json.loads(data["payload"])
            self._config = self.get_config()
            if "occupancy" in payload and payload["occupancy"] is True:
                self.log("Motion Detected!")

                if self.info_timer(self.timer_handler) is not None:
                    self.cancel_timer(self.timer_handler)

                self.turn_on_lights(self._config)

            elif "occupancy" in payload and payload["occupancy"] is False:
                self.log("Motion Cleared!")
                self.timer_handler = self.run_in(
                    self.turn_off_lights, self._config["delay"]
                )

        except json.JSONDecodeError:
            self.log("[ERR] Invalid JSON payload")
        except KeyError:
            self.log("[ERR] Missing occupancy key in payload")

    def get_config(self):
        for name, config in self._schedule.items():
            config["name"] = name
            start = config["start"]
            end = config["end"]
            if self.now_is_between(start, end):
                if "brightness" not in config:
                    config["brightness"] = self._brightness
                config["brightness_adjusted"] = self.convert_brightness_value(value=config["brightness"])
                if "color" not in config:
                    config["color"] = self._color
                if "delay" not in config:
                    config["delay"] = self._delay
                if "lights" not in config:
                    config["lights"] = self._lights
                return config

    # represent brightness value as percentage between 1-100, translate to values 3-255
    def convert_brightness_value(self, value):
        value = (value - 1) / 99
        value_adjusted = int(round(value * (255 - 3) + 3))
        return value_adjusted

    def turn_on_lights(self, config):
        for light in config["lights"]:
            # get current state of lights
            state_all = self.get_entity(light).get_state(attribute="all")
            state_brightness = state_all["attributes"]["brightness"]
            state_color = state_all["attributes"]["rgb_color"]

            # set color via wheel in has ui to get rgb values
            # self.log(f"STATE: {state_brightness} - {state_color}")
            # config_brightness = config["brightness_adjusted"]
            # config_color = config["color"]
            # self.log(f"CONFIG: {config_brightness} : {config_color}")

            if (
                state_all["state"] == "off"
                or not config["color"] == state_color
                or not config["brightness_adjusted"] == state_brightness
            ):
                self.log(f"Turning on light: {light}")
                self.call_service(
                    "light/turn_on",
                    entity_id=light,
                    brightness=config["brightness_adjusted"],
                    rgb_color=config["color"],
                )

    def turn_off_lights(self, kwargs):
        for light in self._config["lights"]:
            self.log(f"Turning off light: {light}")
            self.turn_off(light)
