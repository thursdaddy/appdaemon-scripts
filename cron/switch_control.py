from base_controller import BaseController


class SwitchControl(BaseController):
    """
    Generic Scheduled Actions Controller
    """

    def initialize(self):
        self._time = self.args.get("time")
        self._actions = self.args.get("actions", [])

        if not self._time:
            self.error("time not provided in configuration.")
            return

        self.run_daily(self.execute_scheduled_actions, self._time)

    def execute_scheduled_actions(self, kwargs):
        self.log(f"Cron scheduled execution triggered at {self._time}")
        super().execute_actions(self._actions)
