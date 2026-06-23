import hassapi as hass


class AwayMode(hass.Hass):
    def initialize(self):
        # Configuration
        self._location_entity = "device_tracker.pixel_7_pro"
        self._hvac_entity = "climate.nest"
        self._all_lights_switch = "input_boolean.lights_all"
        self._away_temp = 85
        self._debug_mode = self.args.get("debug", False)

        # --- Configuration Output ---
        self.log("============================")
        self.log(f"  HVAC Target:   {self._away_temp}F")
        self.log(f"  Master Light:  {self._all_lights_switch}")
        self.log(f"  Tracker:       {self._location_entity}")
        self.log(f"  Debug Mode:    {'ENABLED' if self._debug_mode else 'DISABLED'}")
        self.log("=========  CONFIG  =========")

        self.listen_state(self.departure_detected, self._location_entity)

    def debug_log(self, message):
        if self._debug_mode:
            self.log(f"[DEBUG] {message}")

    def departure_detected(self, entity, attribute, old, new, kwargs):
        # Guard against tracker transitions that include None
        if not new or not old:
            return

        if new == "away" and old == "home":
            self.log("Departure Detected: Commencing Away automations.")

            # 1. Turn off all lights
            self.log(f"Action: Turning off {self._all_lights_switch}")
            self.turn_off(self._all_lights_switch)

            # 2. Set HVAC
            try:
                self.log(f"Action: Setting {self._hvac_entity} to {self._away_temp}")
                self.call_service(
                    "climate/set_temperature",
                    entity_id=self._hvac_entity,
                    temperature=self._away_temp,
                )
            except Exception as e:
                self.log(f"[ERR] HVAC Service Call Failed: {e}")

            # 3. Notify
            self.call_service(
                "notify/gotify",
                title="AWAY",
                message="Lights OFF, HVAC set to ECO mode.",
            )
