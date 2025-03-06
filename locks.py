import json
from typing import Dict

import hassapi as hass

_MQTT_PLUGIN_NAMESPACE = "mqtt"


class LockDoors(hass.Hass):
    """
    Lock and Unlock Doors
    """

    def initialize(self) -> None:
        """
        Magnet: Aqara magnets
        Locks: Wyze Locks
        Cameras: Unifi
        """
        # Set in apps.yml
        self._topic = self.args["topic"]
        self._person = self.args["person"]
        self._location_entity = "device_tracker.pixel_7_pro"
        self._magnet = self._topic.replace("zigbee2mqtt/", "binary_sensor.")

        self._lock = self.args["lock"]
        if self._lock == "lock.back_door":
            self._lock_topic = "zigbee2mqtt/back_door_lock/set"
            self._lock_name = "BACK DOOR"
        elif self._lock == "lock.front_door":
            self._lock_topic = "zigbee2mqtt/front_door_lock/set"
            self._lock_name = "FRONT DOOR"

        self._mqtt = self.get_plugin_api("MQTT")
        self._mqtt.listen_event(
            self._parse_json,
            "MQTT_MESSAGE",
            topic=self._topic,
        )
        self.listen_state(self.location_update, self._location_entity)
        self.listen_state(self.person_detected, self._person)
        self._person_detected_flag = False
        self._home_window_active = False
        self._home_window_timer = None
        self._lock_timer = None

    def _parse_json(self, event: str, data: Dict, unused_kwargs: Dict) -> None:
        try:
            payload = json.loads(data["payload"])
            if payload["contact"]:
                self.door_closed()
            elif not payload["contact"]:
                self.door_open()
        except json.JSONDecodeError:
            pass

    def person_detected(self, entity, attribute, old, new, kwargs):
        if new == "on":
            self.log(f"{self._person} -> Person Detected")
            self._person_detected_flag = True
            self.check_unlock_conditions()
        else:
            self._person_detected_flag = False

    def door_open(self) -> None:
        self.log(f"{self._topic} -> Door Open")
        if self._lock_timer:
            self._lock_timer = None

    def door_closed(self) -> None:
        self.log(f"{self._topic} -> Door Closed")
        self._timer_handlers = self.run_in(self.lock_door, 30)

    def lock_door(self, kwargs: Dict) -> None:
        lock_state = self.get_state(self._lock)
        door_state = self.get_state(self._magnet)
        if lock_state == "unlocked" and door_state == "off":
            self.log("Locking...")

            self.call_service(
                "mqtt/publish",
                topic=self._lock_topic,
                payload="LOCK",
            ),

        self._lock_timer = self.run_in(self.jam_detector, 15)

    def jam_detector(self, kwargs):
        lock_state = self.get_state(self._lock)
        if lock_state == "unlocked":
            self.log(
                f"Jammed! Sending Notification that {self._lock_name} is unlocked!"
            )

            self.call_service(
                "notify/mobile_app_pixel_7_pro",
                message=f"{self._lock_name} IS JAMMED UP!",
                title=f"{self._lock_name} IS UNLOCKED!",
            )
        else:
            self.log("Locked")

    def location_update(self, entity, attribute, old, new, kwargs):
        if new == "home" and old != "home":
            self.log(f"{self._location_entity} -> Home Location Detected")
            self._home_window_active = True
            if self._home_window_timer:
                self.cancel_timer(self._home_window_timer)
            self._home_window_timer = self.run_in(self.end_home_window, 300)
            self.check_unlock_conditions()

    def end_home_window(self, kwargs):
        self._home_window_active = False
        self.log("Home window ended")

    def check_unlock_conditions(self):
        if (
            self._person_detected_flag
            and self.get_state(self._location_entity) == "home"
            and self._home_window_active
        ):
            self.unlock_door(kwargs={})

    def unlock_door(self, kwargs: Dict) -> None:
        lock_state = self.get_state(self._lock)
        if lock_state == "locked":
            self.log(f"{self._lock_name} -> Unlocked via Cameras")
            self.call_service(
                "mqtt/publish",
                topic=self._lock_topic,
                payload="UNLOCK",
            ),
