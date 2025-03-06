import json
from datetime import datetime, time
from typing import Dict, List, Optional

import hassapi as hass

_MQTT_PLUGIN_NAMESPACE = "mqtt"


class MotionDetectLight(hass.Hass):
    """
    Motion detection turns on lights based on room occupancy and time of day.
    """

    def initialize(self) -> None:
        """
        Sensor: Aqara Motion Sensor on Zigbee2MQTT
        Light: Tp-Link Kasa Light Bulb (or other)
        """
        self._time_based_lights = self.args["time_based_lights"]
        self._topic = self.args["topic"]
        self._delay = self.args["delay"]

        # Store timers per light
        self.timer_handlers: Dict[str, hass.timer_handle_type] = {}
        for time_range in self._time_based_lights.values():
            for entity in time_range["lights"]:
                self.timer_handlers[entity] = None

        self._mqtt = self.get_plugin_api("MQTT")
        self._mqtt.listen_event(
            self._parse_json,
            "MQTT_MESSAGE",
            topic=self._topic,
        )

    def _parse_json(self, event: str, data: Dict, unused_kwargs: Dict) -> None:
        try:
            payload = json.loads(data["payload"])
        except json.JSONDecodeError:
            return

        occupancy = payload["occupancy"]
        if occupancy:
            self.occupancy_detected()
        else:
            self.occupancy_cleared()

    def occupancy_detected(self) -> None:
        self.log(f"{self._topic} -> Occupancy detected")
        lights_to_turn_on = self._get_lights_for_current_time()
        self.log(lights_to_turn_on)
        if lights_to_turn_on:
            for entity in lights_to_turn_on:
                if self.timer_handlers[entity]:
                    self.cancel_timer(self.timer_handlers[entity])
                    self.timer_handlers[entity] = None
                self.turn_light_on(entity)

    def occupancy_cleared(self) -> None:
        self.log(f"{self._topic} -> Occupancy cleared")
        lights_to_turn_off = self._get_lights_for_current_time()
        if lights_to_turn_off:
            for entity in lights_to_turn_off:
                if self.timer_handlers[entity]:
                    self.cancel_timer(self.timer_handlers[entity])
                self.timer_handlers[entity] = self.run_in(
                    self.turn_light_off, self._delay, entity=entity
                )

    def turn_light_on(self, entity: str) -> None:
        if self.timer_handlers[entity]:
            self.cancel_timer(self.timer_handlers[entity])
        current_state = self.get_state(entity)
        if current_state == "off" or "unknown":
            self.log(f"{self._topic} -> Turning on: {entity}")
            self.turn_on(entity)

    def turn_light_off(self, kwargs) -> None:
        entity = kwargs["entity"]
        if "scene" in entity: #check if any light in the list contains scene.
            scene_lights = self._get_lights_for_scene()
            for entity in scene_lights:
                self.log(f"{self._topic} -> Turning off: {entity}")
                self.turn_off(entity)
        else:
            self.turn_off(entity)

    def _get_lights_for_current_time(self) -> Optional[List[str]]:
        now = datetime.now().time()
        for time_range, config in self._time_based_lights.items():
            start_time = datetime.strptime(config["start"], "%H:%M:%S").time()
            end_time = datetime.strptime(config["end"], "%H:%M:%S").time()
            if start_time <= now <= end_time:
                return config["lights"]
        return None

    def _get_lights_for_scene(self) -> Optional[List[str]]:
        now = datetime.now().time()
        for time_range, config in self._time_based_lights.items():
            start_time = datetime.strptime(config["start"], "%H:%M:%S").time()
            end_time = datetime.strptime(config["end"], "%H:%M:%S").time()
            if start_time <= now <= end_time:
                return config["scene_lights"]
        return None
