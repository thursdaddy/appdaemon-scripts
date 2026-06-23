import appdaemon.plugins.hass.hassapi as hass


class HVACCostTracker(hass.Hass):
    def initialize(self):
        # Read rates and wattage from self.args (configured via apps.yaml)
        self.estimated_wattage_kw = float(self.args.get("estimated_wattage_kw", 4.8))
        self.rates = self.args.get("rates", {
            "summer": {"peak": 0.25, "off_peak": 0.10},
            "winter": {"peak": 0.12, "off_peak": 0.10}
        })
        self.summer_months = range(5, 11)

        # Parse On-Peak Windows from tracker config
        self.on_peak_windows = {}
        schedule_arg = self.args.get("schedule", {})
        on_peak_arg = schedule_arg.get("on_peak", {})

        for season in ["summer", "winter"]:
            season_on_peak = on_peak_arg.get(season, {})
            hours = season_on_peak.get("hours", [])
            if hours:
                self.on_peak_windows[season] = hours

        # Fallback to default hard-coded windows if none configured
        if "summer" not in self.on_peak_windows:
            self.on_peak_windows["summer"] = ["14:00:00-20:00:00"]
        if "winter" not in self.on_peak_windows:
            self.on_peak_windows["winter"] = ["05:00:00-09:00:00", "17:00:00-21:00:00"]

        # Restore daily cost from Home Assistant state if possible (persists across restarts)
        self.runtime_cost = 0.0
        current_cost_state = self.get_state("sensor.hvac_cost_tracker")
        try:
            if current_cost_state not in [None, "unavailable", "unknown"]:
                self.runtime_cost = float(current_cost_state)
                self.log(f"Restored daily cost from sensor.hvac_cost_tracker: ${self.runtime_cost:.3f}")
        except ValueError:
            self.log(f"Could not restore daily cost from sensor.hvac_cost_tracker (state: {current_cost_state}). Starting at $0.00.")

        # Restore previous runtime to compare against
        self.previous_runtime = None
        current_runtime_state = self.get_state("sensor.hvac_cooling")
        try:
            if current_runtime_state not in [None, "unavailable", "unknown"]:
                self.previous_runtime = float(current_runtime_state)
                self.log(f"Restored previous runtime tracker state: {self.previous_runtime} hours.")
        except ValueError:
            self.log(f"Could not restore previous runtime from sensor.hvac_cooling (state: {current_runtime_state}).")

        self.listen_state(self.cooling_runtime_change, "sensor.hvac_cooling")
        
        # Reset daily cost exactly at midnight
        self.run_daily(self.reset_runtime_cost, "00:00:00")
        
        # Ensure sensors are updated on startup
        self.update_cost_sensors()

    def cooling_runtime_change(self, entity, attribute, old, new, kwargs):
        try:
            # Guard against invalid/empty/startup states
            if new in [None, "unavailable", "unknown"]:
                return

            new_runtime = float(new)
            
            # If self.previous_runtime is not initialized, set it to the new runtime and return
            if self.previous_runtime is None:
                self.previous_runtime = new_runtime
                self.log(f"Initialized tracking runtime at {new_runtime} hours.")
                return

            runtime_difference = new_runtime - self.previous_runtime

            if runtime_difference > 0:
                cost_slice = self.calculate_cost(runtime_difference)
                self.runtime_cost += cost_slice
                self.log(
                    f"AC runtime increased by {runtime_difference:.3f} hours (slice cost: ${cost_slice:.3f}). Daily Cost: ${self.runtime_cost:.3f}.",
                    level="DEBUG"
                )
                self.previous_runtime = new_runtime
                self.update_cost_sensors()
            elif new_runtime < self.previous_runtime:
                # Handle sensor resets (e.g., at midnight or manual reset)
                self.log(f"Sensor reset detected (new_runtime: {new_runtime} < previous: {self.previous_runtime}). Resetting previous_runtime tracker.")
                self.previous_runtime = new_runtime

        except ValueError:
            self.log(
                f"Error: Could not convert runtime values to float. New: {new}",
                level="WARNING"
            )

    def calculate_cost(self, runtime_difference):
        energy_used_kwh = self.estimated_wattage_kw * runtime_difference
        rate = self.get_current_rate()
        cost = energy_used_kwh * rate
        return cost

    def get_current_rate(self):
        now = self.datetime()
        month = now.month
        season = "summer" if month in self.summer_months else "winter"
        
        season_rates = self.rates.get(season, {"peak": 0.25, "off_peak": 0.10} if season == "summer" else {"peak": 0.12, "off_peak": 0.10})

        if self.is_now_peak(season):
            return float(season_rates.get("peak", 0.25 if season == "summer" else 0.12))
        else:
            return float(season_rates.get("off_peak", 0.10))

    def is_now_peak(self, season):
        """Returns True if current time matches any On-Peak window"""
        windows = self.on_peak_windows.get(season, [])
        for window in windows:
            start, end = window.split("-")
            if self.now_is_between(start, end):
                return True
        return False

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
        self.previous_runtime = 0.0
        self.log("Daily AC cost reset to $0.00.")
        self.update_cost_sensors()
