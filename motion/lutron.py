import json

import appdaemon.plugins.hass.hassapi as hass


class MotionLights(hass.Hass):
    """
    Lutron

    """

    def initialize(self):
        self.hass_api = self.get_plugin_api("HASS")
        self.mqtt_api = self.get_plugin_api("MQTT")

        # set in apps.yaml
        self._motion_sensor = self.args.get("motion_sensor")
        self._lights = self.args.get("lights", None)
        self._schedule = self.args.get("schedule", None)
        self._brightness = self.args.get("brightness", 75)
        self._delay = self.args.get("delay", 30)
        self._debug_mode = self.args.get("debug", False)
        self.motion_control = self._motion_sensor.replace(
            "zigbee2mqtt/", "input_boolean."
        )

        self.timer_handler = None

        # Collect all lights managed by this automation across all schedules
        self._all_managed_lights = set()
        if self._lights:
            self._all_managed_lights.update(self._lights)
        if self._schedule:
            for config in self._schedule.values():
                sched_lights = config.get("lights")
                if sched_lights:
                    self._all_managed_lights.update(sched_lights)

        if not self._motion_sensor:
            self.log(
                f"[ERR] Set a light or scene to use with \
                        {self._motion_sensor}"
            )
            return

        # Log configuration loading
        self.log("============================")
        self.log(f"  Motion Sensor:  {self._motion_sensor}")
        self.log(f"  Default Lights: {self._lights}")
        self.log(f"  Default Delay:  {self._delay}s")
        self.log(f"  Default Bright: {self._brightness}%")
        self.log(f"  Schedules:      {list(self._schedule.keys()) if self._schedule else 'None'}")
        self.log(f"  Debug Mode:     {'ENABLED' if self._debug_mode else 'DISABLED'}")
        self.log("=== Configuration Loaded ===")

        self.mqtt_api.listen_event(
            self.mqtt_callback, "MQTT_MESSAGE", topic=self._motion_sensor
        )

    def debug_log(self, message):
        if self._debug_mode:
            self.log(f"[DEBUG] {message}")

    def mqtt_callback(self, event_name, data, kwargs):
        motion_control = self.get_state(self.motion_control)
        if motion_control == "off":
            self.debug_log("Motion Disabled, bye.")
            return
        try:
            payload = json.loads(data["payload"])
            self.debug_log(f"Incoming MQTT message: {payload}")
            self.config = self.get_config()
            if self.config is None:
                self.debug_log("No active schedule found, not processing motion event.")
                return

            if "occupancy" in payload and payload["occupancy"] is True:
                self.log("Motion Detected!")

                if self.info_timer(self.timer_handler) is not None:
                    self.debug_log("Canceling active off timer.")
                    self.cancel_timer(self.timer_handler)

                self.turn_on_lights()

            elif "occupancy" in payload and payload["occupancy"] is False:
                self.log("Motion Cleared!")
                self.debug_log(f"Scheduling turn-off in {self.config['delay']}s")
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
        attributes = state_all.get("attributes", {})
        brightness = attributes.get("brightness")
        if self.config.get("brightness_adjusted") == brightness:
            return True
        return False

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
        for light in self._all_managed_lights:
            self.log(f"Turning off light: {light}")
            self.turn_off(light)
