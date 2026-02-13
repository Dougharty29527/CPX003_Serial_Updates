# Backup: I2C-Compatible (Fallback) Version

**Date:** February 8, 2026
**Purpose:** These files are the "backward compatible" patch version that includes
BOTH the original I2C/MCP23017 code AND serial fallback paths.

## When to use these files

Restore these files ONLY if you need to run the Python control panel on the
**original IO board** that has the MCP23017 I2C port expander physically on the
I2C bus (not the ESP32 Rev 10+ board).

## How they work

- If the MCP23017 is detected on the I2C bus → original I2C pin control is used
- If the MCP23017 is NOT detected → mock mode activates, serial paths take over
- Both paths coexist — no code was removed from the original

## File mapping

| Backup File | Restore To |
|------------|------------|
| `io_manager_i2c_fallback.py` | `controllers/io_manager.py` |
| `modem_i2c_fallback.py` | `utils/modem.py` |
| `alarm_manager_i2c_fallback.py` | `utils/alarm_manager.py` |
| `data_handler_i2c_fallback.py` | `utils/data_handler.py` |
| `pressure_sensor_i2c_fallback.py` | `controllers/pressure_sensor.py` |

## How to restore

```bash
cp io_manager_i2c_fallback.py ../controllers/io_manager.py
cp modem_i2c_fallback.py ../utils/modem.py
cp alarm_manager_i2c_fallback.py ../utils/alarm_manager.py
cp data_handler_i2c_fallback.py ../utils/data_handler.py
cp pressure_sensor_i2c_fallback.py ../controllers/pressure_sensor.py
```

## What the production (serial-only) version changes

The production files in the parent directories have ALL I2C/MCP23017/ADS1115
code removed. They communicate with the ESP32 IO Board (Rev 10+) exclusively
via serial JSON messages. The ESP32 handles all hardware I/O directly.
