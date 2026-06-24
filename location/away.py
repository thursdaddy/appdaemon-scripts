import hassapi as hass


class AwayMode(hass.Hass):
    def initialize(self):
        # Configuration
        self._location_entity = self.args.get("location_entity", "device_tracker.pixel_7_pro")
        self._wifi_entity = self.args.get("wifi_sensor", "sensor.pixel_7_pro_wi_fi_connection")
        self._hvac_entity = self.args.get("hvac_entity", "climate.nest")
        self._all_lights_switch = self.args.get("all_lights_switch", "input_boolean.lights_all")
        self._away_temp = float(self.args.get("away_temp", 85.0))
        self._debug_mode = self.args.get("debug", False)

        # State tracking
        self.departure_timer = None

        # --- Configuration Output ---
        self.log("============================")
        self.log(f"  HVAC Target:   {self._away_temp}F")
        self.log(f"  Master Light:  {self._all_lights_switch}")
        self.log(f"  Tracker:       {self._location_entity}")
        self.log(f"  WiFi Sensor:   {self._wifi_entity}")
        self.log(f"  Debug Mode:    {'ENABLED' if self._debug_mode else 'DISABLED'}")
        self.log("=========  CONFIG  =========")

        # Listen to state changes on both sensors
        self.listen_state(self.presence_changed, self._location_entity)
        if self._wifi_entity:
            self.listen_state(self.presence_changed, self._wifi_entity)

    def debug_log(self, message):
        if self._debug_mode:
            self.log(f"[DEBUG] {message}")

    def is_user_home(self) -> bool:
        """Helper to determine if user is home using either GPS or Wi-Fi"""
        gps_state = self.get_state(self._location_entity)
        wifi_state = self.get_state(self._wifi_entity) if self._wifi_entity else None

        is_gps_home = (gps_state == "home")
        is_wifi_connected = (wifi_state == "connected")

        self.debug_log(f"Checking presence: GPS={gps_state} (home={is_gps_home}), WiFi={wifi_state} (connected={is_wifi_connected})")
        return is_gps_home or is_wifi_connected

    def presence_changed(self, entity, attribute, old, new, kwargs):
        if new in [None, "unavailable", "unknown"]:
            return

        user_home = self.is_user_home()

        if user_home:
            # If we had a pending departure timer, cancel it
            if self.departure_timer is not None:
                self.log(f"User detected home/connected via {entity} ({new}). Canceling pending departure timer.")
                self.cancel_timer(self.departure_timer)
                self.departure_timer = None
                
                # Notify user that the away trigger was aborted
                self.call_service(
                    "notify/gotify",
                    title="Departure Aborted",
                    message=f"Aborted: Phone reconnected or returned home via {entity}.",
                )
        else:
            # User is away from both GPS and Wi-Fi
            if self.departure_timer is None:
                self.log(f"User detected away via {entity} ({new}). Starting 5-minute confirmation delay.")
                self.call_service(
                    "notify/gotify",
                    title="Departure Pending",
                    message="Phone detected away. Starting 5-minute verification delay.",
                )
                self.departure_timer = self.run_in(self.confirm_departure, 300)

    def confirm_departure(self, kwargs):
        self.departure_timer = None

        if self.is_user_home():
            self.log("Confirm Departure check failed: User is detected home/connected. Aborting departure.")
            return

        self.log("Departure Confirmed: Commencing Away automations.")

        # 1. Turn off all lights
        self.log(f"Action: Turning off {self._all_lights_switch}")
        self.turn_off(self._all_lights_switch)

        # 2. Set HVAC to Away mode
        try:
            self.log(f"Action: Setting {self._hvac_entity} to {self._away_temp}")
            self.call_service(
                "climate/set_temperature",
                entity_id=self._hvac_entity,
                temperature=self._away_temp,
            )
        except Exception as e:
            self.log(f"[ERR] HVAC Service Call Failed: {e}")

        # 3. Notify user
        self.call_service(
            "notify/gotify",
            title="AWAY",
            message="Departure confirmed. Lights OFF, HVAC set to ECO mode.",
        )
