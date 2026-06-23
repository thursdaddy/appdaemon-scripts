import appdaemon.plugins.hass.hassapi as hass


class ClimateSchedule(hass.Hass):
    def initialize(self):
        # --- Entities & Thresholds ---
        self.climate_entity = self.args.get("climate_entity", "climate.nest")
        self.forecast_sensor = self.args.get("forecast_sensor", "sensor.weather_high_temp")
        self.presence_entity = self.args.get("presence_entity", "device_tracker.pixel_7_pro")
        self.manual_control_entity = self.args.get("manual_control_entity", "input_boolean.hvac_manual_control")

        self.high_temp_threshold = float(self.args.get("high_temp_threshold", 85.0))
        self.climate_comfort_temp = float(self.args.get("climate_comfort_temp", 80.0))
        self.super_off_peak_temp = float(self.args.get("super_off_peak_temp", 75.0))
        self.off_peak_temp = float(self.args.get("off_peak_temp", 78.0))
        self.on_peak_temp = float(self.args.get("on_peak_temp", 85.0))

        self._debug_mode = self.args.get("debug", False)

        # --- Parse E-16 Windows ---
        schedule_arg = self.args.get("schedule", {})
        
        on_peak_arg = schedule_arg.get("on_peak", {})
        self.on_peak_hours = on_peak_arg.get("hours", ["17:00:00-22:00:00"])
        self.on_peak_weekdays_only = on_peak_arg.get("weekdays_only", True)

        super_off_peak_arg = schedule_arg.get("super_off_peak", {})
        self.super_off_peak_hours = super_off_peak_arg.get("hours", ["08:00:00-15:00:00"])
        self.super_off_peak_weekdays_only = super_off_peak_arg.get("weekdays_only", False)

        # --- Configuration Output ---
        self.log("============================")
        self.log(f"  Climate:             {self.climate_entity}")
        self.log(f"  Super Off-Peak Temp: {self.super_off_peak_temp}F")
        self.log(f"  Off-Peak Temp:       {self.off_peak_temp}F")
        self.log(f"  On-Peak Temp:        {self.on_peak_temp}F")
        self.log(f"  On-Peak Hours:       {self.on_peak_hours} (Weekdays only: {self.on_peak_weekdays_only})")
        self.log(f"  Super Off-Peak Hours: {self.super_off_peak_hours} (Weekdays only: {self.super_off_peak_weekdays_only})")
        self.log(f"  Debug Mode:          {'ENABLED' if self._debug_mode else 'DISABLED'}")
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
        """Calculates setpoint based on current schedule tier"""
        if self.is_now_peak():
            self.apply_temperature(self.on_peak_temp, "On-Peak")
        elif self.is_now_super_off_peak():
            self.apply_temperature(self.super_off_peak_temp, "Super Off-Peak")
        else:
            self.apply_temperature(self.off_peak_temp, "Off-Peak")

    def is_now_peak(self):
        """Returns True if current time matches On-Peak window"""
        if self.on_peak_weekdays_only:
            # isoweekday() returns 1 (Monday) to 7 (Sunday)
            weekday = self.datetime().isoweekday()
            if weekday not in [1, 2, 3, 4, 5]:
                return False

        for window in self.on_peak_hours:
            start, end = window.split("-")
            if self.now_is_between(start, end):
                return True
        return False

    def is_now_super_off_peak(self):
        """Returns True if current time matches Super Off-Peak window"""
        if self.super_off_peak_weekdays_only:
            weekday = self.datetime().isoweekday()
            if weekday not in [1, 2, 3, 4, 5]:
                return False

        for window in self.super_off_peak_hours:
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
