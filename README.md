# HASS - AppDaemon

> Note: This is a WIP and pretty rough overall.

### Reasoning

While it seems in 2025, AppDaemon has fallen slightly out of favor over the years as the creating HASS automations via the GUI has become more advanced and feature complete, it is still a very powerful and capable solution. I also imagine this is partially due to the higher bar of entry and lack of documented "best practices". As a vim and NixOS user, this is par for the course.

1. I wanted more experience with Python.
2. More feature complete logic flow and debugging via logs.
3. I'm using zigbee2mqtt, so in some cases I can avoid having to make HASS calls altogether.
4. Better/easier version control with Git.

### Structure

I've initially opted to losely organize automations by trigger type.

For example, `motion/` for motion sensors, `tags/` for NFC tags, `cron/` for scheduled automations, etc, etc.

As the `apps.yml` configuration can get pretty extensive with scheduling, I wanted to avoid having one really large `apps.yml` file.

