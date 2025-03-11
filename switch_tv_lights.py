import hassapi as hass


class TvLights(hass.Hass):
    """
    Turns on tv_lights when tv current consumption goes above 30W for 2 seconds,
    and turns them off when it drops below 25W for 10 seconds.
    """

    def initialize(self):
        self.tv_consumption_entity = "sensor.living_room_tv_current_consumption"
        self.tv_lights_entity = "switch.living_room_tv_lights"
        self.consumption_threshold_on = 30
        self.consumption_threshold_off = 25
        self.delay_on = 2
        self.delay_off = 10
        self.timer_handle_on = None
        self.timer_handle_off = None
        self.lights_on = False

        self.listen_state(self.tv_consumption_changed, self.tv_consumption_entity)

    def tv_consumption_changed(self, entity, attribute, old, new, kwargs):
        try:
            consumption = float(new)
            if consumption == "unavailable":
                return
            if consumption > self.consumption_threshold_on:
                if self.timer_handle_on is None:
                    if self.timer_handle_off:
                        self.cancel_timer(self.timer_handle_off)
                        self.timer_handle_off = None

                    if self.get_state(self.tv_lights_entity) == "off":
                        self.timer_handle_on = self.run_in(
                            self.turn_on_lights, self.delay_on
                        )

            elif consumption < self.consumption_threshold_off:
                if self.timer_handle_on:
                    self.cancel_timer(self.timer_handle_on)

                if self.timer_handle_off is None:
                    self.timer_handle_off = self.run_in(
                        self.turn_off_lights, self.delay_off
                    )

        except (ValueError, TypeError):
            self.log(f"Invalid consumption value: {new}")
            return

    def turn_on_lights(self, kwargs):
        if not self.lights_on:
            self.log(
                f"Consumption above threshold for {self.delay_on} seconds, turning on lights."
            )
            self.turn_on(self.tv_lights_entity)
            self.lights_on = True
        self.timer_handle_on = None

    def turn_off_lights(self, kwargs):
        if self.lights_on:
            self.log(
                f"Consumption below threshold for {self.delay_off} seconds, turning off lights."
            )
            self.turn_off(self.tv_lights_entity)
            self.lights_on = False
        self.timer_handle_off = None
