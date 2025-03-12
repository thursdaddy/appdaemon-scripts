import json

import hassapi as hass


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
        self.hass_api = self.get_plugin_api("HASS")
        self.mqtt_api = self.get_plugin_api("MQTT")

        # set in apps.yaml
        self._lock = self.args.get("lock")
        self._lock_topic = f"zigbee2mqtt/{self._lock}"
        self._magnet = self.args.get("magnet")
        self._magnet_topic = f"zigbee2mqtt/{self._magnet}"
        self._jammed_boolean = f"input_boolean.{self._lock}_jammed"

        self.lock_handler = None
        self.is_it_jammed_handler = None

        self.mqtt_api.listen_event(
            self.lock_callback, "MQTT_MESSAGE", topic=self._lock_topic
        )

        self.mqtt_api.listen_event(
            self.magnet_callback, "MQTT_MESSAGE", topic=self._magnet_topic
        )

    def lock_callback(self, event_name, data, kwargs):
        if self.get_state("input_boolean.automated_locks") == "off":
            self.log("Smart Lock automation disabled!")
            return
        try:
            payload = json.loads(data["payload"])
            if "lock_state" in payload and payload["lock_state"] == "locked":
                self.log("LOCK")

                if self.info_timer(self.lock_handler) is not None:
                    self.cancel_timer(self.lock_handler)

                if self.info_timer(self.is_it_jammed_handler) is not None:
                    self.cancel_timer(self.is_it_jammed_handler)

                state = self.get_state(self._lock.replace("lock_", "lock."))
                if state == "unlocked":
                    self.is_it_jammed_handler = self.run_in(
                        self.jammed_check,
                        15
                    )

            elif "lock_state" in payload and payload["lock_state"] == "unlocked":
                self.log("UNLOCK")

                jam_protection = self.get_state(self._jammed_boolean)
                if jam_protection == "off":
                    self.lock_handler = self.run_in(
                        self.lock_door,
                        30
                    )
                else:
                    self.log("Jam protection is on, please check the door!")

        except json.JSONDecodeError:
            self.log("[ERR] Invalid JSON payload")
        except KeyError:
            self.log("[ERR] Missing occupancy key in payload")

    def magnet_callback(self, event_name, data, kwargs):
        try:
            payload = json.loads(data["payload"])
            if "contact" in payload and payload["contact"] is True:
                self.log("DOOR CLOSED")

                self.set_state(self._jammed_boolean, state="off")

                state = self.get_state(self._lock.replace("lock_", "lock."))
                if state == "unlocked":
                    self.lock_handler = self.run_in(
                        self.lock_door, 30
                    )

            elif "contact" in payload and payload["contact"] is False:
                self.log("DOOR OPEN")

                self.set_state(self._jammed_boolean, state="off")

                if self.info_timer(self.is_it_jammed_handler) is not None:
                    self.cancel_timer(self.is_it_jammed_handler)

                if self.info_timer(self.lock_handler) is not None:
                    self.cancel_timer(self.lock_handler)

        except json.JSONDecodeError:
            self.log("[ERR] Invalid JSON payload")
        except KeyError:
            self.log("[ERR] Missing occupancy key in payload")

    def jammed_check(self, kwargs):
        self.log("Checking jam status:")

        if self.info_timer(self.is_it_jammed_handler) is not None:
            self.cancel_timer(self.is_it_jammed_handler)

        state = self.get_state(self._lock.replace("lock_", "lock."))
        self.log(state)
        if state == "locked":
            self.set_state(self._jammed_boolean, state="off")
        if state == "unlocked":
            self.set_state(self._jammed_boolean, state="on")
            self.log("Jammed up!")
            self.call_service(
                "notify/mobile_app_pixel_7_pro",
                title=f"{self._lock_name} IS JAMMED UP!",
                message=f"{self._lock_name} LEFT UNLOCKED!",
            )
            if self.info_timer(self.lock_handler) is not None:
                self.cancel_timer(self.lock_handler)

    def lock_door(self, kwargs):
        self.log("Locking door...")

        if self.info_timer(self.lock_handler) is not None:
            self.cancel_timer(self.lock_handler)

        self.call_service(
            "mqtt/publish",
            topic=f"{self._lock_topic}/set",
            payload="LOCK",
        ),
