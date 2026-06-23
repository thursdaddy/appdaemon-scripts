import json

import appdaemon.plugins.hass.hassapi as hass


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
        self._debug_mode = self.args.get("debug", False)
        self._motion_control = self._motion_sensor.replace(
            "zigbee2mqtt/", "input_boolean."
        )

        # Lux-based brightness control variables
        self._lux_sensor = self.args.get("lux_sensor", None)
        self._lux_min = float(self.args.get("lux_min", 10.0))
        self._lux_max = float(self.args.get("lux_max", 60.0))
        self._lux_min_brightness = int(self.args.get("lux_min_brightness", 10))

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
        self.log(f"  Default Color:  {self._color}")
        if self._lux_sensor:
            self.log(f"  Lux Sensor:     {self._lux_sensor}")
            self.log(f"  Lux Range:      {self._lux_min} - {self._lux_max} lx")
            self.log(f"  Min Brightness: {self._lux_min_brightness}%")
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
        motion_control = self.get_state(self._motion_control)
        if motion_control == "off":
            self.debug_log("Motion Disabled, bye.")
            return
        try:
            payload = json.loads(data["payload"])
            self.debug_log(f"Incoming MQTT message: {payload}")
            self.config = self.get_config()
            if self.config is None:
                self.debug_log(
                    "No active schedule found, not processing motion event."
                )
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
            if "color" not in config:
                config["color"] = self._color
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

    def state_and_config_values(self, state_all, light, target_brightness):
        attributes = state_all.get("attributes", {})
        brightness = attributes.get("brightness")
        color = attributes.get("rgb_color")
        
        color_matches = True
        if self.config.get("color") and color:
            color_matches = all(abs(c1 - c2) <= 5 for c1, c2 in zip(self.config.get("color"), color))
            
        brightness_matches = True
        if brightness is not None:
            brightness_matches = abs(target_brightness - brightness) <= 3
            
        return color_matches and brightness_matches

    def turn_on_lights(self):
        brightness_percent = self.config["brightness"]
        
        if self._lux_sensor:
            try:
                lux_state = self.get_state(self._lux_sensor)
                if lux_state not in [None, "unavailable", "unknown"]:
                    current_lux = float(lux_state)
                    
                    if current_lux >= self._lux_max:
                        self.log(f"Motion trigger: lux is {current_lux} lx (>= max {self._lux_max} lx). Skipping light activation.")
                        return
                    elif current_lux <= self._lux_min:
                        brightness_percent = self.config["brightness"]
                        self.log(f"Motion trigger: lux is {current_lux} lx (<= min {self._lux_min} lx). Setting brightness to full: {brightness_percent}%.")
                    else:
                        min_b = self._lux_min_brightness
                        max_b = self.config["brightness"]
                        
                        if max_b > min_b:
                            ratio = (current_lux - self._lux_min) / (self._lux_max - self._lux_min)
                            brightness_percent = max_b - (ratio * (max_b - min_b))
                            brightness_percent = max(min_b, min(max_b, brightness_percent))
                            self.log(f"Motion trigger: lux is {current_lux} lx. Scaling brightness to {brightness_percent:.1f}%.")
                        else:
                            brightness_percent = max_b
                            self.log(f"Motion trigger: lux is {current_lux} lx. Brightness defaults to {brightness_percent}%.")
            except (ValueError, TypeError) as e:
                self.log(f"Error calculating lux-based brightness: {e}", level="WARNING")
        
        brightness_adjusted = self.convert_brightness_value(brightness_percent)
        
        for light in self.config["lights"]:
            state_all = self.get_entity(light).get_state(attribute="all")

            matching = self.state_and_config_values(state_all, light, brightness_adjusted)
            if state_all["state"] == "off" or not matching:
                self.log(f"Turning on light: {light} at {brightness_percent:.1f}% brightness")
                self.call_service(
                    "light/turn_on",
                    entity_id=light,
                    brightness=brightness_adjusted,
                    rgb_color=self.config["color"],
                )

    def turn_off_lights(self, kwargs):
        for light in self._all_managed_lights:
            self.log(f"Turning off light: {light}")
            self.turn_off(light)
