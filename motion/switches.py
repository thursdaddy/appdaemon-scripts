import json

import appdaemon.plugins.hass.hassapi as hass


class MotionSwitch(hass.Hass):

    def initialize(self):
        self.hass_api = self.get_plugin_api("HASS")
        self.mqtt_api = self.get_plugin_api("MQTT")

        # set in apps.yaml
        self._motion_sensor = self.args.get("motion_sensor")
        self._switches = self.args.get("switches", None)
        self._schedule = self.args.get("schedule", None)
        self._delay = self.args.get("delay", None)

        self.timer_handler = None

        if not self._motion_sensor:
            self.log(
                f"[ERR] Set a switch or scene to use with \
                    {self._motion_sensor}"
            )
            return

        self.mqtt_api.listen_event(
            self.mqtt_callback, "MQTT_MESSAGE", topic=self._motion_sensor
        )

    def mqtt_callback(self, event_name, data, kwargs):
        try:
            payload = json.loads(data["payload"])
            self.config = self.get_config()
            if "occupancy" in payload and payload["occupancy"] is True:
                self.log("Motion Detected!")

                if self.info_timer(self.timer_handler) is not None:
                    self.cancel_timer(self.timer_handler)

                if self.is_scheduled():
                    self.turn_on_switches()
                else:
                    self.log("Not Scheduled")

            elif "occupancy" in payload and payload["occupancy"] is False:
                self.log("Motion Cleared!")
                if self.config["delay"] is not None:
                    self.timer_handler = self.run_in(
                        self.turn_off_switches,
                        self.config["delay"],
                    )

        except json.JSONDecodeError:
            self.log("[ERR] Invalid JSON payload")
        except KeyError:
            self.log("[ERR] Missing occupancy key in payload")

    def turn_on_switches(self):
        for switch in self.config["switches"]:
            # get current state of switches
            state = self.get_entity(switch).get_state()

            if state == "off":
                self.log(f"Turning on switch: {switch}")
                self.call_service(
                    "switch/turn_on",
                    entity_id=switch,
                )

    def turn_off_switches(self, kwargs):
        for switch in self.config["switches"]:
            self.log(f"Turning off switch: {switch}")
            self.turn_off(switch)

    def is_scheduled(self):
        if self.now_is_between(self.config["start"], self.config["end"]):
            return True

    def get_config(self):
        for name, config in self._schedule.items():
            config["name"] = name
            if "delay" not in config:
                config["delay"] = self._delay
            if "switches" not in config:
                config["switches"] = self._switches
            return config
