# Python Control Panel — Changes Summary (Rev 10.5)

**Project:** VST GM Control Panel (Linux/Raspberry Pi)  
**Date:** February 9, 2026  
**Purpose:** Adapt the Python control software to work with the new ESP32 IO Board (Rev 10+), replacing all direct I2C hardware control with serial communication.

---

## Executive Summary

The Python control panel previously communicated with the IO Board using I2C (a physical wiring protocol that requires the Linux device to directly control individual hardware pins). The new ESP32 IO Board handles all hardware control internally and communicates with the Linux device over a simple serial connection using JSON text messages.

This update removes all I2C hardware code from the Python program and replaces it with serial message-based control. The result is a simpler, faster, and more reliable system where the ESP32 manages physical hardware and the Python program manages business logic (cycles, alarms, scheduling).

---

## What Changed and Why

### 1. Relay Control — From Direct Hardware to Serial Commands

**Before:** The Python program used the Adafruit MCP23017 library to set individual hardware pins HIGH or LOW over the I2C bus. Each mode change required 4-5 sequential pin writes, each with retry logic and error handling for bus failures.

**After:** The Python program writes a single mode number (0-9) to a memory-mapped file. The serial manager detects the change within 100ms and sends a one-line JSON message like `{"type":"data","mode":1}` to the ESP32. The ESP32 sets all relay outputs atomically. When running in the main process, mode commands are sent directly to serial (~1ms) without waiting for polling.

**Why:** The I2C bus was a frequent source of failures — noise on the wiring, bus lockups, and timing issues caused intermittent relay control problems. Serial communication is more reliable over longer distances and eliminates an entire class of field failures.

**Files changed:**
- `controllers/io_manager.py` — `set_mode()`, `set_rest()`, `set_bleed()`, `process_mode()` rewritten
- `utils/modem.py` — Added `send_mode_immediate()`, `_mode_check_cycle()`

---

### 2. Sensor Readings — From Direct ADC to Serial Data

**Before:** The Python program used the Adafruit ADS1115 library to read pressure and motor current values directly from an ADC chip over I2C. This required complex calibration code, rolling averages, and failure recovery logic in Python.

**After:** The ESP32 reads the ADC sensor at 60 times per second and sends computed pressure and current values to the Python program 5 times per second as part of its fast sensor packet. Python simply reads the latest values from `serial_manager.esp32_pressure` and `serial_manager.esp32_current`.

**Why:** Moving ADC reading to the ESP32 eliminates I2C bus contention (two devices sharing the same bus caused timing conflicts), reduces Python CPU load, and provides faster, more stable sensor readings. The ESP32's dedicated hardware timer ensures consistent 60Hz sampling that Python could not achieve.

**Files changed:**
- `controllers/io_manager.py` — Removed all ADC/ADS1115 imports and reading code (~90 lines)
- `utils/modem.py` — Added `esp32_pressure`, `esp32_current` parsing from serial data

---

### 3. Overfill Safety Sensor — From Direct GPIO to Serial Status

**Before:** The Python program read the overfill sensor by checking an MCP23017 input pin (TLS pin) via I2C.

**After:** The ESP32 monitors the overfill sensor on its own GPIO pin (with 8/5 hysteresis for noise rejection) and includes the status in every fast sensor packet (5Hz). Python reads `serial_manager.esp32_overfill` instead.

**Why:** The overfill sensor is a critical safety device. Having the ESP32 monitor it directly means it can trigger an emergency stop even if the Linux device is unresponsive. This is a safety improvement.

**Files changed:**
- `utils/alarm_manager.py` — `OverfillCondition.check()` reads from serial data only

---

### 4. Performance Optimization — Faster Relay Response

**Before (Rev 10.0):** Mode changes could take up to 6 seconds from button press to relay activation due to three compounding delays:
- Spawning a new Linux process for each mode change (200-500ms)
- Polling the mode file every 500ms (0-500ms wait)
- ESP32 checking serial input every 5 seconds (0-5000ms wait)

**After (Rev 10.1+):** Mode changes complete in under 200 milliseconds:
- Mode function called directly — no process spawning (saves 200-500ms)
- Mode polling reduced to every 100ms (saves up to 400ms)
- ESP32 serial read reduced to every 100ms (saves up to 4900ms)
- Main process sends relay commands directly to serial port (bypasses polling entirely)

**Why:** Field technicians reported the system felt unresponsive. A 6-second delay between pressing a button and seeing relays activate erodes operator confidence. Sub-200ms response makes the system feel instant.

**Files changed:**
- `controllers/io_manager.py` — `process_mode()` direct call, `set_mode()` direct serial send
- `utils/modem.py` — Polling interval 500ms → 100ms

---

### 5. Web Portal Integration — Test Commands and Cycle Control

**Before:** The ESP32 web portal's buttons had no connection to the Python control logic. Pressing "Start Cycle" on the web portal would start a basic failsafe cycle on the ESP32, which Python would immediately override — causing a 1-2 second run then stop. Test buttons (Leak, Functionality, Efficiency) did nothing useful.

**After:** When the Linux device is connected, the ESP32 forwards all web portal commands to Python via serial. Python then manages the full cycle with proper alarm monitoring, database logging, and step timing. All test and cycle commands now work from the web portal.

**Why:** The Python program has the complete business logic — alarm thresholds, cycle counting, fault codes, profile-specific behavior. Running cycles through Python ensures consistent behavior whether triggered from the touchscreen or the web portal.

**Kivy Screen Guard Fix (Rev 10.4):** The original Python functions had safety checks that blocked execution if the touchscreen wasn't on the correct screen. This silently blocked all web portal commands. Added `from_web=True` parameter to bypass these guards for web-originated commands.

**Web Portal Test Mode Guard (Rev 10.5):** When a test is running from the web portal, the ESP32 now ignores mode changes from Linux serial data. This prevents the periodic `"mode":0` payload from killing active tests.

**Files changed:**
- `utils/modem.py` — Added handlers for `start_cycle`, `stop_cycle`, `start_test` commands, all with `from_web=True`
- `controllers/io_manager.py` — Added `from_web=False` parameter to `leak_test()`, `functionality_test()`, `efficiency_test_fill_run()`, `canister_clean()`, `run_cycle()`

---

### 6. Serial Data Freshness — No Stale Data

**Before (Rev 10.0-10.2):** Python read the oldest message in the serial buffer, which could be seconds old. Cellular/datetime data was repeated every packet, flooding the log with stale values.

**After (Rev 10.3+):** Python drains the entire serial buffer and uses only the latest message. The ESP32 sends two types of packets:
1. **Fast sensor packets (5Hz):** pressure, current, overfill, SD card, relay mode
2. **Fresh cellular packets (only when modem returns new data):** datetime, LTE status, RSRP, RSRQ, operator, band, passthrough, profile, failsafe

The Python debug log now shows only the fields actually received in each packet, not all cached values.

**Files changed:**
- `utils/modem.py` — Buffer drain loop, field-specific logging

---

### 7. Libraries Removed

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

## Files Modified (Complete List)

| File | Changes |
|------|---------|
| `controllers/io_manager.py` | Removed all I2C/MCP23017/ADS1115 code (~300 lines). Relay control via serial. Direct serial send for faster response. Process spawning eliminated. Added `from_web` parameter to 5 test/cycle functions. Diagnostic logging in child process. |
| `utils/modem.py` | Added full bidirectional ESP32 communication: status parsing (pressure, current, overfill, profile, failsafe, cellular), mode polling (100ms) and immediate send, serial buffer drain, web portal command handlers (start_cycle, stop_cycle, start_test), PPP passthrough management, field-specific debug logging. |
| `utils/alarm_manager.py` | Overfill detection switched from I2C pin read to serial data only. |
| `utils/data_handler.py` | Mode mapping updated with bleed (8) and leak (9) modes for ESP32 relay control. |

---

## Communication Flow Diagram

```
┌──────────────────┐         Serial (JSON)        ┌──────────────────┐
│   Linux / RPi    │ ◄──────────────────────────► │   ESP32 IO Board │
│                  │                               │                  │
│  Python Control  │  {"type":"data","mode":1}  →  │  setRelaysForMode │
│  Panel (Kivy)    │  (on mode change, ~1ms)       │  (Motor,CR1,CR2,  │
│                  │                               │   CR5 outputs)   │
│  io_manager.py   │  ← {"pressure":-14.2,         │                  │
│  modem.py        │     "current":0.07,           │  ADS1015 ADC     │
│  alarm_manager.py│     "overfill":0,             │  Overfill GPIO38 │
│                  │     "sdcard":"OK"}            │                  │
│                  │     (5Hz sensor packets)      │  Web Portal      │
│                  │                               │  (192.168.4.1)   │
│                  │  ← {"command":"start_cycle",  │                  │
│                  │     "type":"run"}             │  WalterModem     │
│                  │     (from web portal)         │  (cellular)      │
└──────────────────┘                               └──────────────────┘
```

**Linux → ESP32 (every 15 seconds):** Device ID, cycle count, fault codes, pressure, current. Used **only** for CBOR payload building (cellular transmission to cloud). ESP32 uses its own ADC readings for CBOR, so these values are supplementary.

**Linux → ESP32 (on mode change):** Immediate relay command. This is the critical control path.

**ESP32 → Linux (5x per second):** Real-time sensor data. Python uses these for all decisions.

**ESP32 → Linux (fresh modem data only):** Cellular status. Sent only when new, never repeated.

**ESP32 → Linux (web portal):** Forwarded user commands from the web interface.

---

## How the System Decides When to Operate

The Linux device (Raspberry Pi) is the brain of the system. It receives real-time pressure and current readings from the ESP32 5 times per second. Based on those readings, it decides:

1. **When to start a run cycle** — Pressure rises above the configured threshold
2. **When to stop a run cycle** — Pressure drops below the stop point or timer expires
3. **When to trigger alarms** — Pressure stuck at zero, motor current too high, overfill detected
4. **When to perform a purge** — After a configured number of run cycles
5. **When to enter bleed mode** — Pressure needs to be relieved

The ESP32 does NOT make these decisions during normal operation. It simply reports sensor data and executes relay commands. The only time the ESP32 takes control is in "failsafe mode" — when the Linux device has been unresponsive for an extended period.

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| Rev 10.0 | 2/8/2026 | Initial serial-only build. I2C removed, serial relay control. |
| Rev 10.1 | 2/8/2026 | Performance fix (6s → 200ms relay response). Password-protected web portal. Web portal test commands connected to Python. |
| Rev 10.2 | 2/8/2026 | Fixed stale CBOR pressure (ESP32 now uses own ADC, not Python echo). Web portal tests connected. |
| Rev 10.3 | 2/9/2026 | Faster pressure updates. Serial buffer drain for freshest data. Direct ESP32 pressure/current reads for CBOR payload. |
| Rev 10.4 | 2/9/2026 | Fixed web portal tests/cycles not starting. Screen guards bypass for web portal commands. Full web portal button audit. Modem.py debug log shows only received fields. |
| Rev 10.5 | 2/9/2026 | ESP32 ignores serial mode overrides during web portal tests. 5Hz sensor packets. Fresh-only cellular data. Child process diagnostic logging. |
