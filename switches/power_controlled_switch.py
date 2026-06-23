import hassapi as hass


class PowerControlledSwitch(hass.Hass):
    """
    Generic controller to turn a switch/light ON or OFF based on power consumption thresholds.
    """

    def initialize(self):
        # Read args
        self.power_entity = self.args.get("power_entity")
        self.switch_entity = self.args.get("switch_entity")
        self.automation_switch = self.args.get("automation_switch")

        self.threshold_on = float(self.args.get("threshold_on", 10.0))
        self.threshold_off = float(self.args.get("threshold_off", 5.0))

        self.delay_on = int(self.args.get("delay_on", 0))
        self.delay_off = int(self.args.get("delay_off", 30))
        self._debug_mode = self.args.get("debug", False)

        # Setup state
        self.timer_handle_on = None
        self.timer_handle_off = None

        if not self.power_entity or not self.switch_entity:
            self.error("power_entity and switch_entity must be provided in configuration.")
            return

        # Log configuration loading
        self.log("============================")
        self.log(f"  Power Entity:  {self.power_entity}")
        self.log(f"  Switch Entity: {self.switch_entity}")
        self.log(f"  Threshold On:  {self.threshold_on}W")
        self.log(f"  Threshold Off: {self.threshold_off}W")
        self.log(f"  Delay On:      {self.delay_on}s")
        self.log(f"  Delay Off:     {self.delay_off}s")
        if self.automation_switch:
            self.log(f"  Automation:    {self.automation_switch}")
        self.log(f"  Debug Mode:    {'ENABLED' if self._debug_mode else 'DISABLED'}")
        self.log("=== Configuration Loaded ===")

        self.listen_state(self.power_changed, self.power_entity)
        self.sync_to_power("Startup")

    def debug_log(self, message):
        if self._debug_mode:
            self.log(f"[DEBUG] {message}")

    def sync_to_power(self, context):
        """Aligns the switch/light state with current power consumption on startup/change."""
        try:
            current_power = self.get_state(self.power_entity)
            if current_power in [None, "unavailable", "unknown"]:
                self.debug_log(f"Sync ({context}): Sensor unavailable. Skipping.")
                return

            power_float = float(current_power)
            current_state = self.get_state(self.switch_entity)

            if power_float > self.threshold_on and current_state == "off":
                self.log(f"Sync ({context}): Power is {power_float}W. Turning ON {self.switch_entity}.")
                self.turn_on(self.switch_entity)
            elif power_float < self.threshold_off and current_state == "on":
                self.log(f"Sync ({context}): Power is {power_float}W. Turning OFF {self.switch_entity}.")
                self.turn_off(self.switch_entity)
            else:
                self.debug_log(f"Sync ({context}): Current state matches power state ({power_float}W).")
        except (ValueError, TypeError) as e:
            self.log(f"Sync Error: {e}", level="WARNING")

    def power_changed(self, entity, attribute, old, new, kwargs):
        try:
            if new in [None, "unavailable", "unknown"] or old in [None, "unavailable", "unknown"]:
                return

            new_val = float(new)
            old_val = float(old)

            is_rising = new_val > self.threshold_on and old_val <= self.threshold_on
            is_falling = new_val < self.threshold_off and old_val >= self.threshold_off

            if not is_rising and not is_falling:
                self.debug_log(f"Power update: {new_val}W. No threshold crossed. Returning.")
                return

            self.debug_log(f"Power threshold crossed! {old_val}W -> {new_val}W. Checking automation switch...")

            # Automation switch check
            if self.automation_switch:
                auto_state = self.get_state(self.automation_switch)
                if auto_state != "on":
                    self.debug_log(f"Veto: Automation switch {self.automation_switch} is {auto_state}.")
                    return

            # --- RISING EDGE ---
            if is_rising:
                self.debug_log("Power is rising. Preparing to turn switch ON.")
                if self.timer_handle_off:
                    self.debug_log("Canceling pending OFF timer.")
                    self.cancel_timer(self.timer_handle_off)
                    self.timer_handle_off = None

                current_state = self.get_state(self.switch_entity)
                if current_state == "off":
                    if not self.timer_handle_on:
                        self.debug_log(f"Starting {self.delay_on}s ON timer.")
                        self.timer_handle_on = self.run_in(self.turn_on_target, self.delay_on)
                else:
                    self.debug_log("Switch is already ON. No timer needed.")

            # --- FALLING EDGE ---
            elif is_falling:
                self.debug_log("Power is falling. Preparing to turn switch OFF.")
                if self.timer_handle_on:
                    self.debug_log("Canceling pending ON timer.")
                    self.cancel_timer(self.timer_handle_on)
                    self.timer_handle_on = None

                current_state = self.get_state(self.switch_entity)
                if current_state == "on":
                    if not self.timer_handle_off:
                        self.debug_log(f"Starting {self.delay_off}s OFF timer.")
                        self.timer_handle_off = self.run_in(self.turn_off_target, self.delay_off)
                else:
                    self.debug_log("Switch is already OFF. No timer needed.")

        except (ValueError, TypeError) as e:
            self.log(f"Error handling power change: {e}", level="WARNING")

    def turn_on_target(self, kwargs):
        self.log(f"Executing turn-on: {self.switch_entity}")
        self.turn_on(self.switch_entity)
        self.timer_handle_on = None

    def turn_off_target(self, kwargs):
        self.log(f"Executing turn-off: {self.switch_entity}")
        self.turn_off(self.switch_entity)
        self.timer_handle_off = None
