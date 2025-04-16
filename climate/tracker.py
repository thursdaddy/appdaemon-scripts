from datetime import datetime, time

import appdaemon.plugins.hass.hassapi as hass


class HVACCostTracker(hass.Hass):

    def initialize(self):
        self.listen_state(self.cooling_runtime_change, "sensor.hvac_cooling")
        self.daily_cost = 0.0
        self.monthly_cost = 0.0
        self.current_month = datetime.now().month
        self.peak_rates_summer = {"start": time(14, 0, 0), "end": time(20, 0, 0)}
        self.peak_rates_winter_morning = {"start": time(5, 0, 0), "end": time(9, 0, 0)}
        self.peak_rates_winter_evening = {
            "start": time(17, 0, 0),
            "end": time(21, 0, 0),
        }
        self.summer_months = range(5, 11)
        self.estimated_wattage_kw = 4.4
        self.previous_runtime = 0.0

        self.run_every(
            self.update_cost_sensors, "now", 360
        )  # Update sensors every minute
        self.run_daily(
            self.reset_daily_cost, time(0, 1, 0)
        )  # Reset daily cost shortly after midnight
        self.run_daily(
            self.reset_monthly_cost_on_new_month, time(0, 5, 0)
        )  # Reset monthly cost on new month

    def cooling_runtime_change(self, entity, attribute, old, new, kwargs):
        try:
            new_runtime = float(new)
            old_runtime = float(old) if old is not None else 0.0
            runtime_difference = new_runtime - old_runtime

            if runtime_difference > 0:
                cost = self.calculate_cost(runtime_difference)
                self.daily_cost += cost
                self.monthly_cost += cost
                self.log(
                    f"AC runtime increased by {runtime_difference:.2f} hours. Cost: ${cost:.2f}. Daily Cost: ${self.daily_cost:.2f}. Monthly Cost: ${self.monthly_cost:.2f}"
                )
            elif new_runtime < old_runtime:
                self.log("INFO: AC must have turned off.")
                return

            self.previous_runtime = new_runtime

        except ValueError:
            self.log(
                f"Error: Could not convert runtime values to float. Old: {old}, New: {new}"
            )

    def calculate_cost(self, hours):
        energy_used_kwh = self.estimated_wattage_kw * hours
        rate = self.get_current_rate()
        cost = energy_used_kwh * rate
        return cost

    def get_current_rate(self):
        now = datetime.now()
        month = now.month
        time_now = now.time()

        if month in self.summer_months:
            if (
                self.peak_rates_summer["start"]
                <= time_now
                < self.peak_rates_summer["end"]
            ):
                return 0.24
            else:
                return 0.09
        else:
            if (
                self.peak_rates_winter_morning["start"]
                <= time_now
                < self.peak_rates_winter_morning["end"]
                or self.peak_rates_winter_evening["start"]
                <= time_now
                < self.peak_rates_winter_evening["end"]
            ):
                return 0.12
            else:
                return 0.09

    def update_cost_sensors(self, kwargs):
        self.set_state(
            "sensor.ac_daily_cost",
            state=f"{self.daily_cost:.2f}",
            attributes={
                "friendly_name": "AC Daily Running Cost",
                "unit_of_measurement": "$",
                "icon": "mdi:currency-usd",
            },
        )
        self.set_state(
            "sensor.ac_monthly_cost",
            state=f"{self.monthly_cost:.2f}",
            attributes={
                "friendly_name": "AC Monthly Running Cost",
                "unit_of_measurement": "$",
                "icon": "mdi:currency-usd",
            },
        )

    def reset_daily_cost(self, kwargs):
        """Resets the daily cost at a specific time after midnight."""
        self.daily_cost = 0.0
        self.previous_runtime = (
            0.0  # Reset previous runtime to avoid calculating cost from 0 next update
        )
        self.log("Daily AC cost reset to $0.00.")

    def reset_monthly_cost_on_new_month(self, kwargs):
        """Resets the monthly cost on the first of the month."""
        now = datetime.now()
        if now.month != self.current_month:
            self.log(
                f"Month changed from {self.current_month} to {now.month}. Resetting monthly cost."
            )
            self.monthly_cost = 0.0
            self.current_month = now.month
