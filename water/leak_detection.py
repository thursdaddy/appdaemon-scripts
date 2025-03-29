import json

import hassapi as hass


class WaterDetectionNotifier(hass.Hass):
    """
    Alert on water detection with recheck and repeating alert logic.
    """

    def initialize(self):
        self.hass_api = self.get_plugin_api("HASS")
        self.mqtt_api = self.get_plugin_api("MQTT")
        self._entity = self.args.get("entity")
        self._entity_topic = f"zigbee2mqtt/{self._entity}"
        self._entity_sensor = f"binary_sensor.{self._entity}"
        self.leak_renotify_timer = None

        self.initial_alert_sent = False

        self.mqtt_api.listen_event(
            self.mqtt_event, "MQTT_MESSAGE", topic=self._entity_topic
        )
        self.log(self._entity)
        self.log(self._entity_topic)
        self.log(self._entity_sensor)

    def mqtt_event(self, event_name, data, kwargs):
        payload = data["payload"]
        try:
            payload_dict = json.loads(payload)
            if payload_dict.get("water_leak"):
                self.log(f"Potential water leak detected for {self._entity}!")
                self.schedule_recheck()
            else:
                self.log("DRY")
                self.initial_alert_sent = False
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.log(
                f"Error processing MQTT payload for {self._entity}: {e}",
                level="WARNING",
            )

    def schedule_recheck(self):
        """Schedules a recheck for the water leak."""
        if self.info_timer(self.leak_renotify_timer) is not None:
            self.cancel_timer(self.leak_renotify_timer)

        if self.initial_alert_sent:
            self.leak_renotify_timer = self.run_in(self.check_for_leaks, 5 * 60)
        else:
            self.leak_renotify_timer = self.run_in(self.check_for_leaks, 60)

    def check_for_leaks(self, kwargs):
        """
        Checks for leaks after a delay and sends a notification if still 'on'.
        """
        try:
            state = self.get_state(self._entity_sensor)
            if state == "on":
                self.log(f"Confirmed water leak for {self._entity}!")
                self.send_alert()
                self.schedule_recheck()
            else:
                self.leak_renotify_timer = None
                self.initial_alert_sent = False
                self.call_service(
                    "notify/gotify",
                    message=f"DRY: {self._entity}!",
                    title="Water sensor now reporting DRY",
                    data={
                        "extras": {
                            "client::display": {"contentType": "text/plain"},
                            "client::notification": {
                                "click": {"url": "https://home.thurs.pw"}
                            },
                        },
                        "priority": 10,
                    },
                )

        except AttributeError as e:
            self.log(
                f"Error rechecking water leak for {self._entity}: {e}", level="WARNING"
            )
            self.leak_renotify_timer = None

    def send_alert(self):
        """Sends the Gotify alert."""
        self.call_service(
            "notify/gotify",
            message=f"Confirmed water leak at {self._entity}!",
            title="Water Leak Alert!!!",
            data={
                "extras": {
                    "client::display": {"contentType": "text/plain"},
                    "client::notification": {"click": {"url": "https://home.thurs.pw"}},
                },
                "priority": 10,
            },
        )
        self.initial_alert_sent = True
