# Changelog: Rev 10 Serial-Only Build

**Date:** February 9, 2026  
**Build Version:** 2.5 — Serial-Only (MCP23017/ADS1115 phased out)  
**Purpose:** Optimized Python control panel for ESP32 IO Board Rev 10+. All I2C hardware code removed. Relay control and sensor data flow exclusively via serial JSON.

---

## Build Type

**This is the SERIAL-ONLY production build.** There is NO I2C fallback. The MCP23017-based IO board is phased out.

**Backward-compatible files** (with I2C fallback) are preserved in:
```
_backup_i2c_compatible/
```
See that directory's `README.md` for restoration instructions.

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────┐
│  Python (Linux)                                             │
│                                                             │
│  IOManager                    SerialManager (modem.py)      │
│  ┌──────────────┐            ┌────────────────────────┐     │
│  │ ModeManager   │──mmap──▶  │ _mode_check_cycle()    │     │
│  │ (mmap file)   │  100ms    │ polls mode, sends      │     │
│  │               │  poll     │ {"type":"data","mode":N}│     │
│  └──────────────┘            │         │               │     │
│                              │         ▼               │     │
│  Sensor cache ◀── reads ──── │ esp32_pressure          │     │
│  _cached_pressure            │ esp32_current           │──── │ ─── /dev/serial0 ───▶ ESP32
│  _cached_current             │ esp32_overfill          │     │
│                              └────────────────────────┘     │
│                                                             │
│  AlarmManager                                               │
│  ┌──────────────┐                                           │
│  │ OverfillCond  │─── reads ──▶ serial_mgr.esp32_overfill  │
│  └──────────────┘                                           │
└────────────────────────────────────────────────────────────┘
```

---

## What Changed from the Original Python Program (vs. the I2C Build)

The original Python control panel communicated directly with the IO Board hardware using the I2C protocol. The Linux device acted as the I2C bus master, controlling the MCP23017 GPIO expander (for relay switching) and reading the ADS1115 ADC (for pressure and current sensors). Every relay toggle required multiple sequential I2C pin writes with retry logic, and every sensor reading required a multi-step ADC sampling pipeline running in Python threads.

The updated serial-only build removes ALL of this. The ESP32 now owns all hardware I/O. Python communicates exclusively over a serial line using JSON text messages. The following sections describe every difference in detail.

---

## File: `controllers/io_manager.py` — Major Rewrite

This is the largest change. Roughly 300 lines of I2C-specific code were removed and replaced with serial JSON equivalents.

### Removed: I2C Hardware Imports (original lines 7-8, 27-29, 35)
- `import board`, `import busio`, `from digitalio import Direction`
- `import adafruit_ads1x15.ads1115 as ADS`
- `from adafruit_ads1x15.analog_in import AnalogIn`
- `from adafruit_mcp230xx.mcp23017 import MCP23017`
- `from .pressure_sensor import PressureSensor`

**Why:** ESP32 Rev 10 handles all hardware I/O. These libraries require the I2C bus to have an MCP23017 and ADS1115 — which no longer exist on the board.

### Removed: `MockPin` class (original lines 38-50)
### Removed: `MockADCChannel` class (original lines 53-60)

**Why:** Mock objects were needed for graceful degradation when I2C was unavailable. In the serial-only build, `_StubPin` (inline class) replaces `MockPin` for structural compatibility. `MockADCChannel` is gone entirely — no ADC channels exist in Python.

### Replaced: `__init__()` Hardware Initialization (original lines 247-274)
**Original:** Full I2C bus init → MCP23017 → ADS1115 → pin objects → PressureSensor  
**Updated:** `_StubPin` objects in `self.pins` dict + `hardware_available = False` constant

**Why:** No I2C bus to initialize. The `_StubPin` objects accept `.value` reads/writes silently so any code referencing `self.pins['x'].value` won't crash.

### Removed: `_init_mock_hardware()` (original lines 329-364)
**Why:** No need for mock mode when there's no hardware to mock.

### Replaced: `setup_pins()` → No-op (original lines 505-553)
**Original:** MCP23017 pin direction configuration with retry logic  
**Updated:** Single log line — ESP32 configures its own GPIOs

### Replaced: `set_rest()` — Simplified (original lines 569-635)
**Original:** I2C pin writes with retry loops and I2C bus reset on failure  
**Updated:** ModeManager mmap update only → serial manager sends mode 0 to ESP32

### Replaced: `set_bleed()` — Simplified (original lines 637-652)
**Original:** I2C pin writes with `_ensure_hardware_for_child_process()`  
**Updated:** Stub pin updates for tracking → serial manager sends mode 8 to ESP32

### Replaced: `_ensure_hardware_for_child_process()` → No-op (original lines 714-771)
**Original:** Full I2C reinitialization after fork() — fresh bus, MCP23017, pins  
**Updated:** `pass` — ModeManager mmap is fork-safe, no I2C to reinitialize

### Replaced: `set_mode()` — Simplified (original lines 773-863)
**Original:** ModeManager update + I2C pin writes with retry loops + bus reset. Included `_mcp_lock.acquire()`, per-pin retry loop, `reset_i2c()` calls, `pin_delay` sleep per pin.  
**Updated:** ModeManager mmap update + stub pin updates + **direct serial send** when running in main process (instant ~1ms relay control). Child processes write to mmap; modem.py polling detects the change and sends via serial.

### Replaced: `process_mode()` — Direct Call (original spawned subprocess)
**Original:** Spawned a new `multiprocessing.Process()` for each mode change. On Raspberry Pi, `fork()` takes 200-500ms — adding massive latency to every cycle step. This was needed in the old I2C build because MCP23017 pin writes could block/hang.  
**Updated:** `set_mode()` is called directly — no subprocess. Since `set_mode()` now just writes to mmap (~0.1ms), there's no blocking risk and no reason to fork.

### Replaced: `_sensor_reading_loop()` — Serial-Only (original lines 390-452)
**Original:** `if hardware_available: read_ADC() elif: serial_fallback()`  
**Updated:** Always reads from `serial_manager.esp32_pressure` and `.esp32_current` — no conditional branching

### Removed: ADC Current Methods (original lines 1481-1570)
The following five methods were removed entirely:
- `_collect_adc_readings()` — Collected 60 ADC samples with MCP bus priority
- `_handle_current_failure()` — Failure count tracking with cached value fallback
- `_process_current_readings()` — Outlier removal and max value extraction
- `_calculate_current_value()` — ADC-to-amps calibration mapping
- `_format_and_cache_result()` — Format and cache ADC result

**Why:** ESP32 performs all ADC sampling, filtering, and calibration at 60Hz.

### Replaced: `get_current()` → Returns Cached Serial Value (original lines 1572-1608)
**Original:** Full ADC pipeline (collect → process → calculate → format)  
**Updated:** `return self.get_cached_current()` (one line)

### Replaced: `reset_i2c()` → No-op (original lines 1985-2029)
**Original:** Full I2C bus tear-down and re-initialization with retry logic  
**Updated:** Returns `True` with a debug log — no bus to reset. Kept as no-op because some error-handling code paths still call it.

### Replaced: `set_shutdown_relay()` — Serial-Only (original lines 1779-1803)
**Original:** MCP23017 pin 4 write + serial fallback  
**Updated:** Sends `send_shutdown_command()` only → `{"mode":"shutdown"}` to ESP32

### Updated: `cleanup()` — Serial Rest Command (original was pin-by-pin I2C write)
**Updated:** Sends `send_mode_immediate(0)` to ESP32 to idle all relays during shutdown.

---

## File: `controllers/io_manager.py` — Web Portal Screen Guard Fix (Rev 10.4)

### Fixed: Test/Cycle Functions Blocked by Kivy Screen Guard

**The Problem:** Every test and cycle function had a "screen guard" — a safety check that prevents the function from running unless the user is on the correct Kivy touchscreen. For example, `leak_test()` would only run if the touchscreen was on the `LeakTest` screen. If the user was on ANY other screen (Main, Maintenance, Faults, etc.), the function silently returned without doing anything.

This was by design for the touchscreen interface. But when the ESP32 web portal sends a command via serial (e.g., the user presses "Start" on the Leak Test web page), the Python program receives it while the touchscreen is sitting on whatever screen the operator left it on — typically `Main`. Since `Main` is in the blocked screen list, the command was silently discarded. No error, no log message — it just didn't work.

**The Fix:** Added a `from_web=False` parameter to all affected functions. When `from_web=True`, the Kivy screen guard is skipped entirely. The web portal has its own security (Maintenance password gate "878") so the guard is redundant for web commands.

**Functions fixed:**
- `leak_test(from_web=False)` — Leak Test (30 min, mode 9)
- `functionality_test(from_web=False)` — Functionality Test (10 x run/purge cycles)
- `efficiency_test_fill_run(from_web=False)` — Efficiency Test (120s fill/run)
- `canister_clean(from_web=False)` — Canister Clean (15 min motor run)
- `run_cycle(is_manual=False, from_web=False)` — Run Cycle and Manual Purge

**Why this is important:** Field technicians frequently use the web portal on their phones to run tests and start cycles remotely, especially when the touchscreen is not easily accessible (e.g., unit mounted high, inside enclosure). Without this fix, NONE of the web portal's test or cycle buttons worked unless someone happened to navigate the touchscreen to the exact matching Kivy screen first.

---

## File: `controllers/io_manager.py` — Diagnostic Logging for Leak Test (Rev 10.5)

### Added: Child Process Instrumentation in `set_sequence()`

**The Problem:** The leak test (and other web portal tests) sometimes failed silently — the timer started on the web portal then reset to `--:--` after about 3 seconds, with relays never activating. Because `set_sequence()` runs in a forked child process, exceptions were not visible in the normal application log.

**The Fix:** Added `Logger.debug()` calls throughout `set_sequence()` with `[CHILD PID=xxx]` prefixes, plus a `try/except/finally` wrapper that logs exceptions and the entry to `_end_sequence()`. These appear in the `gmctl` log on the Linux device and pinpoint exactly where the child process fails.

---

## File: `utils/modem.py` — Serial Communication Overhaul

This file was substantially expanded from a simple data transmitter into a bidirectional JSON communication hub.

### Added: ESP32 Status Variables (new)
The original `modem.py` only sent data TO the ESP32. It never received anything back. The updated version parses incoming ESP32 JSON packets and stores:
- `esp32_pressure` — Pressure in IWC (float, from ESP32 ADS1015)
- `esp32_current` — Motor current in amps (float, from ESP32 ADS1015)
- `esp32_overfill` — Overfill alarm state (bool, from ESP32 GPIO38)
- `esp32_datetime` — Modem timestamp (string)
- `esp32_sdcard_status` — SD card health ("OK" or "FAULT")
- `esp32_lte_connected` — LTE network status (bool)
- `esp32_rsrp` — Signal strength in dBm (float)
- `esp32_rsrq` — Signal quality in dB (float)
- `esp32_passthrough` — Passthrough mode flag (int)
- `esp32_profile` — Active profile name (string)
- `esp32_failsafe` — Failsafe mode flag (bool)

### Added: `receive_esp32_status()` — Full Bidirectional Parsing (new)
**Original:** Did not exist. The original `modem.py` was send-only.  
**Updated:** Parses every incoming JSON line from the ESP32, updates all cached status variables, handles passthrough requests, and dispatches web portal commands.

### Updated: `receive_esp32_status()` — Serial Buffer Drain (Rev 10.3)
**Original (Rev 10.0):** Called `self.serial_port.readline()` which reads the **oldest** message in the serial buffer. If the ESP32 sends a message every 200ms but Python doesn't read fast enough, messages pile up. Python would process data that was already 5-10 seconds old while newer data sat waiting in the buffer.

**Updated:** Reads **all** available lines from the serial buffer (up to 50) and uses only the **last** valid JSON message. This guarantees the pressure and current values are from the most recent ESP32 transmission (less than 1 second old).

**Why:** The Linux controller makes real-time decisions based on pressure readings (start cycles, detect alarms). Reading stale buffered data meant the controller was reacting to conditions that no longer existed.

### Updated: `_get_pressure()` — Direct ESP32 Read (Rev 10.3)
**Original:** Read from `self.data_handler.app.current_pressure` — a Kivy UI property formatted as `"-14.22 IWC"`. Required stripping the " IWC" suffix and converting back to float. This value was updated by a separate 1-second Kivy Clock timer, adding up to 1 additional second of staleness.

**Updated:** Reads `self.esp32_pressure` directly — the raw float value stored when the last serial packet was received. No string conversion, no UI dependency, no extra delay.

### Updated: `_get_current()` — Direct ESP32 Read (Rev 10.3, same fix as pressure)
**Original:** Read from `self.data_handler.app.current_amps` with " A" suffix parsing.  
**Updated:** Reads `self.esp32_current` directly.

### Updated: Debug Logging — Packet-Only Fields (Rev 10.5)
**Original:** The debug log printed ALL cached values (`self.esp32_datetime`, `self.esp32_rsrp`, etc.) on EVERY packet received. This made it look like the ESP32 was sending repeated datetime/cellular data every second, when in reality those were just stale cached values from a previous packet.

**Updated:** Now logs only the fields actually present in the current packet:
```python
received_fields = ', '.join(f'{k}={v}' for k, v in data.items())
self._log('debug', f'ESP32 packet: {received_fields}')
```

**Why:** This was causing confusion during debugging — the `gmctl` log showed `datetime=2026-02-09 13:10:49` repeated every second, making it appear the ESP32 was re-sending stale data when it was actually only the Python log printing cached values.

### Added: `send_mode_immediate()` — Instant Relay Control (new)
**Original:** Did not exist. Mode changes were only sent as part of the 15-second periodic payload.  
**Updated:** Sends a minimal JSON `{"type":"data","mode":N}` message to ESP32 immediately when a mode change is detected. This is the primary relay control path.

### Added: `send_shutdown_command()` — DISP_SHUTDN Control (new)
**Original:** Did not exist. The shutdown relay was controlled via I2C MCP23017 pin 4.  
**Updated:** Sends `{"mode":"shutdown"}` to ESP32, which is the only way to set GPIO13 LOW.

### Added: `_mode_check_cycle()` — ModeManager Polling (new)
**Original:** Did not exist. Mode changes were handled entirely through I2C pin writes.  
**Updated:** Runs every 100ms via Kivy Clock. Reads the current mode from the ModeManager mmap file (shared with forked child processes) and sends mode changes to ESP32 via `send_mode_immediate()`.

### Added: Web Portal Command Handlers (new in Rev 10.1, updated Rev 10.4)
**Original:** Did not exist. The web portal had no connection to Python.  
**Updated:** `receive_esp32_status()` now handles incoming commands forwarded by the ESP32 from the web portal:
- `start_cycle` with type `run` / `manual_purge` / `clean` → calls `app.io.run_cycle()` / `app.io.canister_clean()`
- `stop_cycle` → calls `app.io.stop_cycle()`
- `start_test` with type `leak` / `func` / `eff` → calls `app.io.leak_test()` / `app.io.functionality_test()` / `app.io.efficiency_test_fill_run()`

All web portal commands pass `from_web=True` to bypass the Kivy screen guard.

### Added: PPP Passthrough Management (new)
**Original:** PPP passthrough was not handled by modem.py.  
**Updated:** Full PPP lifecycle management including `connect_ppp()`, `disconnect_ppp()`, `handle_passthrough_request()`, `_start_ppp()`, `_stop_ppp()`, and `_ppp_timeout_monitor()`. Manages the `pppd` subprocess, serial port handoff, and automatic timeout.

### Added: `send_calibration_command()` — Pressure Sensor Zero Calibration (Rev 10.7)
**Original:** Did not exist. Pressure calibration was done locally in Python via `pressure_sensor.py calibrate()` using the ADS1115 ADC directly over I2C and saving to the Python database.  
**Updated:** Sends `{"type":"cmd","cmd":"cal"}` to ESP32 via serial. The ESP32 performs the calibration locally (60 samples, trimmed mean, sanity check) and saves the new zero point to EEPROM. Uses the new `"type":"cmd"` message type to keep commands separate from `"type":"data"` status packets.

**Why:** With the ADC now on the ESP32 (ADS1015), the calibration must happen on the ESP32 side. The Python program triggers it; the ESP32 executes and persists the result.

### Added: `ps_cal` Response Parser — Save ESP32 Calibration to Database (Rev 10.7)
**Original:** Did not exist. The original `pressure_sensor.py` saved the `adc_zero` value to `gm_db` after calibrating locally.  
**Updated:** `receive_esp32_status()` now parses the `ps_cal` field from incoming ESP32 JSON packets. When ESP32 completes a calibration, it sends `{"type":"data","ps_cal":964.50}` back via serial. Python receives this, extracts the value, and saves it to `app.gm_db.add_setting('adc_zero', cal_value)` — using the same database key as the original `pressure_sensor.py`.

**Why:** The calibration is now performed on the ESP32 side (where the ADS1015 ADC lives), but the Python database still needs a copy of the calibration factor for consistency and as a backup reference. The `ps_cal` response closes the loop: Python triggers calibration → ESP32 executes → ESP32 sends result back → Python saves to database.

**Code added (lines ~714-748):**
```python
if 'ps_cal' in data:
    try:
        cal_value = float(data['ps_cal'])
        self._log('info', f'Received pressure calibration from ESP32: ps_cal={cal_value}')
        if hasattr(self, 'data_handler') and self.data_handler:
            app = getattr(self.data_handler, 'app', None)
            if app and hasattr(app, 'gm_db'):
                app.gm_db.add_setting('adc_zero', cal_value)
                self._log('info', f'Saved pressure calibration to database: adc_zero={cal_value}')
    except (ValueError, TypeError) as e:
        self._log('error', f'Invalid ps_cal value: {data["ps_cal"]} — {e}')
```

---

## File: `views/contractor_screen.py` — Calibration Button Fix (Rev 10.7)

### Fixed: `show_calibration_dialog()` — Crash on Calibrate Button (Rev 10.7)
**Original:** Called `self.app.io.pressure_sensor.calibrate` as the dialog accept callback. In the serial-only build, `pressure_sensor` was removed from `IOManager` (the ADS1115 ADC is no longer on the Linux I2C bus), so pressing the button threw `AttributeError: 'IOManager' object has no attribute 'pressure_sensor'` and crashed the application.  
**Updated:** The `accept_method` now points to `self._send_calibration_to_esp32`, a new method on the contractor screen class.

**Error that was occurring:**
```
File "contractor_screen.py", line 303, in show_calibration_dialog
    accept_method=self.app.io.pressure_sensor.calibrate,
AttributeError: 'IOManager' object has no attribute 'pressure_sensor'
```

### Added: `_send_calibration_to_esp32()` — Serial Calibration Callback (Rev 10.7)
**Original:** Did not exist.  
**Updated:** New method called when user confirms the calibration dialog. Retrieves `self.app.serial_manager` and calls `send_calibration_command()`. Logs success/failure via Kivy Logger. Accepts `*args` to match the dialog callback signature.

**Code (lines ~321-343):**
```python
def _send_calibration_to_esp32(self, *args):
    from kivy.logger import Logger
    serial_mgr = getattr(self.app, 'serial_manager', None)
    if serial_mgr:
        result = serial_mgr.send_calibration_command()
        if result:
            Logger.info('PressureSensor: Calibration command sent to ESP32')
        else:
            Logger.warning('PressureSensor: Failed to send calibration command')
    else:
        Logger.error('PressureSensor: No serial manager available')
```

### Updated: Calibration Dialog Text (Rev 10.7)
**Original:** Warning text said "pressure sensor must be open to atmospheric air in order to calibrate."  
**Updated:** Docstring clarifies that calibration sets the current reading to 0.0 IWC regardless of altitude. If the sensor reads -0.5 IWC due to altitude, after calibration it will read 0.0 IWC.

---

## File: `utils/data_handler.py` — Mode Map Update

### Updated: `get_current_mode()` — Complete Mode Mapping
**Original:** Mode map only included `rest`, `run`, `purge`, `burp`.  
**Updated:** Added `bleed: 8` and `leak: 9` to match the ESP32's `setRelaysForMode()` relay mode numbers. Without these, bleed and leak modes would default to 0 (rest) and the ESP32 would set wrong relay states.

---

## File: `utils/alarm_manager.py` — I2C Read Removed

### Replaced: `OverfillCondition.check()` — Serial-Only (original lines 683-691)
**Original:** I2C TLS pin read → serial fallback  
**Updated:** Serial `esp32_overfill` read ONLY. The I2C `context.app.io.pins['tls'].value` read has been removed entirely.

**Why:** With no MCP23017 on the bus, the TLS pin read would always hit a `_StubPin` returning `False`, making the I2C path useless. ESP32's GPIO38 overfill detection with 8/5 hysteresis is more robust anyway.

---

## ESP32 Firmware: Web Portal Test Mode Guard (Rev 10.5)

### Fixed: Linux Serial Data Overriding Web Portal Tests

**The Problem:** When a test (leak, functionality, efficiency) is started from the ESP32 web portal, the ESP32 forwards the command to Linux, which spawns a child process and sets the relay mode. But the Linux periodic payload (sent every 15 seconds for CBOR data) also contains a `"mode"` field — typically `"mode":0` (rest). When the ESP32 received this periodic payload, it blindly called `setRelaysForMode(0)`, immediately killing the test that was in progress.

Additionally, if the Python child process crashes for any reason, it writes mode 0 to the mmap file on exit. The 100ms polling loop in `modem.py` detects this change and sends `"mode":0` to the ESP32 within milliseconds, also killing the test.

**The Fix:** Added a guard in the ESP32's `parsedSerialData()` function: when `testRunning == true` (set when the web portal starts a test), incoming `mode` fields from serial data are **ignored**. The test can only be stopped by:
- An explicit `stop_test` or `stop_cycle` command from the web portal
- An explicit `stop_cycle` command from Linux via serial
- The test timing out

The `stop_cycle` command handler (both from web and serial) now also clears `testRunning` and `activeTestType`, ensuring serial mode control resumes after a test ends.

**Debug output:** When a serial mode is blocked, the ESP32 logs:
```
[Serial] Mode 0 from Linux IGNORED — web test 'leak' in progress
```

---

## Web Portal Button Audit (Rev 10.4) — All Confirmed Working

| Screen | Button | Command | Handler | Status |
|--------|--------|---------|---------|--------|
| Main | Start Cycle | `start_cycle/run` | ESP32 → Linux `run_cycle(from_web=True)` | FIXED |
| Main | Stop | `stop_cycle` | ESP32 → Linux `stop_cycle()` | OK |
| Maintenance | Unlock | Client-side PW "878" | Shows menu | OK |
| Maintenance | Clear Press Alarm | `clear_press_alarm` | ESP32 local reset | OK |
| Maintenance | Clear Motor Alarm | `clear_motor_alarm` | ESP32 local reset | OK |
| Maintenance | Run Tests | `nav('tests')` | Navigation | OK |
| Maintenance | Diagnostics | `nav('diagnostics')` | Navigation | OK |
| Maintenance | Clean Canister | `nav('clean')` | Navigation | OK |
| Maintenance | Passthrough | `showPtModal()` | Modal + GET /setpassthrough | OK |
| Leak Test | Start | `start_test/leak` | ESP32 → Linux `leak_test(from_web=True)` | FIXED |
| Leak Test | Stop | `stop_test` | ESP32 → Linux `stop_cycle()` | OK |
| Functionality | Start | `start_test/func` | ESP32 → Linux `functionality_test(from_web=True)` | FIXED |
| Functionality | Stop | `stop_test` | ESP32 → Linux `stop_cycle()` | OK |
| Efficiency | Start | `start_test/eff` | ESP32 → Linux `efficiency_test_fill_run(from_web=True)` | FIXED |
| Efficiency | Stop | `stop_test` | ESP32 → Linux `stop_cycle()` | OK |
| Clean Canister | Start Clean | `start_cycle/clean` | ESP32 → Linux `canister_clean(from_web=True)` | FIXED |
| Clean Canister | Stop | `stop_cycle` | ESP32 → Linux `stop_cycle()` | OK |
| Manual Mode | Manual Purge | `start_cycle/manual_purge` | ESP32 → Linux `run_cycle(manual=True, from_web=True)` | FIXED |
| Manual Mode | Stop | `stop_cycle` | ESP32 → Linux `stop_cycle()` | OK |
| Profiles | Select + Confirm | `set_profile` + PW "1793" | ESP32 server-side validation | OK |
| Overfill Override | Confirm Override | `overfill_override` | ESP32 local reset | OK |
| Settings | Reboot ESP32 | `restart` | ESP32 `ESP.restart()` | OK |
| Config | Save Name | GET /setdevicename | ESP32 + PW "gm2026" | OK |
| Config | Watchdog Toggle | GET /setwatchdog | ESP32 + PW "gm2026" | OK |
| Maintenance | Calibrate Pressure | `calibrate_pressure` | ESP32 local (60 samples, EEPROM save) | NEW 10.7 |
| Contractor | Calibrate Sensor | `send_calibration_command()` | Python → ESP32 `{"type":"cmd","cmd":"cal"}` | FIXED 10.7 |

---

## Libraries Removed from Python

The following Python libraries are no longer imported or required:

| Library | Previous Purpose | Replacement |
|---------|-----------------|-------------|
| `adafruit_mcp230xx` | MCP23017 I2C GPIO expander | Serial mode commands to ESP32 |
| `adafruit_ads1x15` | ADS1115/ADS1015 ADC readings | ESP32 sends sensor data via serial |
| `board` | Raspberry Pi I2C bus setup | Not needed — no I2C from Linux |
| `busio` | I2C bus communication | Not needed — serial only |
| `digitalio` | GPIO pin direction/pull config | Not needed — ESP32 manages GPIO |

**Why removed:** These libraries required specific I2C hardware connections between the Linux device and the IO Board. With the ESP32 handling all hardware, these connections no longer exist. Removing unused imports reduces startup time and eliminates potential import errors on devices without I2C hardware.

---

## Files NOT Changed

| File | Reason |
|------|--------|
| `main.py` | Reads pressure/current via `io.get_cached_pressure()` — already patched upstream |
| `views/*.py` | All screens use app properties — no direct hardware access |
| `utils/cycle_state_manager.py` | Cycle state is local — no hardware interaction |
| `utils/profile_handler.py` | Profile management is local — no hardware interaction |

---

## Communication Flow Diagram

```
┌──────────────────┐         Serial (JSON)        ┌──────────────────┐
│   Linux / RPi    │ ◄──────────────────────────► │   ESP32 IO Board │
│                  │                               │                  │
│  Python Control  │  {"type":"data","mode":1}  →  │  setRelaysForMode │
│  Panel (Kivy)    │                               │  (Motor,CR1,CR2,  │
│                  │  ← {"pressure":-14.2,         │   CR5 outputs)   │
│  io_manager.py   │     "current":0.07,           │                  │
│  modem.py        │     "overfill":0,             │  ADS1015 ADC     │
│  alarm_manager.py│     "sdcard":"OK"}            │  Overfill GPIO38 │
│                  │     (5Hz sensor packets)      │                  │
│                  │                               │                  │
│                  │  ← {"datetime":"...",          │  WalterModem     │
│                  │     "lte":1,"rsrp":"-85",     │  (cellular)      │
│                  │     "rsrq":"-10",...}          │                  │
│                  │     (only on fresh modem data) │                  │
│                  │                               │                  │
│                  │  ← {"command":"start_cycle",  │  Web Portal      │
│                  │     "type":"run"}             │  (192.168.4.1)   │
│                  │     (from web portal)         │                  │
└──────────────────┘                               └──────────────────┘
```

**Linux → ESP32 (every 15 seconds):** Device ID, cycle count, fault codes, pressure, current. This data is used **only** for building CBOR payloads that are transmitted via cellular to the cloud server. The ESP32 uses its own real-time ADC readings for CBOR pressure/current, so cellular data is always fresh regardless of this 15-second interval.

**Linux → ESP32 (on mode change):** `{"type":"data","mode":N}` sent immediately when the relay mode changes. This is the critical relay control path.

**ESP32 → Linux (5 times per second / 200ms):** Pressure (IWC), current (amps), overfill status, SD card status, relay mode. This is the **critical path** — the Linux controller uses these values for all real-time decisions: starting and stopping run cycles, detecting alarm conditions, and triggering safety shutdowns.

**ESP32 → Linux (only on fresh modem data):** Full status including datetime, LTE connection, RSRP, RSRQ, operator, band, passthrough, profile, failsafe. Sent only when the modem library returns new data (typically every ~60 seconds for signal info, ~15 minutes for time sync). **Never repeated with stale cached values.**

**ESP32 → Linux (web portal commands):** Commands forwarded from the web portal (`start_cycle`, `stop_cycle`, `start_test`, `stop_test`, etc.). Python handles these through the normal IOManager path with full alarm monitoring and database logging.

---

## Backup Files

The backward-compatible (I2C fallback) versions are in:
```
_backup_i2c_compatible/
├── README.md                           ← Restoration instructions
├── io_manager_i2c_fallback.py          ← controllers/io_manager.py with I2C
├── modem_i2c_fallback.py               ← utils/modem.py with fallback
├── alarm_manager_i2c_fallback.py       ← utils/alarm_manager.py with I2C TLS
├── data_handler_i2c_fallback.py        ← utils/data_handler.py with patch
└── pressure_sensor_i2c_fallback.py     ← controllers/pressure_sensor.py
```

---

## Net Result

| Metric | I2C Version (Original) | Serial-Only (Updated) |
|--------|------------|-------------|
| io_manager.py lines | ~2425 | ~2219 |
| Python I2C imports | 5 libraries | 0 |
| I2C bus accesses | ~60/second (ADC) + pin writes | 0 |
| Relay control latency | <1ms (I2C direct) | <200ms (serial mode send) |
| ADC read rate | 60Hz (Python thread) | 60Hz (ESP32, sent to Linux 5x/sec) |
| Overfill detection | Single pin read (no hysteresis) | 8/5 hysteresis (more robust) |
| Web portal integration | None — buttons nonfunctional | Full: all tests, cycles, stops work |
| Mode override protection | None | ESP32 guards web tests from serial mode overrides |
| Required hardware | MCP23017 + ADS1115 on I2C | ESP32 Rev 10+ on serial |

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| Rev 10.0 | 2/8/2026 | Initial serial-only build. All I2C code removed. Relay control and sensor data via serial JSON. |
| Rev 10.1 | 2/8/2026 | Performance fix: relay response 6s → 200ms. Direct serial send from main process. Mode polling 500ms → 100ms. ESP32 serial read 5s → 100ms. Password-protected web portal. Web portal test/cycle commands connected to Python. |
| Rev 10.2 | 2/8/2026 | Fixed stale CBOR pressure. ESP32 now uses its own ADS1015 readings for CBOR, not the Python echo. Web portal tests connected. |
| Rev 10.3 | 2/9/2026 | Serial buffer drain: Python reads all buffered lines and uses only the latest (fixes stale pressure). Direct ESP32 reads for `_get_pressure()` and `_get_current()` (removes Kivy StringProperty indirection). ESP32 ADC rolling average window reduced from 3.3s to 1s. |
| Rev 10.4 | 2/9/2026 | Fixed web portal tests/cycles not starting: added `from_web=True` parameter to bypass Kivy screen guards. Full web portal button audit completed. Modem.py debug log fixed to show only received fields (not all cached values). |
| Rev 10.5 | 2/9/2026 | **ESP32 firmware fix**: Serial data mode field now ignored when a web portal test is running (`testRunning` guard). Prevents Linux periodic payload (`"mode":0`) from killing active tests. ESP32 `stop_cycle` serial command also clears test state. Diagnostic logging added to `set_sequence()` child process for leak test troubleshooting. ESP32 sensor packets now sent at 5Hz (200ms) with SD card status. Cellular/datetime data sent only on fresh modem retrieval. |
| Rev 10.6 | 2/6/2026 | **Fix "CHECK I/O BOARD CONNECTION" false alarm.** `hardware_available` changed from `False` to `True` — the ESP32 serial link IS the I/O board hardware. The old `False` value caused `main.py`'s `get_gm_status()` to show a red error banner and return early, preventing alarms (overfill, etc.) from triggering the buzzer. Also added `send_normal_command()` to `modem.py` and updated `set_shutdown_relay()` in `io_manager.py` to send `{"mode":"normal"}` when clearing a 72-hour shutdown, eliminating the need for an ESP32 reboot. |
| Rev 10.7 | 2/9/2026 | **Pressure sensor calibration (3 files changed).** `modem.py`: Added `send_calibration_command()` — sends `{"type":"cmd","cmd":"cal"}` to ESP32. Added `ps_cal` response parser — saves ESP32 calibration result to `gm_db` as `adc_zero`. `contractor_screen.py`: Fixed crash — replaced `self.app.io.pressure_sensor.calibrate` (removed in serial-only build) with `_send_calibration_to_esp32()`. Updated dialog text for altitude clarity. New `"type":"cmd"` message type. ESP32 sends `{"type":"data","ps_cal":964.50}` back after calibration. |

---

## Testing Checklist

- [ ] Boot app — verify no `import board` / `import busio` errors
- [ ] Verify pressure updates on main screen (from ESP32 serial, ~5Hz)
- [ ] Verify current/amps updates on main screen (from ESP32 serial)
- [ ] Start a run cycle from touchscreen — verify mode 1 sent to ESP32 within 200ms
- [ ] Start a run cycle from web portal — verify mode 1 sent (bypasses screen guard)
- [ ] Start a purge — verify mode 2 sent to ESP32
- [ ] Start a leak test from web portal — verify mode 9 sent, relays hold for 30 min
- [ ] Verify leak test NOT killed by periodic Linux mode payload
- [ ] Stop leak test from web portal — verify relays return to rest, serial mode control resumes
- [ ] Start functionality test from web portal — verify 10x run/purge cycle
- [ ] Start manual mode from touchscreen — verify full sequence sent
- [ ] Trigger bleed mode — verify mode 8 sent to ESP32
- [ ] Trigger overfill — verify alarm fires, buzzer sounds, status bar shows alarm (not "CHECK I/O BOARD")
- [ ] Trigger 72-hour shutdown — verify shutdown command sent to ESP32
- [ ] Clear 72-hour shutdown — verify `{"mode":"normal"}` sent to ESP32 (GPIO13 restored HIGH, no reboot needed)
- [ ] Enter passthrough mode — verify serial sends are suspended
- [ ] Calibrate pressure from web portal Maintenance screen — verify zero point updated and saved to EEPROM
- [ ] Calibrate pressure from Contractor screen button — verify no crash, command sent to ESP32
- [ ] Verify ESP32 sends `{"type":"data","ps_cal":xxx}` back to Linux after calibration
- [ ] Verify `gmctl` log shows "Saved pressure calibration to database: adc_zero=xxx"
- [ ] Reboot ESP32 — verify calibration persists (loaded from EEPROM at boot)
- [ ] Verify no I2C-related error messages in log
- [ ] Verify `gmctl` log shows only received packet fields (no repeated datetime/rsrp)
