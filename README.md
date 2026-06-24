# 🏠 Home Assistant + AppDaemon Automations

This repository contains Python-based Home Assistant automations managed through **AppDaemon**. The project is structured by trigger type to keep the logic modular and configuration files clean.

---

## 📂 Directory Structure

*   `climate/` — Three-tier HVAC climate controls, cost trackers, and tariff schedules.
*   `location/` — Welcome home lights, Wi-Fi + camera proximity door unlocking, and away-mode.
*   `locks/` — Auto-locking, door contact checking, jam protections, and Gotify alerts.
*   `motion/` — Motion-activated lighting (including adaptive RGB brightness based on lux).
*   `pico/` — Caseta Pico remote physical button mappings.
*   `button/` — Smart buttons (single, double, and hold actions).
*   `switches/` — Master switches, power-controlled backlights, and computer sleep/WOL managers.
*   `magnet/` — Door and drawer magnet sensors (pantry lighting).
*   `tags/` — Phone NFC tag-based door unlocking.
*   `water/` — Flood and leak detection gotify notifications.
*   `cron/` — Scheduled actions and network state checkers.

---

## 📋 Automations & Settings Catalog

### 🌡️ Climate & HVAC Control (`climate/`)
*   **Climate Schedule (`ClimateSchedule`)**:
    *   **Climate Entity**: `climate.nest`
    *   **Estimated AC Power Draw**: `4.1 kW` (configured to American Standard® 3.5-ton heat pump draw + blower)
    *   **Schedule Target Setpoints**:
        *   **Super Off-Peak** (8:00 AM – 3:00 PM, Daily): `75.0°F` (Pre-cooling)
        *   **On-Peak** (5:00 PM – 10:00 PM, Weekdays): `85.0°F` (Load-shedding)
        *   **Off-Peak** (All other times): `78.0°F`
*   **HVAC Cost Tracker (`HVACCostTracker`)**:
    *   Listens to: `sensor.hvac_cooling` (history stats) and publishes to `sensor.hvac_cost_tracker`.
    *   **E-16 Tariff Rate Windows**:
        *   **Summer** (May – Oct): Peak = `$0.1257`, Off-Peak = `$0.0995`, Super Off-Peak = `$0.0393`
        *   **Winter** (Nov – Apr): Peak = `$0.1051`, Off-Peak = `$0.0907`, Super Off-Peak = `$0.0425`
    *   **Glitch / Reboot Protection**: Ignores any midday sensor drops (only resets cost/runtime metrics within 5 minutes of midnight).

---

### 🛡️ Smart Locks & Security (`locks/` & `tags/`)
*   **Automated Lock Controls (`LockDoors`)**:
    *   **Front Door**: `lock_front_door` + magnet contact `magnet_front_door`.
    *   **Back Door**: `lock_back_door` + magnet contact `magnet_back_door`.
    *   **Auto-Locking**: Automatically locks the door 30 seconds after it is closed.
    *   **Jam / Left-Open Alert**: If a door is unlocked and left open or gets jammed, it will check the state after 15 seconds. If you are away, it sends a Gotify notification.
*   **NFC Tag Unlock (`UnlockDoor`)**:
    *   Unlocks `lock_front_door` via phone NFC scan on `tag.front_door_unlock`.
    *   Unlocks `lock_back_door` via phone NFC scan on `tag.back_door_unlock`.

---

### 📍 Proximity & Location (`location/`)
*   **Smart Lock Camera Controller (`CameraLockControl`)**:
    *   Triggers when `device_tracker.pixel_7_pro` or `sensor.pixel_7_pro_wi_fi_connection` changes to "home/connected".
    *   **Welcome Window**: Opens a 5-minute unlock window.
    *   **Unlock Triggers**: Unlocks the door if the person-detection camera (`binary_sensor.g4_doorbell_person_detected` or `binary_sensor.back_door_person_detected`) triggers.
    *   **Auto-Reset**: Instantly deactivates the window and cancels timers when the door magnet contact is opened (entering the house) or when the lock unlocks successfully.
    *   **Gotify Alerts**: Sends an alert if the 5-minute window expires without any camera motion detected.
*   **Welcome Lights (`LocationChange`)**:
    *   Triggers when phone arrives home (Wi-Fi connects or GPS updates).
    *   **Schedule Window**: Active **only** from 1 hour before sunset (`"sunset - 01:00:00"`) until `sunrise` (stays off during the day).
    *   **Lights**: `light.living_room_main_lights` and `light.hallway_main_lights`.
    *   **Setting**: Turns on at `50%` brightness for `2 minutes` (120 seconds).
*   **Away Mode (`AwayMode`)**:
    *   Triggers ECO and energy saving settings when GPS transitions to away.

---

### 💡 Motion Lighting (`motion/` & `magnet/`)
*   **Kitchen Under-Cabinet (`MotionLights`)**:
    *   Sensor: `motion_kitchen`.
    *   Schedules:
        *   **Day** (Sunrise – 6:00 PM): Lights on at `100%`, delays off after `5 minutes` (300s).
        *   **Evening** (6:00 PM – 9:00 PM): Lights on at `100%`, delays off after `10 minutes` (600s).
        *   **Night** (9:00 PM – Sunrise): Under-cabinet light only at `30%`, delays off after `30 seconds`.
*   **Kitchen Main (`MotionLights`)**:
    *   Sensor: `motion_kitchen`.
    *   Schedules:
        *   **Day** (Sunrise – 12:00 PM): Bar light at `30%` for `60s`.
        *   **Afternoon** (12:00 PM – 4:00 PM): Bar + Hallway lights at `50%` for `30s`.
        *   **Evening** (4:00 PM – 9:00 PM): Bar + Hallway lights at `50%` for `30s`.
        *   **Night** (9:00 PM – Sunrise): Hallway light at `25%` for `10s`.
*   **Office Motion (`MotionRGBLight` with Lux)**:
    *   Sensor: `motion_office`. Light: `light.office_desk`.
    *   Lux Sensor: `sensor.motion_office_illuminance` (Scales brightness between `50 - 250 lx` from min `10%` to target).
    *   Schedules (Time-based RGB Colors):
        *   **Day** (Sunrise – 6:00 PM): `[255, 247, 255]` (Cool Pink) @ `80%` brightness, `5 min` delay.
        *   **Evening** (6:00 PM – 10:00 PM): `[255, 157, 71]` (Warm Amber) @ `100%` brightness, `2 min` delay.
        *   **Night** (10:00 PM – 4:00 AM): `[255, 110, 84]` (Soft Red) @ `60%` brightness, `1 min` delay.
*   **Stairway Motion (`MotionRGBLight`)**:
    *   Upstairs lights `1` and `2` turn on warm amber (`[255, 157, 71]`) during evening (`18:00 - 22:00` at `60%`) and dim red (`[255, 28, 20]` at `1%` brightness for `30s`) at night.
*   **Printer Area Motion (`MotionRGBLight`)**:
    *   Activates printer workspace lighting with cool white during the day and red lighting at night.
*   **Pantry Door Magnet (`PantryLight`)**:
    *   Magnet: `magnet_pantry_door`. Light: `light.pantry_leds`.
    *   Turns on pantry lights when opened; shuts off automatically after a `5-minute` timeout (300s).
*   **SIM Room Motion Controllers (`MotionSwitch`)**:
    *   **Desk Light (`sim_motion_light`)**:
        *   Sensor: `motion_sim`. Switch: `switch.sim_desk_light`.
        *   Delays: `15 minutes` (900s) during the day (`sunrise` to `23:00`), `30 seconds` at night (`23:00:01` to `sunrise`).
    *   **Espresso Machine (`sim_motion_espresso`)**:
        *   Sensor: `motion_sim`. Switch: `switch.kitchen_espresso`.
        *   Schedule: Active **only** in the morning between `sunrise` and **`11:00:00` AM** (automatically starts warming up the kitchen espresso machine when morning motion is detected in the SIM room).

---

### 🎛️ Physical Remotes & Buttons (`pico/` & `button/`)
*   **Office Pico Remote (`PicoEvent`)**:
    *   `On` Button: Turn ON desk light (`light.office_desk`).
    *   `Off` Button: Turn OFF desk light.
    *   `Lower` Button: Turn OFF desk light **AND** disable office motion lights (turns `input_boolean.motion_office` off).
    *   `Stop` Button: Toggle office motion light controls on/off.
*   **Living Room Pico Remote (`PicoEvent`)**:
    *   `On` / `Off` Buttons: Control `light.living_room_main_lights`.
    *   `Stop` Button: Force-resets the office motion control `on` (`input_boolean.motion_office`).
*   **Sim Room Pico Remote (`PicoEvent`)**:
    *   `On` / `Off` Buttons: Toggle SIM activity state (`input_boolean.activity_sim`).
    *   `Lower` Button: Toggle `switch.sim_fan`.
    *   `Raise` Button: Toggle `switch.sim_spotlight`.
*   **Bedroom Smart Button (`ButtonPress`)**:
    *   **Single Press**: Turn OFF all house lights (`input_boolean.lights_all`).
    *   **Double Press**: Disable motion controls for all rooms (`input_boolean.motion_all`).
    *   **Hold Press**: Send sleep signal/turn off PC `c137` (`input_boolean.computer_c137`).

---

### 🔌 Smart Switches & Power Automation (`switches/`)
*   **Power Controlled TV Backlight (`PowerControlledSwitch`)**:
    *   Monitor: TV current consumption.
    *   Action: Turns on `light.tv_lights` when TV consumes `>30W`. Shuts them off 30 seconds after TV drops `<25W`.
*   **Power Controlled 3D Printer Lights (`PowerControlledSwitch`)**:
    *   Monitor: 3D printer current consumption.
    *   Action: Activates `switch.printer_lights` when printing `>10W`, shuts off 10s after print finishes `<5W`.
*   **Computer Sleep & State Monitors (`ComputerManager` & `ComputerStateMonitor`)**:
    *   Manages Wake-On-Lan and tracks state for:
        *   **PC C137** (192.168.10.137 / 9C:5C:8E:BC:1E:46)
        *   **PC Sim** (192.168.10.116 / 9C:6B:00:14:AC:A5)
        *   **PC Gamer** (192.168.10.169 / A8:A1:59:EC:99:AD)
*   **SIM Room Master Switch (`BooleanSIM`)**:
    *   Toggling `input_boolean.activity_sim` controls spotlights, the projector, SIM fan, and boots up PC Sim via WOL.

---

### 💧 Leak & Flood Detection (`water/`)
*   **Leak Monitors (`WaterDetectionNotifier`)**:
    *   Watches water sensors for the washing machine, bedroom bathroom, and master bathroom.
    *   Triggers repeat warnings every 5 minutes if wet, and sends Gotify alerts when wet/dry.

---

### ⏰ Cron & Scheduled Tasks (`cron/`)
*   **Espresso Machine Off**: Daily at `12:00:00` PM, turns off `switch.kitchen_espresso`.
*   **Daily Motion Reset**: Daily at `04:00:00` AM, cycles master motion controls to clear any temporary overrides and ensure motion control is re-enabled for the morning.
