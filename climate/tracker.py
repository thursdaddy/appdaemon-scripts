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

        # Parse E-16 Windows from tracker config
        schedule_arg = self.args.get("schedule", {})
        
        on_peak_arg = schedule_arg.get("on_peak", {})
        self.on_peak_hours = on_peak_arg.get("hours", ["17:00:00-22:00:00"])
        self.on_peak_weekdays_only = on_peak_arg.get("weekdays_only", True)

        super_off_peak_arg = schedule_arg.get("super_off_peak", {})
        self.super_off_peak_hours = super_off_peak_arg.get("hours", ["08:00:00-15:00:00"])
        self.super_off_peak_weekdays_only = super_off_peak_arg.get("weekdays_only", False)

        # Restore daily costs and sub-tier costs from Home Assistant state
        self.runtime_cost = self.restore_cost_sensor("sensor.hvac_cost_tracker")
        self.peak_cost = self.restore_cost_sensor("sensor.hvac_cost_peak")
        self.off_peak_cost = self.restore_cost_sensor("sensor.hvac_cost_off_peak")
        self.super_off_peak_cost = self.restore_cost_sensor("sensor.hvac_cost_super_off_peak")

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

    def restore_cost_sensor(self, entity_id):
        current_state = self.get_state(entity_id)
        try:
            if current_state not in [None, "unavailable", "unknown"]:
                val = float(current_state)
                self.log(f"Restored daily cost from {entity_id}: ${val:.3f}")
                return val
        except ValueError:
            self.log(f"Could not restore daily cost from {entity_id} (state: {current_state}). Starting at $0.00.")
        return 0.0

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
                
                # Accrue cost slice to the active tariff tier
                if self.is_now_peak():
                    self.peak_cost += cost_slice
                elif self.is_now_super_off_peak():
                    self.super_off_peak_cost += cost_slice
                else:
                    self.off_peak_cost += cost_slice

                self.log(
                    f"AC runtime increased by {runtime_difference:.3f} hours (slice cost: ${cost_slice:.3f}). Daily Cost: ${self.runtime_cost:.3f}.",
                    level="DEBUG"
                )
                self.previous_runtime = new_runtime
                self.update_cost_sensors()
            elif new_runtime < self.previous_runtime:
                # Handle sensor resets (only allow near midnight)
                now_time = self.time()
                is_near_midnight = (now_time.hour == 0 and now_time.minute < 5) or (now_time.hour == 23 and now_time.minute > 55)
                if is_near_midnight:
                    self.log(f"Sensor reset detected near midnight (new_runtime: {new_runtime} < previous: {self.previous_runtime}). Resetting previous_runtime tracker.")
                    self.previous_runtime = new_runtime
                else:
                    self.log(f"Ignored runtime decrease (possible glitch/reboot): {self.previous_runtime} -> {new_runtime}", level="WARNING")

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
        
        default_rates = {
            "summer": {"peak": 0.1257, "off_peak": 0.0995, "super_off_peak": 0.0393},
            "winter": {"peak": 0.1051, "off_peak": 0.0907, "super_off_peak": 0.0425}
        }
        season_rates = self.rates.get(season, default_rates[season])

        if self.is_now_peak():
            return float(season_rates.get("peak", default_rates[season]["peak"]))
        elif self.is_now_super_off_peak():
            return float(season_rates.get("super_off_peak", default_rates[season]["super_off_peak"]))
        else:
            return float(season_rates.get("off_peak", default_rates[season]["off_peak"]))

    def is_now_peak(self):
        """Returns True if current time matches On-Peak window"""
        if self.on_peak_weekdays_only:
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
        self.set_state(
            "sensor.hvac_cost_peak",
            state=f"{self.peak_cost:.3f}",
            attributes={
                "friendly_name": "AC Daily Peak Cost",
                "unit_of_measurement": "$",
                "icon": "mdi:currency-usd",
            },
        )
        self.set_state(
            "sensor.hvac_cost_off_peak",
            state=f"{self.off_peak_cost:.3f}",
            attributes={
                "friendly_name": "AC Daily Off-Peak Cost",
                "unit_of_measurement": "$",
                "icon": "mdi:currency-usd",
            },
        )
        self.set_state(
            "sensor.hvac_cost_super_off_peak",
            state=f"{self.super_off_peak_cost:.3f}",
            attributes={
                "friendly_name": "AC Daily Super Off-Peak Cost",
                "unit_of_measurement": "$",
                "icon": "mdi:currency-usd",
            },
        )

    def reset_runtime_cost(self, kwargs):
        """Resets the daily cost at a specific time after midnight."""
        self.runtime_cost = 0.0
        self.peak_cost = 0.0
        self.off_peak_cost = 0.0
        self.super_off_peak_cost = 0.0
        self.previous_runtime = 0.0
        self.log("Daily AC cost reset to $0.00.")
        self.update_cost_sensors()
