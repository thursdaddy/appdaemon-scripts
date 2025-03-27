# HASS + AppDaemon = ❤️

> Note: This is a WIP and pretty rough overall.

### Reasoning

As Home Assistant's GUI automations have become more advanced and feature-rich, AppDaemon's popularity has somewhat decreased by 2025 but it remains a powerful and capable solution.

I assume the decline is partly due to its steeper learning curve and a lack of well-established best practices but as a Vim and NixOS user, this is familiar territory. 😅

So here some of my half-baked reasons:
1. I wanted more experience with Python.
2. More feature complete logic flow and debugging via logs.
3. I'm using zigbee2mqtt, so in some cases I can avoid having to make HASS calls altogether.
4. Better/easier version control with Git.

### Structure

I've initially opted to loosely organize automations by trigger type.

For example, `motion/` for motion sensors, `tags/` for NFC tags, `cron/` for scheduled automations, etc, etc.

As the `apps.yml` configuration can get pretty extensive with scheduling, I wanted to avoid having one really large `apps.yml` file.

