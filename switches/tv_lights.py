import hassapi as hass


class TvLights(hass.Hass):
    """
    Turns on tv_lights based on power consumption using Edge-Detection.
    """

    def initialize(self):
        # Configuration
        self.tv_consumption_entity = "sensor.living_room_tv_current_consumption"
        self.tv_lights_entity = "light.tv_lights"
        self._automation_switch = "input_boolean.lights_tv_automation"

        self.consumption_threshold_on = 30
        self.consumption_threshold_off = 25
        self.delay_on = 0
        self.delay_off = 30

        self._debug_mode = self.args.get("debug", False)

        self.timer_handle_on = None
        self.timer_handle_off = None

        # --- Configuration Output ---
        self.log("============================")
        self.log(f"  Power Entity:  {self.tv_consumption_entity}")
        self.log(f"  Lights Entity: {self.tv_lights_entity}")
        self.log(f"  Threshold On:  {self.consumption_threshold_on}W")
        self.log(f"  Threshold Off: {self.consumption_threshold_off}W")
        self.log(f"  Delay On:      {self.delay_on}s")
        self.log(f"  Delay Off:     {self.delay_off}s")
        self.log(f"  Automation:    {self._automation_switch}")
        self.log(f"  Debug Mode:    {'ENABLED' if self._debug_mode else 'DISABLED'}")
        self.log("=== Configuration Loaded ===")

        self.listen_state(self.tv_consumption_changed, self.tv_consumption_entity)
        self.sync_lights_to_power("Startup")

    def debug_log(self, message):
        if self._debug_mode:
            self.log(f"[DEBUG] {message}")

    def sync_lights_to_power(self, context):
        """Helper to align light state with current power draw"""
        try:
            current_power = self.get_state(self.tv_consumption_entity)
            if current_power in [None, "unavailable", "unknown"]:
                self.debug_log(f"Sync ({context}): Sensor unavailable. Skipping.")
                return

            power_float = float(current_power)
            light_state = self.get_state(self.tv_lights_entity)

            if power_float > self.consumption_threshold_on and light_state == "off":
                self.log(
                    f"Sync ({context}): TV is ON ({power_float}W). Syncing lights ON."
                )
                self.turn_on(self.tv_lights_entity)
            elif power_float < self.consumption_threshold_off and light_state == "on":
                self.log(
                    f"Sync ({context}): TV is OFF ({power_float}W). Syncing lights OFF."
                )
                self.turn_off(self.tv_lights_entity)
            else:
                self.debug_log(
                    f"Sync ({context}): Lights already match power state ({power_float}W)."
                )
        except (ValueError, TypeError) as e:
            self.log(f"Sync Error: {e}")

    def tv_consumption_changed(self, entity, attribute, old, new, kwargs):
        try:
            if new in [None, "unavailable", "unknown"] or old in [
                None,
                "unavailable",
                "unknown",
            ]:
                return

            new_val = float(new)
            old_val = float(old)

            # Edge Detection Logic
            is_rising = (
                new_val > self.consumption_threshold_on
                and old_val <= self.consumption_threshold_on
            )
            is_falling = (
                new_val < self.consumption_threshold_off
                and old_val >= self.consumption_threshold_off
            )

            if not is_rising and not is_falling:
                # This log helps you see that the script is alive but intentionally staying quiet
                self.debug_log(
                    f"Power update: {new_val}W. No threshold crossed. Returning."
                )
                return

            self.debug_log(
                f"THINKING: Threshold crossed! {old_val}W -> {new_val}W. Checking master switch..."
            )

            # Master Check
            auto_switch = self.get_state(self._automation_switch)
            if auto_switch != "on":
                self.debug_log(
                    f"THINKING: I want to act, but {self._automation_switch} is {auto_switch}. Vetoing action."
                )
                return

            # --- RISING EDGE ---
            if is_rising:
                self.debug_log(
                    "THINKING: Power is rising. Preparing to turn on lights."
                )
                if self.timer_handle_off:
                    self.debug_log("THINKING: Found a pending OFF timer. Canceling it.")
                    self.cancel_timer(self.timer_handle_off)
                    self.timer_handle_off = None

                current_light = self.get_state(self.tv_lights_entity)
                if current_light == "off":
                    if not self.timer_handle_on:
                        self.debug_log(
                            f"THINKING: Lights are {current_light}. Starting {self.delay_on}s ON timer."
                        )
                        self.timer_handle_on = self.run_in(
                            self.turn_on_lights, self.delay_on
                        )
                else:
                    self.debug_log(
                        f"THINKING: Lights are already {current_light}. No need to start timer."
                    )

            # --- FALLING EDGE ---
            elif is_falling:
                self.debug_log(
                    "THINKING: Power is falling. Preparing to turn off lights."
                )
                if self.timer_handle_on:
                    self.debug_log("THINKING: Found a pending ON timer. Canceling it.")
                    self.cancel_timer(self.timer_handle_on)
                    self.timer_handle_on = None

                current_light = self.get_state(self.tv_lights_entity)
                if current_light == "on":
                    if not self.timer_handle_off:
                        self.debug_log(
                            f"THINKING: Lights are {current_light}. Starting {self.delay_off}s OFF timer."
                        )
                        self.timer_handle_off = self.run_in(
                            self.turn_off_lights, self.delay_off
                        )
                else:
                    self.debug_log(
                        f"THINKING: Lights are already {current_light}. No need to start timer."
                    )

        except (ValueError, TypeError) as e:
            self.log(f"[ERR] Thinking error: {e}")

    def turn_on_lights(self, kwargs):
        self.log(
            f"EXECUTE: Power > {self.consumption_threshold_on}W. Turning ON {self.tv_lights_entity}"
        )
        self.turn_on(self.tv_lights_entity)
        self.timer_handle_on = None

    def turn_off_lights(self, kwargs):
        self.log(
            f"EXECUTE: Power < {self.consumption_threshold_off}W. Turning OFF {self.tv_lights_entity}"
        )
        self.turn_off(self.tv_lights_entity)
        self.timer_handle_off = None
