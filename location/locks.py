import hassapi as hass


class CameraLockControl(hass.Hass):
    """
    Lock and Unlock Doors via Location + Camera
    """
    HOME_WINDOW_TIMEOUT_SECONDS = 300


    def initialize(self) -> None:
        self.hass_api = self.get_plugin_api("HASS")
        self.mqtt_api = self.get_plugin_api("MQTT")

        # set in apps.yaml
        self._lock: str = self.args.get("lock")
        self._lock_topic: str = f"zigbee2mqtt/{self._lock}"
        self._location_entity: str = "device_tracker.pixel_7_pro"
        self._camera: str = self.args.get("camera")

        # home detection flags
        self._home_window_timer = None
        self._home_window_active = False

        # person detection
        self.listen_state(self.home_callback, self._location_entity)
        self.listen_state(self.camera_callback, self._camera)

    def _is_automation_enabled(self) -> bool:
        """Check if the smart lock automation is enabled."""
        if self.get_state("input_boolean.automated_locks") == "off":
            self.log("Smart Lock automation disabled!")
            return False
        return True

    def home_callback(self, entity, attribute, old, new, kwargs):
        if not self._is_automation_enabled():
            return

        self.log("home callback")
        self.location_update(entity, attribute, old, new, kwargs)

    def camera_callback(self, entity, attribute, old, new, kwargs):
        if not self._is_automation_enabled():
            return

        self.log("camera callback")
        self.person_detected(entity, attribute, old, new, kwargs)

    def location_update(self, entity, attribute, old, new, kwargs):
        if new == "home" and old != "home":
            self.log("Home Location Detected")
            self._home_window_active = True
            self._home_window_timer = self.run_in(
                self.end_home_window, self.HOME_WINDOW_TIMEOUT_SECONDS
            )
        elif new == "away" and old != "away":
            self.log("Detected Away, Locking Door.")
            self._home_window_active = False
            self.lock_door()
            if self._home_window_timer:
                self.cancel_timer(self._home_window_timer)

    def end_home_window(self, kwargs):
        self._home_window_active = False
        self.log("Home window ended")

    def person_detected(self, entity, attribute, old, new, kwargs):
        if new == "on":
            self.log("Person Detected")
            self._person_detected_flag = True
            self.check_unlock_conditions()

    def check_unlock_conditions(self):
        self.log("Checking unlock conditions...")
        self.log(f"person_detected_flag = {self._person_detected_flag}")
        self.log(f"home window active = {self._home_window_active}")
        if (
            self._person_detected_flag
            and self.get_state(self._location_entity) == "home"
            and self._home_window_active
        ):
            self.unlock_door()
        else:
            self.log("not unlocking")

    def unlock_door(self):
        self.log("checking lock state")
        lock_state = self.get_state(self._lock)
        if lock_state == "locked":
            self.log("Unlocked via Cameras")
            self.call_service(
                "mqtt/publish",
                topic=f"{self._lock_topic}/set",
                payload="UNLOCK",
            )
        self._person_detected_flag = False
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
            )
