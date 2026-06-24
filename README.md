# AppDaemon Automation Configs

This repository contains Python-based automations and configurations managed through AppDaemon for Home Assistant.

Detailed list of all active automations, schedules, and entities can be found in [automations.md](file:///Users/thurs/dev/appd/apps/automations.md).

---

## Directory Structure

*   `climate/` — Three-tier HVAC scheduling (E-16 Tariff Plan) and cumulative cooling cost tracking.
*   `location/` — Driveway Wi-Fi welcome lights, Away mode overrides, and camera-based proximity unlocking.
*   `locks/` — Automated locking, left-open alerts, door magnets, and NFC tags.
*   `motion/` — Motion-activated lighting with scheduling, lux-based brightness scaling, and espresso machine controllers.
*   `pico/` — Button configurations for Lutron Caseta Pico remotes.
*   `button/` — Multipress smart buttons (single, double, hold actions).
*   `switches/` — Master activity switches, computer WOL/sleep managers, and power-draw reactive plugs.
*   `magnet/` — Pantry door and drawer lighting triggers.
*   `tags/` — NFC tag triggers for door unlocks.
*   `water/` — Flood/leak monitoring and Gotify alerts.
*   `cron/` — Daily schedules, resets, and network ping monitors.

---

## Architecture & Base Classes

Most automation classes inherit from custom helpers or standard AppDaemon plugins:

1.  **`BaseController` ([base_controller.py](file:///Users/thurs/dev/appd/apps/base_controller.py))**:
    A lightweight wrapper extending `appdaemon.plugins.hass.hassapi.Hass`. It provides standard helper methods for executing arrays of actions (like turning entities on/off, toggling, or calling custom services with args).
2.  **`MotionSwitch` ([motion/switches.py](file:///Users/thurs/dev/appd/apps/motion/switches.py)) / `MotionLights` ([motion/lutron.py](file:///Users/thurs/dev/appd/apps/motion/lutron.py))**:
    Event-driven controllers listening to Zigbee2MQTT motion sensor occupancy payloads. They check corresponding room-level overrides (e.g. `input_boolean.motion_<room>`) before executing lighting or switch transitions.
3.  **`MotionRGBLight` ([motion/rgb_lights.py](file:///Users/thurs/dev/appd/apps/motion/rgb_lights.py))**:
    Supports time-of-day specific RGB colors, and optionally monitors a lux sensor to scale the target brightness output dynamically based on ambient room light.

---

## Deployment & Environments

*   **Production Deployment**: Configured and deployed via NixOS on the home server. The host environment manages service definitions, templates, and coordinates state with Home Assistant.
*   **Local Workspace**: File modifications are written to this workspace (`/Users/thurs/dev/appd/apps`) and synced or deployed via NixOS modules.
*   **Git Workflow**: Always verify python syntax compilation before committing and deploying. Do not push to remote directly from the workspace unless desired.

## Development & Verification

This workspace includes a **Nix flake** (`flake.nix`) and **direnv** config (`.envrc`) to automatically load a Python environment populated with `appdaemon` and `requests` dependencies.

To activate the shell:
```bash
# Using direnv (automatic upon entering the directory)
direnv allow

# Or manually using Nix
nix develop
```

Once inside the environment, you can recursively verify that all Python files compile without syntax errors:
```bash
python3 -m compileall .
```
