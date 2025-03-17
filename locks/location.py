import hassapi as hass


class CameraLockControl(hass.Hass):
    """
    Lock and Unlock Doors via Location + Camera
    """

    def initialize(self) -> None:
        self.hass_api = self.get_plugin_api("HASS")
        self.mqtt_api = self.get_plugin_api("MQTT")

        # set in apps.yaml
        self._lock = self.args.get("lock")
        self._lock_topic = f"zigbee2mqtt/{self._lock}"
        self._location_entity = "device_tracker.pixel_7_pro"
        self._camera = self.args.get("camera")

        # home detection flags
        self._home_window_timer = None
        self._home_window_active = False

        # person detection
        self._person_detected_flag = False

        self.listen_state(self.home_callback, self._location_entity)
        self.listen_state(self.camera_callback, self._camera)

    def home_callback(self, entity, attribute, old, new, kwargs):
        if self.get_state("input_boolean.automated_locks") == "off":
            self.log("Smart Lock automation disabled!")
            return

        self.log("home callback")
        self.location_update(entity, attribute, old, new, kwargs)

    def camera_callback(self, entity, attribute, old, new, kwargs):
        if self.get_state("input_boolean.automated_locks") == "off":
            self.log("Smart Lock automation disabled!")
            return

        self.log("camera callback")
        self.person_detected(entity, attribute, old, new, kwargs)

    def location_update(self, entity, attribute, old, new, kwargs):
        self.log(new)
        self.log(old)
        if new == "home" and old != "home":
            self.log("Home Location Detected")
            self._home_window_active = True
            if self._home_window_timer:
                self.cancel_timer(self._home_window_timer)
            self._home_window_timer = self.run_in(self.end_home_window, 300)
            self.check_unlock_conditions()
        elif new == "away" and old != "away":
            self.log("Detected Away..")
            self._home_window_active = False
            self.lock_door

    def end_home_window(self, kwargs):
        self._home_window_active = False
        self.log("Home window ended")

    def person_detected(self, entity, attribute, old, new, kwargs):
        if new == "on":
            self.log("Person Detected")
            self._person_detected_flag = True
            self.check_unlock_conditions()
        else:
            self._person_detected_flag = False

    def check_unlock_conditions(self):
        self.log("checking unlock conditions")
        self.log(self._person_detected_flag)
        self.log(self.get_state(self._location_entity))
        self.log(self._home_window_active)
        self.unlock_door()
        if (
            self._person_detected_flag
            and self.get_state(self._location_entity) == "home"
            and self._home_window_active
        ):
            self.log("trueee")
            self.unlock_door()
        else:
            self.log("falseeeee")

    def unlock_door(self):
        self.log("checking lock state")
        lock_state = self.get_state("lock.front_door")
        self.log("lock.front_door")
        if lock_state == "locked":
            self.log("Unlocked via Cameras")
            self.call_service(
                "mqtt/publish",
                topic=f"{self._lock_topic}/set",
                payload="UNLOCK",
            ),

    def lock_door(self):
        lock_state = self.get_state(self._lock)
        if lock_state == "unlocked":
            self.log("Locked via Location")
            self.call_service(
                "mqtt/publish",
                topic=f"{self._lock_topic}/set",
                payload="LOCK",
            ),
