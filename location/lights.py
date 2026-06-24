import json

import hassapi as hass


class LocationChange(hass.Hass):
    def initialize(self):
        # Configuration
        self._location_entity = "device_tracker.pixel_7_pro"
        self._wifi_entity = self.args.get("wifi_sensor", None)
        self._doors = ["zigbee2mqtt/magnet_back_door", "zigbee2mqtt/magnet_front_door"]
        self._schedule = self.args.get("schedule", {})

        # Default fallbacks
        self._default_delay = self.args.get("delay", 90)
        self._default_lights = self.args.get("lights", [])
        self._default_brightness = self.args.get("brightness", 50)
        self._debug_mode = self.args.get("debug", False)

        # State tracking
        self.timer_handler = None
        self._home_window_active = False
        self._active_config = None

        # --- Configuration Output ---
        self.log("============================")
        self.log(f"  Schedule:      {list(self._schedule.keys())}")
        self.log(f"  Doors:         {self._doors}")
        self.log(f"  Tracker:       {self._location_entity}")
        if self._wifi_entity:
            self.log(f"  WiFi Sensor:   {self._wifi_entity}")
        self.log(f"  Debug Mode:    {'ENABLED' if self._debug_mode else 'DISABLED'}")
        self.log("===        CONFIG        ===")

        self.listen_state(self.location_update, self._location_entity)
        if self._wifi_entity:
            self.listen_state(self.location_update, self._wifi_entity)
        self.mqtt_api = self.get_plugin_api("MQTT")

        # Listen for door sensors permanently
        for door in self._doors:
            self.mqtt_api.listen_event(self.magnet_callback, "MQTT_MESSAGE", topic=door)

    def debug_log(self, message):
        if self._debug_mode:
            self.log(f"[DEBUG] {message}")

    def location_update(self, entity, attribute, old, new, kwargs):
        if new in ["home", "connected"] and old not in ["home", "connected"]:
            if not self._home_window_active:
                self.log(f"Arrival Detected via {entity} ({old} -> {new}). Opening 5-minute welcome window.")
                self._active_config = self.get_current_schedule_config()

                if self._active_config:
                    self._home_window_active = True
                    self.run_in(self.end_home_window, 300)
                    
                    self.call_service(
                        "notify/gotify",
                        title="HOME",
                        message="Arrival window active. Waiting for door...",
                    )
                else:
                    self.debug_log(
                        "Arrived home, but no active schedule found. Skipping welcome window."
                    )

    def magnet_callback(self, event_name, data, kwargs):
        if not self._home_window_active:
            return

        try:
            payload = json.loads(data["payload"])
            if payload.get("contact") is False:  # Door Opened
                self.log(
                    f"Door access detected: Triggering '{self._active_config['name']}' lights."
                )
                self.execute_welcome_lights()
                self._home_window_active = False
        except Exception as e:
            self.log(f"Error parsing magnet data: {e}")

    def execute_welcome_lights(self):
        cfg = self._active_config
        brightness = self.convert_brightness(cfg["brightness"])

        for light in cfg["lights"]:
            self.turn_on(light, brightness=brightness)

        if self.timer_handler:
            self.cancel_timer(self.timer_handler)
        self.timer_handler = self.run_in(self.turn_off_welcome_lights, cfg["delay"])

    def turn_off_welcome_lights(self, kwargs):
        self.log("Welcome window delay finished. Turning off lights.")
        for light in self._active_config["lights"]:
            self.turn_off(light)

    def get_current_schedule_config(self):
        for name, cfg in self._schedule.items():
            if self.now_is_between(cfg["start"], cfg["end"]):
                return {
                    "name": name,
                    "lights": cfg.get("lights", self._default_lights),
                    "delay": cfg.get("delay", self._default_delay),
                    "brightness": cfg.get("brightness", self._default_brightness),
                }
        return None

    def convert_brightness(self, percent):
        return int(round(((percent - 1) / 99) * (255 - 3) + 3))

    def end_home_window(self, kwargs):
        self._home_window_active = False
        self.debug_log("Home window expired.")
