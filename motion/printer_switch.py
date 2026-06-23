import json

import appdaemon.plugins.hass.hassapi as hass


class MotionSwitchPrinter(hass.Hass):

    def initialize(self):
        # Initialize APIs
        self.hass_api = self.get_plugin_api("HASS")
        self.mqtt_api = self.get_plugin_api("MQTT")

        # Variables set in apps.yaml
        self._motion_sensor = self.args.get("motion_sensor")
        self._switches = self.args.get("switches", [])
        self._delay = self.args.get("delay", 60)
        self._debug_mode = self.args.get("debug", False)
        self._power_sensor = "sensor.3d_printer_current_consumption"

        self.timer_handler = None

        # --- Configuration Output (Ordered for standard Log Viewers) ---
        # We log the "Header" first so it stays at the top of the block
        self.log("============================")
        self.log(f"  Delay:         {self._delay} seconds")
        self.log(f"  Switches:      {self._switches}")
        self.log(f"  Motion Sensor: {self._motion_sensor}")
        self.log(f"  Debug Mode:    {'ENABLED' if self._debug_mode else 'DISABLED'}")
        self.log("=== Configuration Loaded ===")

        if not self._motion_sensor:
            self.log("[ERR] motion_sensor not defined in apps.yaml")
            return

        self.mqtt_api.listen_event(
            self.mqtt_callback, "MQTT_MESSAGE", topic=self._motion_sensor
        )

    def debug_log(self, message):
        if self._debug_mode:
            self.log(f"[DEBUG] {message}")

    def mqtt_callback(self, event_name, data, kwargs):
        self.debug_log(f"Incoming MQTT data: {data}")

        try:
            payload = json.loads(data["payload"])

            if "occupancy" in payload:
                if payload["occupancy"] is True:
                    self.log("Event: Motion Detected")

                    if self.timer_handler and self.info_timer(self.timer_handler) is not None:
                        self.debug_log("Existing timer found. Canceling.")
                        self.cancel_timer(self.timer_handler)

                    self.turn_on_switches()

                elif payload["occupancy"] is False:
                    self.log("Event: Motion Cleared")
                    self.debug_log(f"Scheduling turn-off in {self._delay}s")

                    self.timer_handler = self.run_in(
                        self.turn_off_switches, self._delay
                    )
            else:
                self.debug_log(f"Occupancy key missing in payload: {payload}")

        except Exception as e:
            self.log(f"[ERR] Error in mqtt_callback: {e}")

    def turn_on_switches(self):
        for switch in self._switches:
            state = self.get_state(switch)
            self.debug_log(f"Current state of {switch}: {state}")

            if state == "off":
                self.log(f"Action: Turning ON {switch}")
                self.turn_on(switch)

    def turn_off_switches(self, kwargs):
        self.debug_log("Timer finished. Checking power consumption before turning off.")

        try:
            power_state = self.get_state(self._power_sensor)
            power_value = (
                float(power_state)
                if power_state not in [None, "unavailable", "unknown"]
                else 0.0
            )

            self.debug_log(f"Current power consumption: {power_value}W")

            if power_value > 5:
                self.debug_log(f"Hold: Power is {power_value}W (> 5W). Keeping lights ON.")
                # Reschedule check in 60s
                self.timer_handler = self.run_in(self.turn_off_switches, 60)
                return

            for switch in self._switches:
                self.log(f"Action: Turning OFF {switch}")
                self.turn_off(switch)

        except Exception as e:
            self.log(f"[ERR] Error in turn_off_switches: {e}")
