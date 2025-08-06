from datetime import datetime

import appdaemon.plugins.hass.hassapi as hass


class ClimateSchedule(hass.Hass):
    def initialize(self):
        self.climate_entity = self.args.get("climate_entity")
        self.forecast_sensor = self.args.get("forecast_sensor")
        self.high_temp_threshold = self.args.get("high_temp_threshold", 85)
        self.climate_comfort_temp = self.args.get("climate_comfort_temp", 83)
        self.on_peak_temp = self.args.get("on_peak_temp", 85)
        self.off_peak_temp = self.args.get("off_peak_temp", 80)
        self.manual_control_entity = (
            "input_boolean.hvac_manual_control"  # Define the manual control entity
        )
        self.presence_entity = "device_tracker.pixel_7_pro"

        if not self.climate_entity:
            self.error("climate_entity not defined in apps.yaml")
            return
        if not self.forecast_sensor:
            self.error("forecast_sensor not defined in apps.yaml")
            return

        self.run_every(
            self.check_manual_override, "now+1", 360
        )  # Run every 10 seconds for testing
        self.run_daily(self.check_daily_forecast, "04:00:00")  # Keep daily at 4:00 AM

    def check_manual_override(self, kwargs):
        """Checks if manual control is enabled."""
        manual_control_state = self.get_state(self.manual_control_entity)
        if manual_control_state == "on":
            self.log("HVAC manual control is ON. Skipping automatic adjustments.")
            return
        self.check_schedule_and_set_climate()

    def check_presence(self):
        """Checks if the presence entity is home."""
        presence_state = self.get_state(self.presence_entity)
        if presence_state == "home":
            return True
        else:
            self.log("NOT HOME - Skipping HVAC adjustments.")
            return False

    def check_set_temperature(self, desired_temp):
        """Checks the current temperature and sets it if it doesn't match."""
        current_state = self.get_state(self.climate_entity, attribute="temperature")
        if current_state is not None:
            try:
                current_temp = float(current_state)
                if current_temp != desired_temp:
                    self.log(
                        f"Current temperature ({current_temp}) does not match desired ({desired_temp})."
                    )
                    return False  # Temperature needs to be set
                else:
                    self.log(
                        f"Current temperature ({current_temp}) matches desired ({desired_temp}). No action needed."
                    )
                    return True  # Temperature already matches
            except ValueError:
                self.log(f"Error: Could not parse current temperature: {current_state}")
                return False
        else:
            self.log(f"Error: Could not get current state of {self.climate_entity}")
            return False

    def check_schedule_and_set_climate(self):
        if not self.check_presence():
            return

        now = datetime.now()
        month = now.month
        now_time_str = now.strftime("%H:%M:%S")

        peak_status = self.determine_peak_status(month, now_time_str)

        if peak_status == "on_peak":
            desired_temp = self.on_peak_temp
            self.log(
                f"Current time ({now_time_str}) is on-peak. Desired temperature: {desired_temp}"
            )
            if not self.check_set_temperature(desired_temp):
                self.set_hvac_mode("cool", desired_temp)
        elif peak_status == "off_peak":
            desired_temp = self.off_peak_temp
            self.log(
                f"Current time ({now_time_str}) is off-peak. Desired temperature: {desired_temp}"
            )
            if not self.check_set_temperature(desired_temp):
                self.set_hvac_mode("cool", desired_temp)
        else:
            self.log(f"Current time ({now_time_str}) is neither on-peak nor off-peak.")

    def determine_peak_status(self, month, now_time_str):
        schedule = self.args.get("schedule", {})

        # Check for summer on-peak (May through October)
        if 5 <= month <= 10:
            if "summer" in schedule.get("on_peak", {}):
                hours_list = schedule["on_peak"]["summer"].get("hours", [])
                for time_range in hours_list:
                    start_time_str, end_time_str = time_range.split("-")
                    if self.now_is_between(start_time_str, end_time_str):
                        return "on_peak"

        # Check for winter on-peak periods (November through April)
        if 11 <= month <= 12 or 1 <= month <= 4:
            if "winter" in schedule.get("on_peak", {}):
                hours_list = schedule["on_peak"]["winter"].get("hours", [])
                for time_range in hours_list:
                    start_time_str, end_time_str = time_range.split("-")
                    if self.now_is_between(start_time_str, end_time_str):
                        return "on_peak"

        # Check for summer off-peak (May through October)
        if 5 <= month <= 10:
            if "summer" in schedule.get("off_peak", {}):
                hours_list = schedule["off_peak"]["summer"].get("hours", [])
                for time_range in hours_list:
                    start_time_str, end_time_str = time_range.split("-")
                    if self.now_is_between(start_time_str, end_time_str):
                        return "off_peak"

        # Check for winter off-peak periods (November through April)
        if 11 <= month <= 12 or 1 <= month <= 4:
            if "winter" in schedule.get("off_peak", {}):
                hours_list = schedule["off_peak"]["winter"].get("hours", [])
                for time_range in hours_list:
                    start_time_str, end_time_str = time_range.split("-")
                    if self.now_is_between(start_time_str, end_time_str):
                        return "off_peak"

        return None

    def check_daily_forecast(self, kwargs):
        forecast_high = self.get_state(self.forecast_sensor)
        self.log(f"Checking daily forecast. Forecasted high is {forecast_high}")

        try:
            forecast_high_temp = float(forecast_high)
            if forecast_high_temp > self.high_temp_threshold:
                desired_temp = self.climate_comfort_temp
                self.log(
                    f"Forecast high ({forecast_high_temp}) is above threshold ({self.high_temp_threshold}). Desired temperature: {desired_temp}"
                )
                if not self.check_set_temperature(desired_temp):
                    self.set_hvac_mode("cool", desired_temp)
            else:
                self.log(
                    f"Forecast high ({forecast_high_temp}) is below threshold ({self.high_temp_threshold}). Setting HVAC to off."
                )
                self.set_hvac_mode("off")
        except ValueError:
            self.log(
                f"Error: Could not convert forecast high ({forecast_high}) to a number. Skipping daily forecast check."
            )
            return

    def set_hvac_mode(self, hvac_mode, target_temp=None):
        """Helper function to try and set the HVAC mode."""
        if hvac_mode == "cool" and target_temp is not None:
            self.log(f"Setting {self.climate_entity} to cool at {target_temp}")
            self.call_service(
                "climate/set_temperature",
                entity_id=self.climate_entity,
                temperature=target_temp,
            )
        elif hvac_mode == "off":
            self.log(f"Setting {self.climate_entity} to off")
            self.call_service(
                "climate/set_hvac_mode",
                entity_id=self.climate_entity,
                hvac_mode="off",
            )
        else:
            self.log(
                f"Warning: set_hvac_mode with '{hvac_mode}' might not be fully handled."
            )
