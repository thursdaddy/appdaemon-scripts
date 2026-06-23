import hassapi as hass


class PrinterLights(hass.Hass):
    """
    Turns ON printer_lights when printer current consumption goes ABOVE Threshold
    Turns OFF printer_lights when printer current consumption goes BELOW Threshold
    """

    def initialize(self):
        self.printer_consumption_entity = "sensor.3d_printer_current_consumption"
        self.printer_lights_entity = "switch.printer_lights"

        self.consumption_threshold_on = 10
        self.consumption_threshold_off = 5

        self.delay_on = 5
        self.delay_off = 10

        self.timer_handle_on = None
        self.timer_handle_off = None

        # Listen for any state change of the consumption sensor
        self.listen_state(
            self.printer_consumption_changed, self.printer_consumption_entity
        )

        self.log("Printer Light Automation Initialized.")
        self.sync_lights_to_power("Startup")

    def sync_lights_to_power(self, context):
        """Helper to align light state with current power draw"""
        try:
            current_power = self.get_state(self.printer_consumption_entity)
            if current_power in [None, "unavailable", "unknown"]:
                return

            power_float = float(current_power)
            light_state = self.get_state(self.printer_lights_entity)

            if power_float > self.consumption_threshold_on and light_state == "off":
                self.log(f"{context}: Power is {power_float}W. Turning lights ON.")
                self.turn_on(self.printer_lights_entity)

            elif power_float < self.consumption_threshold_off and light_state == "on":
                self.log(f"{context}: Power is {power_float}W. Turning lights OFF.")
                self.turn_off(self.printer_lights_entity)
        except (ValueError, TypeError) as e:
            self.log(f"Error in sync_lights: {e}")
        try:
            if current_power not in [None, "unavailable", "unknown"]:
                power_float = float(current_power)
                light_state = self.get_state(self.printer_lights_entity)

                if power_float > self.consumption_threshold_on and light_state == "off":
                    self.log(
                        f"Startup: Printer is already active ({power_float}W). Turning lights on."
                    )
                    self.turn_on(self.printer_lights_entity)
                elif (
                    power_float < self.consumption_threshold_off and light_state == "on"
                ):
                    self.log(
                        f"Startup: Printer is already idle ({power_float}W). Starting OFF timer."
                    )
                    self.turn_off_lights
        except (ValueError, TypeError):
            self.log("Startup: Could not parse current power value.")

    def printer_consumption_changed(self, entity, attribute, old, new, kwargs):
        try:
            # Guard against bad data
            if new in [None, "unavailable", "unknown"] or old in [
                None,
                "unavailable",
                "unknown",
            ]:
                return

            new_val = float(new)
            old_val = float(old)

            # --- RISING EDGE: Crossed ABOVE the ON threshold ---
            if (
                new_val > self.consumption_threshold_on
                and old_val <= self.consumption_threshold_on
            ):
                self.log(
                    f"Power Rising: {old_val}W -> {new_val}W. Crossing {self.consumption_threshold_on}W threshold."
                )

                # Cleanup any pending "Turn Off" timers
                if self.timer_handle_off:
                    self.log("Cancelling pending OFF timer.")
                    self.cancel_timer(self.timer_handle_off)
                    self.timer_handle_off = None

                # Check physical light state
                if self.get_state(self.printer_lights_entity) == "off":
                    if not self.timer_handle_on:
                        self.log(
                            f"Lights are OFF. Starting ON timer for {self.delay_on}s."
                        )
                        self.timer_handle_on = self.run_in(
                            self.turn_on_lights, self.delay_on
                        )
                else:
                    self.log("Lights are already ON. No action taken.")

            # --- FALLING EDGE: Crossed BELOW the OFF threshold ---
            elif (
                new_val < self.consumption_threshold_off
                and old_val >= self.consumption_threshold_off
            ):
                self.log(
                    f"Power Falling: {old_val}W -> {new_val}W. Crossing {self.consumption_threshold_off}W threshold."
                )

                # Cleanup any pending "Turn On" timers
                if self.timer_handle_on:
                    self.log("Cancelling pending ON timer.")
                    self.cancel_timer(self.timer_handle_on)
                    self.timer_handle_on = None

                # Check physical light state
                if self.get_state(self.printer_lights_entity) == "on":
                    if not self.timer_handle_off:
                        self.log(
                            f"Lights are ON. Starting OFF timer for {self.delay_off}s."
                        )
                        self.timer_handle_off = self.run_in(
                            self.turn_off_lights, self.delay_off
                        )
                else:
                    self.log("Lights are already OFF. No action taken.")

        except (ValueError, TypeError) as e:
            self.log(f"Error processing power change: {e}", level="WARNING")

    def turn_on_lights(self, kwargs):
        self.log("Execution: Turning printer lights ON.")
        self.turn_on(self.printer_lights_entity)
        self.timer_handle_on = None

    def turn_off_lights(self, kwargs):
        self.log("Execution: Turning printer lights OFF.")
        self.turn_off(self.printer_lights_entity)
        self.timer_handle_off = None
