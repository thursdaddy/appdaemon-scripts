# Automations & Settings Catalog

This catalog outlines all active AppDaemon automation apps, their configurations, monitored entity IDs, and schedules.

---

## 🌡️ Climate & HVAC Control (`climate/`)

### **Climate Schedule (`ClimateSchedule`)**
*   **App Class / Module**: `ClimateSchedule` / `hvac` (defined in [hvac.py](file:///Users/thurs/dev/appd/apps/climate/hvac.py))
*   **Target Entity**: `climate.nest`
*   **Power Reference**: `4.1 kW` (estimated cooling power draw for American Standard® 3.5-ton heat pump)
*   **Tariff Setpoint Logic (E-16 Plan)**:
    *   **Super Off-Peak** (08:00:00 – 15:00:00, Daily): `75.0°F` (Pre-cooling window)
    *   **On-Peak** (17:00:00 – 22:00:00, Weekdays only): `85.0°F` (Load-shedding window)
    *   **Off-Peak** (Fallback, all other times): `78.0°F`

### **HVAC Cost Tracker (`HVACCostTracker`)**
*   **App Class / Module**: `HVACCostTracker` / `tracker` (defined in [tracker.py](file:///Users/thurs/dev/appd/apps/climate/tracker.py))
*   **Source Entity**: `sensor.hvac_cooling` (history stats tracking compressor run runtime)
*   **Output Entity**: `sensor.hvac_cost_tracker`
*   **E-16 Tariff Tiers**:
    *   **Summer** (May 1 – Oct 31): Peak = `$0.1257/kWh`, Off-Peak = `$0.0995/kWh`, Super Off-Peak = `$0.0393/kWh`
    *   **Winter** (Nov 1 – Apr 30): Peak = `$0.1051/kWh`, Off-Peak = `$0.0907/kWh`, Super Off-Peak = `$0.0425/kWh`
*   **Glitch & Reboot Protection**: Ignore runtime sensor resets or drops throughout the day. Baselines are only reset near midnight (between `23:55` and `00:05`).

---

## 🛡️ Smart Locks & Security (`locks/` & `tags/`)

### **Automated Lock Controls (`LockDoors`)**
*   **App Class / Module**: `LockDoors` / `locks` (defined in [locks.py](file:///Users/thurs/dev/appd/apps/locks/locks.py))
*   **Monitored Entities**:
    *   Front Door: `lock.lock_front_door` + `binary_sensor.magnet_front_door`
    *   Back Door: `lock.lock_back_door` + `binary_sensor.magnet_back_door`
*   **Logic**:
    *   **Auto-Lock**: Trigger lock command 30 seconds after the door magnet status returns to closed.
    *   **Left-Open/Jammed Alerts**: Checks state 15 seconds after unlocking/jamming. Sends Gotify notification if the door is left open or jammed when you are away.
    *   **Magnet Break Alerts**: Sends a Gotify alert notifying which door was opened the moment a door magnet is separated.

### **NFC Tag Unlocks (`UnlockDoor`)**
*   **App Class / Module**: `UnlockDoor` / `locks`
*   **Entities**:
    *   `tag.front_door_unlock` -> Unlocks `lock.lock_front_door`
    *   `tag.back_door_unlock` -> Unlocks `lock.lock_back_door`

---

## 📍 Proximity & Location (`location/`)

### **Smart Lock Camera Controller (`CameraLockControl`)**
*   **App Class / Module**: `CameraLockControl` / `camera` (defined in [camera.py](file:///Users/thurs/dev/appd/apps/location/camera.py))
*   **Tracking Sensors**: `device_tracker.pixel_7_pro` and `sensor.pixel_7_pro_wi_fi_connection`
*   **Behavior**:
    *   Arriving home (transitioning tracker to "home" or connecting to home Wi-Fi) initiates a **5-minute welcome window**.
    *   If motion is detected on cameras (`binary_sensor.g4_doorbell_person_detected` or `binary_sensor.back_door_person_detected`) within this window, the door unlocks automatically.
    *   The window is cancelled immediately once the door magnet opens or the door is successfully unlocked.
    *   If the 5-minute window expires without person detection, a Gotify notice is sent.

### **Welcome Lights (`LocationChange`)**
*   **App Class / Module**: `LocationChange` / `lights` (defined in [lights.py](file:///Users/thurs/dev/appd/apps/location/lights.py))
*   **Tracking Sensors**: `sensor.pixel_7_pro_wi_fi_connection` (driveway Wi-Fi detection) or GPS arrival.
*   **Target Entities**: `light.living_room_main_lights` and `light.hallway_main_lights`
*   **Schedule Window**: Active **only** between 1 hour before sunset (`"sunset - 01:00:00"`) and `sunrise`.
*   **Settings**: Turns on lights at `50%` brightness for `2 minutes` (120s) upon arrival, then shuts off.

### **Away Mode (`AwayMode`)**
*   **App Class / Module**: `AwayMode` / `away` (defined in [away.py](file:///Users/thurs/dev/appd/apps/location/away.py))
*   **Logic**: Triggers when tracker transitions to away to override heating/cooling and lighting rules.

---

## 💡 Motion-Activated Lighting & Switches (`motion/` & `magnet/`)

### **Kitchen Cabinets (`MotionLights`)**
*   **Sensor**: `zigbee2mqtt/motion_kitchen`
*   **Schedules**:
    *   **Day** (sunrise to `18:00:00`): Under-cabinet and above-cabinet lights to `100%`, 5 min delay.
    *   **Evening** (`18:00:01` to `21:00:00`): Under-cabinet and above-cabinet lights to `100%`, 10 min delay.
    *   **Night** (`21:00:01` to sunrise): Under-cabinet light only to `30%`, 30s delay.

### **Kitchen Main (`MotionLights`)**
*   **Sensor**: `zigbee2mqtt/motion_kitchen`
*   **Schedules**:
    *   **Day** (sunrise to `12:00:00`): Bar lights at `30%`, 60s delay.
    *   **Afternoon** (`12:00:01` to `16:00:00`): Bar + Hallway lights at `50%`, 30s delay.
    *   **Evening** (`16:00:01` to `21:00:00`): Bar + Hallway lights at `50%`, 30s delay.
    *   **Night** (`21:00:01` to sunrise): Hallway lights at `25%`, 10s delay.

### **Office Motion (`MotionRGBLight` with Lux)**
*   **Sensor**: `zigbee2mqtt/motion_office`
*   **Target**: `light.office_desk`
*   **Lux Sensor**: `sensor.motion_office_illuminance`
*   **Lux Ranges**: Scales brightness between `50 lx` (minimum `10%` brightness) and `250 lx` (uses target schedule brightness).
*   **Schedules**:
    *   **Day** (sunrise to `18:00:00`): Color `[255, 247, 255]` (Cool Pink) @ `80%` brightness, 5 min delay.
    *   **Evening** (`18:00:01` to `22:00:00`): Color `[255, 157, 71]` (Warm Amber) @ `100%` brightness, 2 min delay.
    *   **Night** (`22:00:01` to `04:00:00`): Color `[255, 110, 84]` (Soft Red) @ `60%` brightness, 60s delay.

### **Stairway Motion (`MotionRGBLight`)**
*   **Sensor**: `zigbee2mqtt/motion_stairway`
*   **Schedules**:
    *   **Day** (sunrise to `18:00:00`): Warm Amber `[255, 157, 71]` @ `80%`, 2 min delay.
    *   **Evening** (`18:00:01` to `22:00:00`): Warm Amber `[255, 157, 71]` @ `60%`, 2 min delay.
    *   **Night** (`22:00:01` to `sunrise - 00:00:01`): Dim Red `[255, 28, 20]` @ `1%`, 30s delay (only turns on `light.upstairs_light_1`).

### **Printer Area (`MotionRGBLight`)**
*   **Sensor**: `zigbee2mqtt/motion_printer`
*   **Schedules**:
    *   **Day** (sunrise to `23:00:00`): Cool White `[255, 247, 255]` @ `80%`, 2 min delay.
    *   **Night** (`23:00:01` to `sunrise - 00:00:01`): Red `[255, 28, 20]` @ `20%`, 30s delay (only turns on `light.printer_lower`).

### **SIM Room Motion Controller (`MotionSwitch`)**
*   **Sensor**: `zigbee2mqtt/motion_sim`
*   **Bypasses**: Respects room-level `input_boolean.motion_sim` and global `input_boolean.motion_all` switches.
*   **Desk Light (`sim_motion_light`)**:
    *   Target: `switch.sim_desk_light`
    *   Schedules:
        *   Day (`sunrise` to `23:00:00`): 15 min (900s) delay.
        *   Night (`23:00:01` to `sunrise - 00:00:01`): 30s delay.
*   **Espresso Machine (`sim_motion_espresso`)**:
    *   Target: `switch.kitchen_espresso`
    *   Schedule: Active **only** in the morning between `sunrise` and `11:00:00` AM. Turns on when motion is detected; does not schedule an auto-off delay.

### **Pantry Door (`PantryLight`)**
*   **Sensor**: `binary_sensor.magnet_pantry_door`
*   **Target**: `light.pantry_leds`
*   **Logic**: Turns on when door opens; automatically turns off after `5 minutes` (300s).

---

## 🎛️ Physical Remotes & Buttons (`pico/` & `button/`)

### **Office Pico Remote**
*   **Target**: `device_name: office` (monitored via `PicoEvent`)
*   **Mappings**:
    *   `On`: Turns on `light.office_desk`.
    *   `Off`: Turns off `light.office_desk`.
    *   `Lower`: Turns off `light.office_desk` and disables motion control (`input_boolean.motion_office` = off).
    *   `Stop`: Toggles `input_boolean.motion_office` (enable/disable office motion controls).

### **Living Room Pico Remote**
*   **Target**: `device_name: livingroom`
*   **Mappings**:
    *   `On` / `Off`: Controls `light.living_room_main_lights`.
    *   `Stop`: Force-enables office motion controls (`input_boolean.motion_office` = on).

### **SIM Room Pico Remote**
*   **Target**: `device_name: sim`
*   **Mappings**:
    *   `On` / `Off`: Toggles activity state (`input_boolean.activity_sim`).
    *   `Lower`: Toggles `switch.sim_fan`.
    *   `Raise`: Toggles `switch.sim_spotlight`.

### **Bedroom Smart Button**
*   **Target**: Monitored via `ButtonPress`
*   **Mappings**:
    *   **Single Press**: Turns off all house lights (`input_boolean.lights_all` = off).
    *   **Double Press**: Disables all motion automation (`input_boolean.motion_all` = off).
    *   **Hold**: Triggers sleep on PC `c137` (`input_boolean.computer_c137` = off).

---

## 🔌 Smart Switches & Power Automation (`switches/`)

### **Power Controlled TV Backlights**
*   **Monitored Power**: `sensor.living_room_tv_current_consumption`
*   **Target**: `light.tv_lights`
*   **Thresholds**: Turns ON above `30W`, turns OFF 30s after dropping below `25W`.

### **Power Controlled 3D Printer Lights**
*   **Monitored Power**: `sensor.3d_printer_current_consumption`
*   **Target**: `switch.printer_lights`
*   **Thresholds**: Turns ON above `10W`, turns OFF 10s after dropping below `5W`.

### **PC Power & State Controllers**
*   **Wake-on-LAN & Sleep Manager**: Sends sleep commands via HTTP (`http://<host>:8009/sleep`) and wakes via WOL packet.
*   **Monitored Devices**:
    *   **PC C137**: `192.168.10.137` / `input_boolean.computer_c137`
    *   **PC Gamer**: `192.168.10.169` / `input_boolean.computer_gamer`
    *   **PC Sim**: `192.168.10.116` / `input_boolean.computer_sim`

### **SIM Room Activity (`BooleanSIM`)**
*   **Trigger**: `input_boolean.activity_sim` state changes.
*   **Target Entities**: Controls spotlights, the projector, the SIM fan, and boots up PC Sim via Wake-on-LAN.

---

## 💧 Leak & Flood Detection (`water/`)
*   **Monitored Sensors**: Leak sensors for washing machine, bedroom bathroom, and master bathroom.
*   **Logic**: Sends Gotify alert upon transition to wet/dry. If wet, repeats warnings every 5 minutes.

---

## ⏰ Cron & Scheduled Tasks (`cron/`)
*   **Espresso Off**: Daily at `12:00:00` PM, turns off `switch.kitchen_espresso`.
*   **Daily Motion Reset**: Daily at `04:00:00` AM, cycles `input_boolean.motion_all` to clear room-level overrides.
