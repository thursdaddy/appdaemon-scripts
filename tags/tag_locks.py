import json

import hassapi as hass


class UnlockDoor(hass.Hass):
    """
    Tags to unlock doors
    """

    def initialize(self):
        self.hass_api = self.get_plugin_api("HASS")

        self._tag = self.args.get("tag")
        self._lock = self.args.get("lock")
        self._lock_topic = f"zigbee2mqtt/{self._lock}"

        self._entity = self.get_entity(self._tag)
        self.handle = self._entity.listen_state(self.tag_callback)

    def tag_callback(self, data, events, *kwargs):
        try:
            self.log(data)
            self.log(self._lock_topic)

            self.call_service(
                "mqtt/publish",
                topic=f"{self._lock_topic}/set",
                payload="UNLOCK",
            ),

        except json.JSONDecodeError:
            return
