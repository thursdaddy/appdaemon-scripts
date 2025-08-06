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
        if new == "home" and old != "home":
            self.log("Home Location Detected")
            self._home_window_active = True
            self._home_window_timer = self.run_in(self.end_home_window, 300)
        elif new == "away" and old != "away":
            self.log("Detected Away, Locking Door.")
            self._home_window_active = False
            self.lock_door
            if self._home_window_timer:
                self.cancel_timer(self._home_window_timer)

    def end_home_window(self, kwargs):
        self._home_window_active = False
        self.log("Home window ended")

    def person_detected(self, entity, attribute, old, new, kwargs):
        if new == "on":
            self.log("Person Detected")
            self.check_unlock_conditions()

    def check_unlock_conditions(self):
        self.log("Checking unlock conditions...")
        if self.get_state(self._location_entity) == "home" and self._home_window_active:
            self.log("Unlocking via Cameras")
            self.unlock_door()
        else:
            self.log("not unlocking")

    def unlock_door(self):
        self.call_service(
            "mqtt/publish",
            topic=f"{self._lock_topic}/set",
            payload="UNLOCK",
        ),
        if self._home_window_timer:
            self.cancel_timer(self._home_window_timer)

    def lock_door(self):
        lock_state = self.get_state(self._lock)
        if lock_state == "unlocked":
            self.log("Locked via Location")
            self.call_service(
                "mqtt/publish",
                topic=f"{self._lock_topic}/set",
                payload="LOCK",
            ),
