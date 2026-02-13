# Migration Plan: I2C Hardware Control → Serial Relay Control

**Project:** vst_gm_control_panel
**Date:** February 8, 2026
**Purpose:** Replace direct I2C MCP23017/ADS1015 hardware control with serial commands to ESP32 (Walter IO Board Rev 10)

---

## 1. Current Architecture Analysis

### How the Program Works Today

The Linux control panel (`main.py`) is a Kivy/KivyMD industrial control application that manages vapor recovery compressor cycles at gas stations. It communicates with hardware over an I2C bus shared between two chips:

**Hardware Devices (currently on I2C bus):**
- **MCP23017** (I2C address `0x20`): 16-pin GPIO expander used for relay outputs and sensor inputs
- **ADS1115** (I2C address `0x48`): 16-bit ADC used for pressure sensing (channel P0) and motor current sensing (channels P2/P3)

**Key Files and Their Roles:**

| File | Role |
|------|------|
| `main.py` | Application entry point, UI management, cycle orchestration, alarm coordination |
| `controllers/io_manager.py` | **PRIMARY CHANGE TARGET** — All I2C relay control and ADC current reading |
| `controllers/pressure_sensor.py` | **REMOVE ENTIRELY** — All I2C ADC pressure reading |
| `utils/modem.py` | Serial communication with ESP32 — needs expanded parsing |
| `utils/alarm_manager.py` | Alarm checking — reads TLS (overfill) pin via I2C |
| `utils/data_handler.py` | Telemetry logging — gets mode number for serial transmission |

---

### Current I2C Pin Usage (MCP23017)

| Pin | Name | Direction | Purpose |
|-----|------|-----------|---------|
| GPA0 (pin 0) | `motor` | OUTPUT | Motor relay (CR0) |
| GPA1 (pin 1) | `v1` | OUTPUT | Valve 1 relay (CR1) |
| GPA2 (pin 2) | `v2` | OUTPUT | Valve 2 relay (CR2) |
| GPA3 (pin 3) | `v5` | OUTPUT | Valve 5 relay (CR5) |
| GPA4 (pin 4) | `shutdown` | OUTPUT | DISP_SHUTDN relay (GPIO13 on ESP32) |
| GPB0 (pin 8) | `tls` | INPUT | Tank Level Switch / Overfill sensor |
| GPB2 (pin 10) | `panel_power` | INPUT | Panel power detection |

### Current ADC Usage (ADS1115)

| Channel | Purpose | Read By |
|---------|---------|---------|
| P0 | Pressure sensor | `PressureSensor.get_pressure()` via `io_manager._sensor_reading_loop()` |
| P2 | Motor current (positive) | `IOManager.get_current()` via `io_manager._sensor_reading_loop()` |
| P3 | Motor current (negative) | `IOManager.get_current()` — differential with P2 |

---

### How Mode/Relay Control Currently Works

**YES, modes call a function that sets specific pin combinations.** The function is `IOManager.set_mode(mode_string)` at line 744 of `io_manager.py`.

The mode-to-pin mapping table (line 752-759):

```python
modes = {
    'run':   {'motor': True,  'v1': True,  'v2': False, 'v5': True},
    'rest':  {'motor': False, 'v1': False, 'v2': False, 'v5': False},
    'purge': {'motor': True,  'v1': False, 'v2': True,  'v5': False},
    'burp':  {'motor': False, 'v1': False, 'v2': False, 'v5': True},
    'bleed': {'motor': False, 'v1': False, 'v2': True,  'v5': True},
    'leak':  {'motor': False, 'v1': True,  'v2': True,  'v5': True}
}
```

**Call chain:**
1. `main.py` decides to run a cycle (e.g., `start_run_cycle()`)
2. Calls `io.run_cycle()` which creates a sequence like `[('run', 120), ('rest', 2), ('purge', 50), ('burp', 5), ...]`
3. `process_sequence()` spawns a **child process** (multiprocessing)
4. Child calls `set_sequence()` → iterates through steps → `process_mode(mode_str)`
5. `process_mode()` spawns another child process calling `set_mode(mode_str)`
6. `set_mode()` writes individual pin values via `self.pins[pin].value = True/False` over I2C

**This is the critical insight:** The entire chain boils down to setting a *mode string* which maps to a *fixed set of relay states*. The ESP32 Rev 10 firmware already implements identical mode-to-relay mapping via `setRelaysForMode(modeNum)`.

### Recommendation: Send Mode Number Over Serial

Instead of setting individual pins via I2C, the simplest approach is:

1. **Map mode strings to ESP32 mode numbers** (already defined in firmware):
   - `rest` → `0`, `run` → `1`, `purge` → `2`, `burp` → `3`, `bleed` → `8`, `leak` → `9`
2. **Send `{"type":"data", "mode": N}` via serial** every time a mode changes
3. **ESP32 handles physical relay control** — no I2C MCP23017 needed at all

For `shutdown`: Send `{"type":"data", "mode": "shutdown"}` (string, not integer).

---

### How Pressure Is Currently Obtained

1. `IOManager.__init__()` creates `PressureSensor(self._adc)` at line 261
2. `start_background_sensors()` starts `_sensor_reading_loop()` thread (line 366)
3. Thread calls `pressure_sensor.get_pressure()` every ~0.2s (line 399)
4. `get_pressure()` → `_collect_pressure_samples()` → `_read_adc_value()` → reads `AnalogIn(adc, ADS.P0).value`
5. Raw ADC value is converted to IWC pressure using linear calibration
6. Result cached in `_cached_pressure`, UI reads via `get_cached_pressure()`

**After migration:** ESP32 sends `{"pressure": -1.25}` in its 15-second status packet, and the value is already computed with rolling averages at 60Hz. Linux just reads the latest value.

### How Current Is Currently Obtained

1. `IOManager.__init__()` creates `AnalogIn` channels for P2 and P3 (lines 253-254)
2. `_sensor_reading_loop()` calls `get_current()` every ~0.2s (line 408)
3. `get_current()` → `_collect_adc_readings()` → reads 60 samples of `abs(channel2 - channel3)`
4. Result is mapped from ADC range to amps via `map_value(max, 1248, 4640, 2.1, 8.0)`
5. Cached in `_cached_current`, UI reads via `get_cached_current()`

**After migration:** ESP32 sends `{"current": 5.23}` in its status packet, already computed with rolling averages.

### How Cycles/Count Is Managed

- `main.py` line 1161: `gm_db.get_setting('run_cycle_count')` / `gm_db.add_setting('run_cycle_count', N)`
- Incremented each time `run_cycle()` is called (line 1158-1162)
- Sent to ESP32 in modem.py payload as `cycles` field
- **No change needed** — stays in Linux database

### How Date/Time Is Managed

- `main.py` line 966: `get_datetime()` uses `datetime.now()` with timezone
- ESP32 provides its modem-synced UTC time in `datetime` field of status packets
- **No change needed** — Linux keeps its own clock, ESP32 keeps its modem-synced clock

### How Overfill (TLS) Is Currently Checked

- `alarm_manager.py` line 685: `tls_active = context.app.io.pins['tls'].value` — **direct I2C read**
- This reads MCP23017 pin 8 (GPB0) over I2C
- **After migration:** ESP32 sends `{"overfill": 0|1}` in its status packet (every 15 seconds). The alarm manager should use this value instead of I2C.

---

## 2. Migration Plan — File by File

### 2.1 `controllers/io_manager.py` — MAJOR CHANGES

**What to change:**
1. **Remove all MCP23017 I2C imports and initialization** (lines 27-29, 247-271)
2. **Remove all ADC/ADS1115 imports and initialization** (lines 27-28, 250-258)
3. **Remove `PressureSensor` import and usage** (line 35, 261)
4. **Replace `set_mode()` function** — instead of setting individual pin values over I2C, send mode number via serial to ESP32
5. **Replace `set_rest()`, `set_bleed()`** — send mode 0 and mode 8 via serial
6. **Remove `set_shutdown_relay()`** — send `{"type":"data","mode":"shutdown"}` via serial
7. **Remove `_collect_adc_readings()`, `get_current()`, `_sensor_reading_loop()`** — ESP32 provides these values
8. **Remove `setup_pins()`, `reset_i2c()`, `_ensure_hardware_for_child_process()`** — no I2C
9. **Remove `_mcp_lock`** — no shared I2C bus
10. **Replace `get_cached_pressure()` and `get_cached_current()`** — read from serial manager's latest ESP32 status
11. **Remove `pins` dictionary entirely** — no MCP pins
12. **Keep `ModeManager`** — still useful for ultra-fast local mode tracking
13. **Keep buzzer code** — uses pigpio directly, not I2C
14. **Keep process management** (cycle_process, mode_process, process_sequence, set_sequence) — the cycle timing logic stays on Linux, only the relay activation moves to serial

**New function needed:**
```python
def send_mode_to_esp32(self, mode_string):
    """Send relay mode command to ESP32 via serial.
    
    Maps mode string to ESP32 mode number and sends via serial.
    
    Args:
        mode_string: 'rest', 'run', 'purge', 'burp', 'bleed', 'leak'
    
    Mode number mapping (matches ESP32 setRelaysForMode()):
        rest  → 0 (all off)
        run   → 1 (motor + CR1 + CR5)
        purge → 2 (motor + CR2)
        burp  → 3 (CR5 only)
        bleed → 8 (CR2 + CR5, labeled FRESH_AIR on ESP32)
        leak  → 9 (CR1 + CR2 + CR5)
    """
    MODE_MAP = {
        'rest': 0, 'run': 1, 'purge': 2, 'burp': 3,
        'bleed': 8, 'leak': 9
    }
    mode_num = MODE_MAP.get(mode_string, 0)
    # Access serial_manager from app
    serial_mgr = self.app.serial_manager
    if serial_mgr and serial_mgr.serial_port and serial_mgr.serial_port.is_open:
        import json
        msg = json.dumps({"type": "data", "mode": mode_num}, separators=(',', ':'))
        serial_mgr.serial_port.write((msg + '\n').encode('ascii'))
        serial_mgr.serial_port.flush()
```

### 2.2 `controllers/pressure_sensor.py` — REMOVE ENTIRELY

This entire file reads the ADS1115 ADC over I2C. After migration, pressure comes from the ESP32's 15-second status packet. The `PressureSensor` class and all its methods become dead code.

**Action:** Comment out the entire file or delete its contents. Remove the import from `io_manager.py`.

### 2.3 `utils/modem.py` — EXPAND PARSING

**Current state:** Already receives JSON from ESP32 every 1 second (`_receive_cycle`). Parses `datetime`, `sdcard`, `passthrough`, `lte`, `rsrp`, `rsrq`.

**What to add:**
1. Parse `pressure` field from ESP32 status → store as `self.esp32_pressure`
2. Parse `current` field from ESP32 status → store as `self.esp32_current`
3. Parse `overfill` field from ESP32 status → store as `self.esp32_overfill`
4. Parse `profile` field from ESP32 status → store as `self.esp32_profile`
5. Parse `failsafe` field from ESP32 status → store as `self.esp32_failsafe`
6. **Confirm data is NOT sent during passthrough** — already handled at line 824: `if self.is_passthrough_active(): return`
7. Add a method `send_mode_command(mode_num)` for IOManager to call

**New instance variables:**
```python
self.esp32_pressure = 0.0
self.esp32_current = 0.0
self.esp32_overfill = False
self.esp32_profile = ''
self.esp32_failsafe = False
```

**Add to `receive_esp32_status()` parsing block (after line 548):**
```python
if 'pressure' in data:
    try:
        self.esp32_pressure = float(data['pressure'])
    except (ValueError, TypeError):
        pass

if 'current' in data:
    try:
        self.esp32_current = float(data['current'])
    except (ValueError, TypeError):
        pass

if 'overfill' in data:
    self.esp32_overfill = bool(int(data['overfill']))

if 'profile' in data:
    self.esp32_profile = data['profile']

if 'failsafe' in data:
    self.esp32_failsafe = bool(int(data['failsafe']))
```

### 2.4 `utils/alarm_manager.py` — CHANGE OVERFILL CHECK

**Current (line 685):**
```python
tls_active = context.app.io.pins['tls'].value  # I2C read
```

**Replace with:**
```python
tls_active = context.app.serial_manager.esp32_overfill  # From serial data
```

This uses the latest ESP32 status (updated every 1 second in the receive cycle). The ESP32 reads GPIO38 with hysteresis validation and sends `"overfill": 0|1` in every status packet.

### 2.5 `main.py` — MINOR CHANGES

**Changes needed:**
1. `get_pressure()` (line 994) — change `self.io.get_cached_pressure()` to read from `self.serial_manager.esp32_pressure`
2. `get_amps()` (line 1056) — change `self.io.get_cached_current()` to read from `self.serial_manager.esp32_current`
3. Remove `self.io.start_background_sensors()` call (line 412) — no more sensor thread needed
4. `fifteen_second_updates()` (line 516) — add occasional relay status confirmation
5. The mode number sent in the serial payload (`modem.py` `_get_mode()`) already works correctly

### 2.6 `utils/data_handler.py` — NO CHANGES NEEDED

The `get_current_mode()` function (line 227) reads from `ModeManager` (memory-mapped file), which is still updated by `IOManager.set_mode()`. This continues to work.

---

## 3. Delays to Remove

The following `time.sleep()` calls in `io_manager.py` exist to allow I2C bus settling. With serial commands, they are unnecessary:

| Location | Delay | Reason to Remove |
|----------|-------|-----------------|
| `set_mode()` line 829: `time.sleep(0.2)` | 200ms | Was for I2C pin verification after mode set |
| `set_mode()` line 824: `sleep_with_check(self.pin_delay)` | 10ms per pin | Was for I2C pin settling between each pin write |
| `setup_pins()` line 495: `time.sleep(0.1)` | 100ms | Was for I2C retry delay |
| `set_rest()` line 566: `time.sleep(0.1)` | 100ms | Was for I2C retry delay |
| `reset_i2c()` line 1967: `time.sleep(0.1)` | 100ms+ | Entire function removed |

**Impact:** These delays add up to 250-500ms per mode change. Removing them means relay changes happen at serial speed (~1ms).

---

## 4. What Stays the Same

- **Cycle sequencing logic** — Linux still decides when to run, purge, burp, etc.
- **Alarm management** — Linux still manages all alarm state, 72-hour shutdown, etc.
- **Database operations** — All SQLite databases stay on Linux
- **ModeManager** — Memory-mapped file for fast mode tracking stays
- **Buzzer control** — Uses pigpio directly, not I2C
- **UI/Kivy** — No UI changes needed
- **Multiprocessing** — Cycle processes still used for timing isolation
- **modem.py serial send/receive** — Already implemented, just needs expanded parsing

---

## 5. Summary of Simple Solution

The simplest path is:

1. **`set_mode()` sends a serial JSON instead of writing I2C pins** — one function change
2. **Pressure and current come from ESP32 serial data** — already being received, just add parsing
3. **Overfill reads from serial data** — one line change in alarm_manager
4. **Remove all I2C imports and initialization** — cleanup dead code
5. **Remove `pressure_sensor.py`** — entirely replaced by ESP32 ADC
6. **Remove sensor background thread** — no longer needed
7. **Remove all I2C retry/reset logic** — no I2C bus to manage

The ESP32 handles all the hard real-time requirements (60Hz ADC, relay GPIO, overfill hysteresis). Linux just sends mode commands and receives sensor values.
