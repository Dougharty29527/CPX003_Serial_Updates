# Python Control Panel — Changes Summary (Rev 10.1)

**Project:** VST GM Control Panel (Linux/Raspberry Pi)  
**Date:** February 8, 2026  
**Purpose:** Adapt the Python control software to work with the new ESP32 IO Board (Rev 10+), replacing all direct I2C hardware control with serial communication.

---

## Executive Summary

The Python control panel previously communicated with the IO Board using I2C (a physical wiring protocol that requires the Linux device to directly control individual hardware pins). The new ESP32 IO Board handles all hardware control internally and communicates with the Linux device over a simple serial connection using JSON text messages.

This update removes all I2C hardware code from the Python program and replaces it with serial message-based control. The result is a simpler, faster, and more reliable system where the ESP32 manages physical hardware and the Python program manages business logic (cycles, alarms, scheduling).

---

## What Changed and Why

### 1. Relay Control — From Direct Hardware to Serial Commands

**Before:** The Python program used the Adafruit MCP23017 library to set individual hardware pins HIGH or LOW over the I2C bus. Each mode change required 4-5 sequential pin writes, each with retry logic and error handling for bus failures.

**After:** The Python program writes a single mode number (0-9) to a memory-mapped file. The serial manager detects the change and sends a one-line JSON message like `{"type":"data","mode":1}` to the ESP32. The ESP32 sets all relay outputs atomically.

**Why:** The I2C bus was a frequent source of failures — noise on the wiring, bus lockups, and timing issues caused intermittent relay control problems. Serial communication is more reliable over longer distances and eliminates an entire class of field failures.

**Files changed:**
- `controllers/io_manager.py` — `set_mode()`, `set_rest()`, `set_bleed()` rewritten
- `utils/modem.py` — Added `send_mode_immediate()`, `_mode_check_cycle()`

---

### 2. Sensor Readings — From Direct ADC to Serial Data

**Before:** The Python program used the Adafruit ADS1115 library to read pressure and motor current values directly from an ADC chip over I2C. This required complex calibration code, rolling averages, and failure recovery logic in Python.

**After:** The ESP32 reads the ADC sensor at 60 times per second and sends computed pressure and current values to the Python program every 1 second as part of its status update. Python simply reads the latest values from `serial_manager.esp32_pressure` and `serial_manager.esp32_current`.

**Why:** Moving ADC reading to the ESP32 eliminates I2C bus contention (two devices sharing the same bus caused timing conflicts), reduces Python CPU load, and provides faster, more stable sensor readings. The ESP32's dedicated hardware timer ensures consistent 60Hz sampling that Python could not achieve.

**Files changed:**
- `controllers/io_manager.py` — Removed all ADC/ADS1115 imports and reading code
- `utils/modem.py` — Added `esp32_pressure`, `esp32_current` parsing from serial data

---

### 3. Overfill Safety Sensor — From Direct GPIO to Serial Status

**Before:** The Python program read the overfill sensor by checking an MCP23017 input pin (TLS pin) via I2C.

**After:** The ESP32 monitors the overfill sensor on its own GPIO pin and includes the status in every serial update. Python reads `serial_manager.esp32_overfill` instead.

**Why:** The overfill sensor is a critical safety device. Having the ESP32 monitor it directly means it can trigger an emergency stop even if the Linux device is unresponsive. This is a safety improvement.

**Files changed:**
- `utils/alarm_manager.py` — `OverfillCondition.check()` reads from serial data

---

### 4. Performance Optimization — Faster Relay Response

**Before (Rev 10.0):** Mode changes could take up to 6 seconds from button press to relay activation due to three compounding delays:
- Spawning a new Linux process for each mode change (200-500ms)
- Polling the mode file every 500ms (0-500ms wait)
- ESP32 checking serial input every 5 seconds (0-5000ms wait)

**After (Rev 10.1):** Mode changes complete in under 200 milliseconds:
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

**Before:** The ESP32 web portal's "Start Cycle" and test buttons had no connection to the Python control logic. Pressing "Start Cycle" on the web portal would start a basic failsafe cycle on the ESP32, which Python would immediately override — causing a 1-2 second run then stop.

**After:** When the Linux device is connected, the ESP32 forwards all web portal commands to Python via serial. Python then manages the full cycle with proper alarm monitoring, database logging, and step timing. Test commands (Leak Test, Functionality Test, Efficiency Test) are now also forwarded and handled.

**Why:** The Python program has the complete business logic — alarm thresholds, cycle counting, fault codes, profile-specific behavior. Running cycles through Python ensures consistent behavior whether triggered from the touchscreen or the web portal.

**Files changed:**
- `utils/modem.py` — Added handlers for `start_cycle`, `stop_cycle`, and `start_test` commands received from ESP32

---

### 6. Libraries Removed

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
| `controllers/io_manager.py` | Removed all I2C/MCP23017/ADS1115 code. Relay control via serial. Direct serial send for faster response. Process spawning eliminated. |
| `utils/modem.py` | Added ESP32 status parsing (pressure, current, overfill, profile, failsafe). Added mode polling and immediate send. Added web portal command handlers (start_cycle, stop_cycle, start_test). |
| `utils/alarm_manager.py` | Overfill detection switched from I2C pin read to serial data. |
| `utils/data_handler.py` | Mode mapping updated with bleed (8) and leak (9) modes. |

---

## Backup Location

The previous I2C-compatible version of all modified files is preserved in:
```
vst_gm_control_panel/_backup_i2c_compatible/
```
With a README explaining how to restore if needed.

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
│  modem.py        │     "overfill":0}             │  ADS1015 ADC     │
│  alarm_manager.py│                               │  Overfill GPIO38 │
│                  │  ← {"command":"start_cycle",  │                  │
│                  │     "type":"run"}             │  Web Portal      │
│                  │     (from web portal)         │  (192.168.4.1)   │
└──────────────────┘                               └──────────────────┘
```

**Linux → ESP32:** Mode commands, device info, cycle count, fault codes  
**ESP32 → Linux:** Sensor data (1s), full status (15s), web portal commands  

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| Rev 10.0 | 2/8/2026 | Initial serial-only build. I2C removed, serial relay control. |
| Rev 10.1 | 2/8/2026 | Performance fix (6s → 200ms relay response). Password-protected web portal. Web portal test commands connected to Python. |
