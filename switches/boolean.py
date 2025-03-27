import subprocess

import appdaemon.plugins.hass.hassapi as hass
import requests


class BooleanControlLights(hass.Hass):

    def initialize(self):
        self._boolean = self.args.get("boolean")
        self._entities = self.args.get("entities")

        self.listen_state(self.callback, self._boolean)

    def callback(self, entity, attribute, old, new, kwargs):
        if new == "off":
            self.turn_off_all_lights()
            self.turn_on(self._boolean)  # no-op

    def turn_off_all_lights(self):
        self.log("Running lights off")
        for entity in self._entities:
            self.log(f"turning off {entity}")
            self.turn_off(entity)


class BooleanControlMotion(hass.Hass):

    def initialize(self):
        self._boolean = self.args.get("boolean")
        self._entities = self.args.get("entities")

        self.listen_state(self.callback, self._boolean)

    def callback(self, entity, attribute, old, new, kwargs):
        if new == "on":
            self.turn_on_motion_automations()
        if new == "off":
            self.turn_off_motion_automations()

    def turn_on_motion_automations(self):
        self.log("turning motion on")
        for switch in self._entities:
            self.log(f"Turning on {switch}".replace("input_boolean.", ""))
            self.turn_on(switch)

    def turn_off_motion_automations(self):
        self.log("turning motion off")
        for switch in self._entities:
            self.log(f"Turning off {switch}".replace("input_boolean.", ""))
            self.turn_off(switch)


class BooleanComputer(hass.Hass):

    def initialize(self):
        self._boolean = self.args.get("boolean")
        self._host = self.args.get("host")
        self._mac = self.args.get("mac")
        self._sleep_retry_count = 0  # Initialize the retry counter

        self.listen_state(self.callback, self._boolean)

    def callback(self, entity, attribute, old, new, kwargs):
        if new == "on":
            self.wake_on_lan()
        if new == "off":
            self._sleep_retry_count = 0
            self.sleep_on_lan()

    def sleep_on_lan(self):
        self.log("Go to sleep!")
        try:
            response = requests.get(f"http://{self._host}:8009/sleep")
            response.raise_for_status()
            self.log(f"Sleep command sent successfully. Response: {response.text}")

            self.run_in(self.check_state_and_resend_sleep, 20)

        except requests.exceptions.RequestException as e:
            self.log(f"Error sending Sleep command: {e}", level="ERROR")

    def check_state_and_resend_sleep(self, kwargs):
        self.log("checking status")
        try:
            state_response = requests.get(
                f"http://{self._host}:8009/state/local", timeout=5
            )
            state_response.raise_for_status()

            if "<state>online</state>" in state_response.text:
                if self._sleep_retry_count < 3:
                    self.log("Still online after sleep. Rerunning sleep command.")
                    self._sleep_retry_count += 1
                    self.sleep_on_lan()
                else:
                    self.log("Still online after sleep. Retry limit reached.")

            else:
                self.log("c137 is offline after sleep. Sleep successful.")

        except requests.exceptions.ConnectionError as connection_error:
            if "Failed to establish a new connection" in str(
                connection_error
            ) or "timed out" in str(connection_error):
                self.log("c137 is offline after sleep. Sleep successful.")
            else:
                self.log(f"Connection error: {connection_error}", level="WARNING")

        except requests.exceptions.RequestException as state_error:
            self.log(f"Error checking state: {state_error}", level="WARNING")

    def wake_on_lan(self):
        self.log("Wake up!")
        try:
            subprocess.run(
                ["/run/current-system/sw/bin/wakeonlan", self._mac], check=True
            )
            self.log("Wake on LAN command sent successfully.")
        except subprocess.CalledProcessError as e:
            self.log(f"Error sending Wake on LAN command: {e}", level="ERROR")
        except FileNotFoundError:
            self.log("wakeonlan command not found.", level="ERROR")
        except Exception as e:
            self.log(f"An unexpected error occured: {e}", level="ERROR")
