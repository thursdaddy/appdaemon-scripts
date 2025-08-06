from datetime import datetime, time

import appdaemon.plugins.hass.hassapi as hass


class HVACCostTracker(hass.Hass):
    def initialize(self):
        self.runtime_cost = 0.0
        self.monthly_cost = 0.0
        self.current_month = datetime.now().month
        self.peak_rates_summer = {"start": time(14, 0, 0), "end": time(20, 0, 0)}
        self.peak_rates_winter_morning = {"start": time(5, 0, 0), "end": time(9, 0, 0)}
        self.peak_rates_winter_evening = {
            "start": time(17, 0, 0),
            "end": time(21, 0, 0),
        }
        self.summer_months = range(5, 11)
        self.estimated_wattage_kw = 4.8
        self.previous_runtime = 0.0

        self.listen_state(self.cooling_runtime_change, "sensor.hvac_cooling")
        self.run_daily(
            self.reset_runtime_cost, time(0, 1, 0)
        )  # Reset daily cost shortly after midnight

    def cooling_runtime_change(self, entity, attribute, old, new, kwargs):
        try:
            new_runtime = float(new)
            old_runtime = float(old) if old is not None else 0.0
            runtime_difference = new_runtime - old_runtime

            if runtime_difference > 0:
                cost = self.calculate_cost(runtime_difference)
                self.runtime_cost = cost
                self.log(
                    f"AC runtime increased by {runtime_difference:.3f} hours. Cost: ${cost:.3f}."
                )
                self.update_cost_sensors()
            elif new_runtime < old_runtime:
                return

            self.previous_runtime = new_runtime

        except ValueError:
            self.log(
                f"Error: Could not convert runtime values to float. Old: {old}, New: {new}"
            )

    def calculate_cost(self, runtime_difference):
        energy_used_kwh = self.estimated_wattage_kw * runtime_difference
        rate = self.get_current_rate()
        cost = energy_used_kwh * rate
        self.log(cost)
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
                return 0.25
            else:
                return 0.10
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
                return 0.10

    def update_cost_sensors(self):
        self.set_state(
            "sensor.hvac_cost_tracker",
            state=f"{self.runtime_cost:.3f}",
            attributes={
                "friendly_name": "AC Daily Running Cost",
                "unit_of_measurement": "$",
                "icon": "mdi:currency-usd",
            },
        )

    def reset_runtime_cost(self, kwargs):
        """Resets the daily cost at a specific time after midnight."""
        self.runtime_cost = 0.0
        self.previous_runtime = (
            0.0  # Reset previous runtime to avoid calculating cost from 0 next update
        )
        self.log("Daily AC cost reset to $0.00.")
