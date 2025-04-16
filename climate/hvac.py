from datetime import datetime

import appdaemon.plugins.hass.hassapi as hass


class NestClimateManager(hass.Hass):
    """
    AppDaemon app to manage a Nest thermostat based on Electron Provider time-of-use plans,
    and daily high forecast.
    """

    def initialize(self):
        """Initialize the app."""
        self.log("NestClimateManager Initialized.")

        # Define entities and settings
        self.nest_entity = "climate.nest"
        self.forecast_sensor = "sensor.forecast_today_high"
        self.high_temp_threshold = 85
        self.climate_peak_temp = 82
        self.climate_comfort_temp = 78

        # Listen for daily forecast check
        self.run_daily(self.check_daily_forecast, "04:00:00")

    def check_daily_forecast(self, kwargs):
        """
        Check the daily forecast and set the thermostat mode and temperature.
        This runs at 4:00 AM.
        """
        forecast_high = self.get_state(self.forecast_sensor)
        self.log(f"Checking daily forecast.  Forecasted high is {forecast_high}")

        try:
            forecast_high_temp = float(forecast_high)
            if forecast_high_temp > self.high_temp_threshold:
                self.log(
                    f"Forecast high ({forecast_high_temp}) is above threshold ({self.high_temp_threshold}). Setting Nest to cool at {self.climate_comfort_temp}."
                )
                self.set_hvac_mode(
                    hvac_mode="cool", target_temp=self.climate_comfort_temp
                )
            else:
                self.log(
                    f"Forecast high ({forecast_high_temp}) is below threshold ({self.high_temp_threshold}). Turning off Nest."
                )
                self.set_hvac_mode(hvac_mode="off")
        except ValueError:
            self.log(
                f"Error: Could not convert forecast high ({forecast_high}) to a number.  Skipping daily forecast check."
            )
            return

        # Check Electron Provider time of use and adjust temperature
        self.check_utility_provider_rate()

    def check_utility_provider_rate(self):
        """
        Check Electron Provider time of use and set the thermostat temperature.
        """
        now = datetime.now()
        month = now.month
        hour = now.hour

        # Electron Provider Time of Use logic
        is_peak = False
        if 5 <= month <= 10:  # Summer (May to October)
            if 14 <= hour < 20:  # 2 PM to 8 PM
                is_peak = True
        elif 11 <= month <= 4:  # Winter (November to April)
            if (5 <= hour < 9) or (17 <= hour < 21):  # 5 AM to 9 AM and 5 PM to 9 PM
                is_peak = True

        if is_peak:
            self.log(
                f"Electron Provider peak hours. Setting Nest temperature to {self.climate_peak_temp}."
            )
            self.set_hvac_mode(
                hvac_mode="cool", target_temp=self.climate_peak_temp
            )  # set to cool during peak
        else:
            self.log(
                f"Electron Provider off-peak hours. Setting Nest temperature to {self.climate_comfort_temp}."
            )
            self.set_hvac_mode(hvac_mode="cool", target_temp=self.climate_comfort_temp)

    def set_hvac_mode(self, hvac_mode, target_temp=None):
        """
        Set the HVAC mode and temperature of the Nest thermostat.

        Args:
            hvac_mode (str): The HVAC mode to set (e.g., "cool", "off").
            target_temp (float, optional): The target temperature to set. Defaults to None.
        """
        self.log(f"Setting HVAC mode to {hvac_mode}")
        self.call_service(
            "climate/set_hvac_mode", entity_id=self.nest_entity, hvac_mode=hvac_mode
        )
        if target_temp is not None:
            self.log(f"Setting target temperature to {target_temp}")
            self.call_service(
                "climate/set_temperature",
                entity_id=self.nest_entity,
                temperature=target_temp,
            )
