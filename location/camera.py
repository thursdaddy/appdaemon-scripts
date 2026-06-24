import json
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
        self._wifi_entity = self.args.get("wifi_sensor")
        self._camera = self.args.get("camera")
        self._magnet = self.args.get("magnet", None)

        # home detection flags
        self._home_window_timer = None
        self._home_window_active = False
        self._last_camera_trigger = None

        # person detection
        self.listen_state(self.home_callback, self._location_entity)
        if self._wifi_entity:
            self.listen_state(self.home_callback, self._wifi_entity)
        self.listen_state(self.camera_callback, self._camera)

        if self._magnet:
            self._magnet_topic = f"zigbee2mqtt/{self._magnet}"
            self.mqtt_api.listen_event(
                self.magnet_callback, "MQTT_MESSAGE", topic=self._magnet_topic
            )

    def home_callback(self, entity, attribute, old, new, kwargs):
        if self.get_state("input_boolean.automated_locks") == "off":
            self.log("Smart Lock automation disabled!")
            return

        self.location_update(entity, attribute, old, new, kwargs)

    def camera_callback(self, entity, attribute, old, new, kwargs):
        if self.get_state("input_boolean.automated_locks") == "off":
            self.log("Smart Lock automation disabled!")
            return

        self.person_detected(entity, attribute, old, new, kwargs)

    def location_update(self, entity, attribute, old, new, kwargs):
        door_name = self._lock.replace("lock_", "").replace("_", " ").title()
        if self._is_home_condition_met() and (old != "home" or not self._home_window_active):
            self.log(f"Home Location Detected. Activating 5-minute unlock window for {door_name}.")
            self._home_window_active = True
            self._home_window_timer = self.run_in(self.end_home_window, 300)

            # Check if camera is currently active or was recently triggered
            camera_state = self.get_state(self._camera)
            recently_triggered = False
            if self._last_camera_trigger:
                time_diff = (self.datetime() - self._last_camera_trigger).total_seconds()
                if time_diff < 90:
                    recently_triggered = True

            if camera_state == "on" or recently_triggered:
                self.log(f"Camera near {door_name} was active (state: {camera_state}, recent: {recently_triggered}). Unlocking immediately.")
                self.unlock_door()

        elif not self._is_home_condition_met() and (old == "home" or self._home_window_active):
            self.log(f"Detected Away from home. Locking {door_name}.")
            self._home_window_active = False
            self.lock_door()
            if self._home_window_timer:
                self.cancel_timer(self._home_window_timer)

    def end_home_window(self, kwargs):
        door_name = self._lock.replace("lock_", "").replace("_", " ").title()
        if self._home_window_timer:
            self.cancel_timer(self._home_window_timer)
            self._home_window_active = False
        self.log(f"Home unlock window expired for {door_name}.")
        
        # Notify the user that the window has expired
        self.call_service(
            "notify/gotify",
            title=f"Smart Lock Window Expired",
            message=f"The 5-minute unlock window for {door_name} has expired.",
            data={
                "extras": {
                    "client::display": {"contentType": "text/plain"},
                },
                "priority": 4,
            }
        )

    def person_detected(self, entity, attribute, old, new, kwargs):
        if new == "on":
            door_name = self._lock.replace("lock_", "").replace("_", " ").title()
            self.log(f"Person Detected near {door_name}.")
            self._last_camera_trigger = self.datetime()
            self.check_unlock_conditions()

    def _is_home_condition_met(self) -> bool:
        location_home = self.get_state(self._location_entity) == "home"
        if self._wifi_entity:
            wifi_connected = self.get_state(self._wifi_entity) == "connected"
            return location_home or wifi_connected
        return location_home

    def check_unlock_conditions(self):
        door_name = self._lock.replace("lock_", "").replace("_", " ").title()
        self.log(f"Checking unlock conditions for {door_name}...")
        if self._is_home_condition_met() and self._home_window_active:
            self.log(f"Unlocking {door_name} via Cameras.")
            self.unlock_door()
        else:
            self.log(f"Not unlocking {door_name}. Conditions not met (home: {self._is_home_condition_met()}, window_active: {self._home_window_active}).")

    def unlock_door(self):
        door_name = self._lock.replace("lock_", "").replace("_", " ").title()
        self.log(f"Unlocking {door_name}...")
        if self._home_window_timer:
            self.cancel_timer(self._home_window_timer)
            self._home_window_timer = None
        self._home_window_active = False
        self.mqtt_api.mqtt_publish(
            topic=f"{self._lock_topic}/set",
            payload="UNLOCK",
        )

    def lock_door(self):
        door_name = self._lock.replace("lock_", "").replace("_", " ").title()
        lock_state = self.hass_api.get_state(self._lock)
        if lock_state == "unlocked":
            self.log(f"Locking {door_name}...")
            self.mqtt_api.mqtt_publish(
                topic=f"{self._lock_topic}/set",
                payload="LOCK",
            )

    def magnet_callback(self, event_name, data, kwargs):
        try:
            payload = json.loads(data["payload"])
            if "contact" in payload and payload["contact"] is False:
                # Door was opened
                door_name = self._lock.replace("lock_", "").replace("_", " ").title()
                if self._home_window_active:
                    self.log(f"{door_name} was opened. Resetting/canceling the home unlock window.")
                    if self._home_window_timer:
                        self.cancel_timer(self._home_window_timer)
                        self._home_window_timer = None
                    self._home_window_active = False
        except json.JSONDecodeError:
            self.log("[ERR] Invalid JSON payload on magnet")
        except KeyError:
            self.log("[ERR] Missing contact key in payload on magnet")
