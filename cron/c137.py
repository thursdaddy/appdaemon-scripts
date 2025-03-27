import xml.etree.ElementTree as ET

import appdaemon.plugins.hass.hassapi as hass
import requests


class ComputerStateMonitor(hass.Hass):

    def initialize(self):
        self.log("monitor check c137")
        self.run_every(self.check_computer, "now+1", 60)  # Run every minute

    def check_computer(self, kwargs):
        try:
            response = requests.get("http://127.0.0.1:8009/state/ip/192.168.10.137")
            response.raise_for_status()
            xml_string = response.text
            root = ET.fromstring(xml_string)
            computer_state = root.find("state").text
            input_boolean = "input_boolean.computer_c137"

            if computer_state == "offline":
                if self.get_state(input_boolean) == "on":
                    self.turn_off(input_boolean)
                    self.log(
                        f"Computer 192.168.10.137 offline, turned off {input_boolean}"
                    )
            elif computer_state == "online":
                if self.get_state(input_boolean) == "off":
                    self.turn_on(input_boolean)
                    self.log(
                        f"Computer 192.168.10.137 online, turned on {input_boolean}"
                    )
            else:
                self.log(f"Unexpected computer state: {computer_state}")

        except requests.exceptions.RequestException as e:
            self.log(f"Error checking computer: {e}", level="ERROR")
        except ET.ParseError as e:
            self.log(
                f"Error parsing XML: {e}, XML: {xml_string if 'xml_string' in locals() else 'No XML'}",
                level="ERROR",
            )
        except AttributeError as e:
            self.log(
                f"Error accessing XML element: {e}, XML: {xml_string if 'xml_string' in locals() else 'No XML'}",
                level="ERROR",
            )
