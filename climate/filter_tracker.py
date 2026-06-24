import datetime
import appdaemon.plugins.hass.hassapi as hass


class HVACFilterTracker(hass.Hass):
    def initialize(self):
        # Configure entities
        self.cooling_runtime_sensor = self.args.get("cooling_runtime_sensor", "sensor.hvac_cooling")
        self.ticket_boolean = self.args.get("ticket_boolean", "input_boolean.hvac_filter_replace")
        self.last_changed_datetime = self.args.get("last_changed_datetime", "input_datetime.hvac_filter_last_changed")
        self.accumulated_runtime_number = self.args.get("accumulated_runtime_number", "input_number.hvac_filter_runtime")
        self.runtime_threshold_number = self.args.get("runtime_threshold_number", "input_number.hvac_filter_runtime_threshold")
        self.days_threshold_number = self.args.get("days_threshold_number", "input_number.hvac_filter_days_threshold")

        # Initialize tracking state
        self.previous_runtime = None
        current_state = self.get_state(self.cooling_runtime_sensor)
        try:
            if current_state not in [None, "unavailable", "unknown"]:
                self.previous_runtime = float(current_state)
                self.log(f"Initialized filter tracker with current daily runtime: {self.previous_runtime} hours.")
        except ValueError:
            self.log(f"Could not convert runtime state: {current_state} to float. Starting fresh.")

        # Event Listeners
        self.listen_state(self.runtime_changed, self.cooling_runtime_sensor)
        self.listen_state(self.ticket_changed, self.ticket_boolean)

        # Midnight Check for calendar age
        self.run_daily(self.check_calendar_age, "00:00:05")

        # Run immediate startup check
        self.check_calendar_age(None)

    def runtime_changed(self, entity, attribute, old, new, kwargs):
        if new in [None, "unavailable", "unknown"]:
            return

        try:
            new_val = float(new)

            if self.previous_runtime is None:
                self.previous_runtime = new_val
                return

            # If daily sensor reset (midnight)
            if new_val < self.previous_runtime:
                self.log(f"Daily runtime sensor reset detected: {self.previous_runtime} -> {new_val}")
                self.previous_runtime = new_val
                return

            delta = new_val - self.previous_runtime
            if delta > 0:
                # Fetch current accumulator
                accum_str = self.get_state(self.accumulated_runtime_number)
                accum_val = 0.0
                try:
                    if accum_str not in [None, "unavailable", "unknown"]:
                        accum_val = float(accum_str)
                except ValueError:
                    pass

                new_accum = accum_val + delta
                self.set_state(self.accumulated_runtime_number, state=f"{new_accum:.3f}")
                self.log(f"Accrued {delta:.3f} cooling hours to filter. Total runtime: {new_accum:.3f} hours.", level="DEBUG")

                # Check threshold
                threshold_str = self.get_state(self.runtime_threshold_number)
                threshold_val = 300.0
                try:
                    if threshold_str not in [None, "unavailable", "unknown"]:
                        threshold_val = float(threshold_str)
                except ValueError:
                    pass

                if new_accum >= threshold_val:
                    self.log(f"Filter runtime {new_accum:.1f}h meets or exceeds threshold {threshold_val}h. Activating alert.")
                    self.trigger_alert()

            self.previous_runtime = new_val
        except ValueError:
            self.log(f"Error converting runtime value to float: {new}", level="WARNING")

    def check_calendar_age(self, kwargs):
        last_changed_str = self.get_state(self.last_changed_datetime)
        if last_changed_str in [None, "unavailable", "unknown"]:
            self.log(f"Cannot perform age check: last changed state is {last_changed_str}.", level="WARNING")
            return

        try:
            # Parse only YYYY-MM-DD (ignoring time if present)
            date_part = last_changed_str.split(" ")[0]
            last_changed_date = datetime.datetime.strptime(date_part, "%Y-%m-%d").date()
            today = self.datetime().date()
            days_elapsed = (today - last_changed_date).days

            # Get threshold
            threshold_str = self.get_state(self.days_threshold_number)
            threshold_val = 90
            try:
                if threshold_str not in [None, "unavailable", "unknown"]:
                    threshold_val = int(float(threshold_str))
            except ValueError:
                pass

            self.log(f"Filter status: {days_elapsed} days elapsed since last replacement ({last_changed_str}). Threshold: {threshold_val} days.")

            if days_elapsed >= threshold_val:
                self.log(f"Filter age ({days_elapsed} days) meets or exceeds threshold ({threshold_val} days). Activating alert.")
                self.trigger_alert()
        except ValueError as e:
            self.log(f"Error parsing date string '{last_changed_str}': {e}", level="WARNING")

    def trigger_alert(self):
        ticket_state = self.get_state(self.ticket_boolean)
        if ticket_state != "on":
            self.log("Action: Setting filter ticket boolean to ON.")
            self.set_state(self.ticket_boolean, state="on")

    def ticket_changed(self, entity, attribute, old, new, kwargs):
        if old == "on" and new == "off":
            self.reset_filter_metrics()

    def reset_filter_metrics(self):
        self.log("Action: Resetting filter metrics (Filter marked as replaced).")
        # Reset runtime hours
        self.set_state(self.accumulated_runtime_number, state="0.0")
        
        # Reset last changed date
        today_str = self.datetime().date().isoformat()
        self.set_state(self.last_changed_datetime, state=today_str)
        self.log(f"Filter runtime reset to 0. Last changed date set to {today_str}.")
