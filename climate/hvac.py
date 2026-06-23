import appdaemon.plugins.hass.hassapi as hass


class ClimateSchedule(hass.Hass):
    def initialize(self):
        # --- Entities & Thresholds ---
        self.climate_entity = "climate.nest"
        self.forecast_sensor = "sensor.weather_high_temp"
        self.presence_entity = "device_tracker.pixel_7_pro"
        self.manual_control_entity = "input_boolean.hvac_manual_control"

        self.high_temp_threshold = 85
        self.climate_comfort_temp = 83
        self.on_peak_temp = 85
        self.off_peak_temp = 80

        self._debug_mode = self.args.get("debug", False)

        # --- Hard-Coded On-Peak Windows Only ---
        # If time is NOT in these windows, it is considered Off-Peak
        self.on_peak_windows = {
            "summer": ["15:00:00-19:00:00"],
            "winter": ["06:00:00-09:00:00", "18:00:00-21:00:00"],
        }

        # --- Configuration Output ---
        self.log("============================")
        self.log(f"  Climate:       {self.climate_entity}")
        self.log(f"  Comfort Temp:  {self.climate_comfort_temp}F")
        self.log(f"  Peak Temp:     {self.on_peak_temp}F")
        self.log(f"  Off-Peak Temp: {self.off_peak_temp}F")
        self.log(f"  Debug Mode:    {'ENABLED' if self._debug_mode else 'DISABLED'}")
        self.log("===        CONFIG        ===")

        # Run checks (Every 6 minutes)
        self.run_every(self.check_manual_override, "now+1", 360)
        self.run_daily(self.check_daily_forecast, "04:00:00")

    def debug_log(self, message):
        if self._debug_mode:
            self.log(f"[DEBUG] {message}")

    def check_manual_override(self, kwargs):
        """Gatekeeper: Checks if automation is allowed to run"""
        if self.get_state(self.manual_control_entity) == "on":
            self.debug_log("Manual control is ON. Skipping.")
            return

        if self.get_state(self.presence_entity) != "home":
            self.debug_log("Not Home. Skipping adjustments.")
            return

        self.check_schedule_and_set_climate()

    def check_schedule_and_set_climate(self):
        """Calculates current season and checks windows"""
        month = self.datetime().month
        season = "summer" if 5 <= month <= 10 else "winter"

        # Binary Logic: It's either Peak or it's Off-Peak
        if self.is_now_peak(season):
            self.apply_temperature(self.on_peak_temp, "On-Peak")
        else:
            self.apply_temperature(self.off_peak_temp, "Off-Peak")

    def is_now_peak(self, season):
        """Returns True if current time matches any On-Peak window"""
        windows = self.on_peak_windows.get(season, [])
        for window in windows:
            start, end = window.split("-")
            if self.now_is_between(start, end):
                return True
        return False

    def apply_temperature(self, desired_temp, context):
        """Sets temperature only if it differs from current target"""
        current_target = self.get_state(self.climate_entity, attribute="temperature")

        try:
            if current_target is not None and float(current_target) == float(
                desired_temp
            ):
                self.debug_log(f"Thinking: Temp already at {desired_temp} ({context}).")
                return

            self.log(f"Action: Setting {context} temperature to {desired_temp}")
            self.call_service(
                "climate/set_temperature",
                entity_id=self.climate_entity,
                temperature=desired_temp,
            )
        except (ValueError, TypeError) as e:
            self.log(f"[ERR] Failed to compare temperatures: {e}")

    def check_daily_forecast(self, kwargs):
        """Daily 4 AM logic based on high-temp forecast"""
        forecast_high = self.get_state(self.forecast_sensor)

        try:
            high_temp = float(forecast_high)
            if high_temp > self.high_temp_threshold:
                self.log(
                    f"Forecast: High of {high_temp}F. Pre-cooling to {self.climate_comfort_temp}F."
                )
                self.apply_temperature(self.climate_comfort_temp, "Forecast Comfort")
            else:
                self.log(f"Forecast: High of {high_temp}F is mild. Turning HVAC OFF.")
                self.call_service(
                    "climate/set_hvac_mode",
                    entity_id=self.climate_entity,
                    hvac_mode="off",
                )
        except (ValueError, TypeError):
            self.log(f"[ERR] Invalid forecast data: {forecast_high}")
