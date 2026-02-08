# Changelog: Rev 10 Serial-Only Build

**Date:** February 8, 2026
**Build Version:** 2.0 — Serial-Only (MCP23017/ADS1115 phased out)
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
│  │ (mmap file)   │  0.5s     │ polls mode, sends      │     │
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

## File: `controllers/io_manager.py` — Major Rewrite

### Removed: I2C Hardware Imports (was lines 7-8, 27-29, 35)
- `import board`, `import busio`, `from digitalio import Direction`
- `import adafruit_ads1x15.ads1115 as ADS`
- `from adafruit_ads1x15.analog_in import AnalogIn`
- `from adafruit_mcp230xx.mcp23017 import MCP23017`
- `from .pressure_sensor import PressureSensor`

**Why:** ESP32 Rev 10 handles all hardware I/O. These libraries require the I2C bus to have an MCP23017 and ADS1115 — which no longer exist on the board.

### Removed: `MockPin` class (was lines 38-50)
### Removed: `MockADCChannel` class (was lines 53-60)

**Why:** Mock objects were needed for graceful degradation when I2C was unavailable. In the serial-only build, `_StubPin` (inline class) replaces `MockPin` for structural compatibility. `MockADCChannel` is gone entirely — no ADC channels exist in Python.

### Replaced: `__init__()` Hardware Initialization (was lines 247-274)
**Was:** Full I2C bus init → MCP23017 → ADS1115 → pin objects → PressureSensor
**Now:** `_StubPin` objects in `self.pins` dict + `hardware_available = False` constant

**Why:** No I2C bus to initialize. The `_StubPin` objects accept `.value` reads/writes silently so any code referencing `self.pins['x'].value` won't crash.

### Removed: `_init_mock_hardware()` (was lines 329-364)
**Why:** No need for mock mode when there's no hardware to mock.

### Replaced: `setup_pins()` → No-op (was lines 505-553)
**Was:** MCP23017 pin direction configuration with retry logic
**Now:** Single log line — ESP32 configures its own GPIOs

### Replaced: `set_rest()` — Simplified (was lines 569-635)
**Was:** I2C pin writes with retry loops and I2C bus reset on failure
**Now:** ModeManager update only (serial manager sends mode 0 to ESP32)

### Replaced: `set_bleed()` — Simplified (was lines 637-652)
**Was:** I2C pin writes with `_ensure_hardware_for_child_process()`
**Now:** Stub pin updates for tracking (serial manager sends mode 8 to ESP32)

### Replaced: `_ensure_hardware_for_child_process()` → No-op (was lines 714-771)
**Was:** Full I2C reinitialization after fork() — fresh bus, MCP23017, pins
**Now:** `pass` — ModeManager mmap is fork-safe, no I2C to reinitialize

### Replaced: `set_mode()` — Simplified (was lines 773-863)
**Was:** ModeManager update + I2C pin writes with retry loops + bus reset
**Now:** ModeManager update + stub pin updates (serial manager detects change, sends mode N to ESP32). Removed: `_mcp_lock.acquire()`, per-pin retry loop, `reset_i2c()` calls, `pin_delay` sleep per pin.

### Replaced: `_sensor_reading_loop()` — Serial-Only (was lines 390-452)
**Was:** `if hardware_available: read_ADC() elif: serial_fallback()`
**Now:** Always reads from `serial_manager.esp32_pressure` and `.esp32_current` — no conditional branching

### Removed: ADC Current Methods (was lines 1481-1570)
- `_collect_adc_readings()` — Collected 60 ADC samples with MCP bus priority
- `_handle_current_failure()` — Failure count tracking with cached value fallback
- `_process_current_readings()` — Outlier removal and max value extraction
- `_calculate_current_value()` — ADC-to-amps calibration mapping
- `_format_and_cache_result()` — Format and cache ADC result

**Why:** ESP32 performs all ADC sampling, filtering, and calibration at 60Hz.

### Replaced: `get_current()` → Returns Cached Serial Value (was lines 1572-1608)
**Was:** Full ADC pipeline (collect → process → calculate → format)
**Now:** `return self.get_cached_current()` (one line)

### Replaced: `reset_i2c()` → No-op (was lines 1985-2029)
**Was:** Full I2C bus tear-down and re-initialization with retry logic
**Now:** Returns `True` with a debug log — no bus to reset

### Replaced: `set_shutdown_relay()` — Serial-Only (was lines 1779-1803)
**Was:** MCP23017 pin 4 write + serial fallback
**Now:** Serial `send_shutdown_command()` only (sends `{"mode":"shutdown"}` to ESP32)

### Updated: `cleanup()` — Serial Rest Command (was pin-by-pin I2C write)
**Now:** Sends `send_mode_immediate(0)` to ESP32 to idle all relays during shutdown

---

## File: `utils/modem.py` — Comment Updates

All "REV 10 PATCH" comments updated to "SERIAL-ONLY" to reflect that serial is the **only** control path, not a fallback. No logic changes from the patch version.

---

## File: `utils/data_handler.py` — Comment Update

`get_current_mode()` comments updated from "REV 10 PATCH" to "SERIAL-ONLY". The bleed(8) and leak(9) mode mappings are unchanged.

---

## File: `utils/alarm_manager.py` — I2C Read Removed

### Replaced: `OverfillCondition.check()` — Serial-Only (was lines 683-691)
**Was:** I2C TLS pin read → serial fallback
**Now:** Serial `esp32_overfill` read ONLY. The I2C `context.app.io.pins['tls'].value` read has been removed entirely.

**Why:** With no MCP23017 on the bus, the TLS pin read would always hit a `_StubPin` returning `False`, making the I2C path useless. ESP32's GPIO38 overfill detection with 8/5 hysteresis is more robust anyway.

---

## Files NOT Changed

| File | Reason |
|------|--------|
| `main.py` | Reads pressure/current via `io.get_cached_pressure()` — already patched upstream |
| `views/*.py` | All screens use app properties — no direct hardware access |
| `utils/cycle_state_manager.py` | Cycle state is local — no hardware interaction |
| `utils/profile_handler.py` | Profile management is local — no hardware interaction |

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

| Metric | I2C Version | Serial-Only |
|--------|------------|-------------|
| io_manager.py lines | ~2425 | ~2130 |
| Python I2C imports | 5 libraries | 0 |
| I2C bus accesses | ~60/second (ADC) + pin writes | 0 |
| Relay control latency | <1ms (I2C direct) | <500ms (serial poll) |
| ADC read rate | 60Hz (Python thread) | 60Hz (ESP32, sent every 15s) |
| Overfill detection | Single pin read | 8/5 hysteresis (more robust) |
| Required hardware | MCP23017 + ADS1115 on I2C | ESP32 Rev 10+ on serial |

---

## Testing Checklist

- [ ] Boot app — verify no `import board` / `import busio` errors
- [ ] Verify pressure updates on main screen (from ESP32 serial)
- [ ] Verify current/amps updates on main screen (from ESP32 serial)
- [ ] Start a run cycle — verify mode 1 sent to ESP32 within 500ms
- [ ] Start a purge — verify mode 2 sent to ESP32
- [ ] Start a leak test (Maintenance) — verify mode 9 sent to ESP32
- [ ] Start manual mode (Maintenance) — verify full sequence sent
- [ ] Trigger bleed mode — verify mode 8 sent to ESP32
- [ ] Trigger overfill — verify alarm fires from ESP32 serial data
- [ ] Trigger 72-hour shutdown — verify shutdown command sent to ESP32
- [ ] Enter passthrough mode — verify serial sends are suspended
- [ ] Verify no I2C-related error messages in log
