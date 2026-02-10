# VST Green Machine Control Panel - Full Analysis

## 1. Application Overview

The VST Green Machine Control Panel is an industrial control system for **vapor recovery equipment at gas stations**. It runs on a Raspberry Pi with a Kivy/KivyMD touchscreen UI and controls hardware via I2C (MCP23017 GPIO expander, ADS1115 ADC, pressure sensors, relays, and a motor).

**Key capabilities:**
- Multi-profile support: CS2, CS8, CS9, CS12 (different equipment configurations)
- Alarm management with 72-hour shutdown protocols
- Hardware I/O via I2C: pressure sensors, relays, motor control
- Multi-language support (English/Spanish)
- User access control with 5 permission levels
- OOBE (Out-of-Box Experience) for initial setup
- Real-time monitoring and automated cycle management
- Data logging to USB/local CSV and serial telemetry via ESP32

---

## 2. Architecture

```
ControlPanel (MDApp) - main.py
    |
    +-- IOManager (controllers/io_manager.py)
    |       |-- ModeManager (mmap-based mode state)
    |       |-- MCP23017 (I2C GPIO expander - relays/pins)
    |       |-- ADS1115 (I2C ADC - current sensing)
    |       |-- PressureSensor (controllers/pressure_sensor.py)
    |       |-- pigpio (buzzer PWM)
    |       +-- CycleStateManager (utils/cycle_state_manager.py)
    |
    +-- AlarmManager (utils/alarm_manager.py)
    |       |-- AlarmRepository (persistence layer)
    |       +-- Alarm instances (strategy pattern via AlarmCondition)
    |
    +-- ProfileHandler (utils/profile_handler.py)
    +-- DatabaseManager (utils/database_manager.py) - SQLite
    +-- DataHandler (utils/data_handler.py) - CSV logging
    +-- LanguageHandler (utils/language_handler.py)
    +-- SerialManager (utils/modem.py) - ESP32 telemetry
    +-- Views (views/*.py) - 30+ Kivy screens
```

---

## 3. Key Variables: Where They Live and How They're Updated

### 3.1 Mode (`mode`)

| Location | Variable | Type | Description |
|---|---|---|---|
| `IOManager` | `self.mode` | `str` | In-memory mode: `'rest'`, `'run'`, `'purge'`, `'burp'`, `'bleed'`, `'leak'` |
| `ModeManager` | mmap file `/tmp/vst_mode.bin` | `int` (0-5) | Process-safe persistent mode via memory-mapped file |
| `ControlPanel` | `current_mode` | `StringProperty` | UI-bound mode string |
| Database | `gm.mode_fallback` | `TEXT` | SQLite fallback when mmap fails |

**Flow:**
1. `IOManager.set_mode(mode)` sets `self.mode` and calls `self.mode_manager.set_mode(mode)` which writes to mmap
2. `IOManager.set_rest()` sets all cycle pins to False and writes `'rest'` to mmap
3. `ControlPanel.get_current_mode()` reads from `io.mode_manager.get_mode()` and updates `current_mode` StringProperty
4. `DataHandler.get_current_mode()` reads from `app.io.mode_manager.get_mode()` for CSV logging
5. Mode is also read by `IOManager.get_values()` for relay status display

**Mode-to-Pin Mapping** (defined in `IOManager.set_mode()`):
| Mode | motor | v1 | v2 | v5 |
|------|-------|-----|-----|-----|
| rest | False | False | False | False |
| run | True | True | False | True |
| purge | True | False | True | False |
| burp | False | False | False | True |
| bleed | False | False | True | True |
| leak | False | True | True | True |

### 3.2 Fault / Alarm State

| Location | Variable | Type | Description |
|---|---|---|---|
| `ControlPanel` | `alarm` | `BooleanProperty` | True when any alarm is active |
| `ControlPanel` | `alarm_list` | `ListProperty` | List of active alarm names |
| `ControlPanel` | `active_alarms` | `StringProperty` | Display text for active alarms |
| `ControlPanel` | `pressure_sensor_alarm` | `BooleanProperty` | Pressure sensor alarm flag |
| `ControlPanel` | `shutdown` | `BooleanProperty` | True when in 72-hour shutdown |
| `AlarmManager` | `active_alarms` | `Set[str]` | Set of currently active alarm names |
| `AlarmManager` | `_cached_72_hour_state` | `bool` | Cached 72-hour shutdown condition |
| `AlarmRepository` | DB `alarms` table | SQLite | Persistent alarm start times and failure counts |
| `AlarmRepository` | DB `gm` table | SQLite | Persistent alarm flags (e.g., `vac_pump_alarm`) |
| `IOManager` | `gm_fault_count` | `int` | In-memory GM fault counter (CS9 only) |
| `IOManager` | `high_current_detected` | `bool` | High current state flag |
| `IOManager` | `low_current_detected` | `bool` | Low current state flag |

**Flow:**
1. `AlarmManager.check_alarms()` runs every 1 second (via thread), iterates all `Alarm` objects calling `alarm.update()`
2. Each `Alarm.update()` calls its `AlarmCondition.check()` strategy to test the condition
3. If condition met for `alarm.duration` seconds, alarm triggers (`time_triggered` set)
4. `AlarmManager.active_alarms` set is updated
5. `ControlPanel.check_alarms()` runs every 3 seconds (Kivy Clock), reads from `AlarmManager` and updates UI properties
6. GM fault monitoring: `IOManager.check_gm_fault()` runs every 2 seconds via Kivy Clock (CS9 only)
7. 72-hour checker: `AlarmManager.check_72_hour_conditions()` runs every 5 minutes via Kivy Clock

**Alarm Types by Profile:**
| Profile | Alarms |
|---------|--------|
| CS2 | Pressure Sensor, Vac Pump, Overfill, Digital Storage |
| CS8 | All of CS2 + Under/Over/Zero/Variable Pressure + 72-Hour Shutdown |
| CS9 | CS2 + GM Fault + 72-Hour Shutdown |
| CS12 | CS2 + 72-Hour Shutdown |

### 3.3 Cycles (`run_cycle`, `current_run_cycle_count`)

| Location | Variable | Type | Description |
|---|---|---|---|
| `ControlPanel` | `run_cycle` | `BooleanProperty` | True when a run cycle is active |
| `ControlPanel` | `current_run_cycle_count` | `StringProperty` | Total cycle count from DB |
| `ControlPanel` | `manual_mode` | `BooleanProperty` | True when in manual mode |
| `ControlPanel` | `test_cycle` | `BooleanProperty` | True when test cycle is running |
| `ControlPanel` | `test_cycle_counter` | `NumericProperty` | Counter for test cycles |
| `IOManager` | `cycle_process` | `multiprocessing.Process` | The running cycle process |
| `IOManager` | `mode_process` | `multiprocessing.Process` | The running mode process |
| `IOManager` | `manual_cycle_count` | `int` | Manual mode cycle counter |
| Database | `gm.run_cycle_count` | `TEXT` | Persistent cycle count |
| Database | `gm.last_run_cycle` | `TEXT` | ISO timestamp of last run cycle |

**Flow:**
1. `ControlPanel.get_pressure()` (every 1s) checks if pressure > threshold -> calls `start_run_cycle()`
2. `start_run_cycle()` calls `io.run_cycle()` which builds a sequence and calls `process_sequence()`
3. `process_sequence()` spawns a **child process** (`multiprocessing.Process`) targeting `set_sequence()`
4. `set_sequence()` iterates (mode, delay) tuples, calling `process_mode()` for each step
5. `process_mode()` spawns **another child process** targeting `set_mode()` to set physical pins
6. Cycle count is incremented in `run_cycle()` and persisted to `gm.run_cycle_count` in DB

**Standard Run Cycle Sequence:**
```
run(120s) -> rest(2s) -> [purge(50s) -> burp(5s)] x6 -> rest(15s)
```

### 3.4 Pressure

| Location | Variable | Type | Description |
|---|---|---|---|
| `ControlPanel` | `current_pressure` | `StringProperty` | Formatted pressure (e.g., `"1.50 IWC"`) |
| `IOManager` | `_cached_pressure` | `str` | Background-thread cached pressure |
| `PressureSensor` | `pressure_readings` | `deque(maxlen=60)` | Rolling window of raw pressure values |
| `PressureSensor` | `adc_zero` | `float` | ADC zero calibration value |
| `PressureSensor` | `sensor_dc_value` | `float` | Error value (-99.9) |
| Database | `gm.adc_zero` | `TEXT` | Persistent calibration value |

**Flow:**
1. `IOManager._sensor_reading_loop()` runs in a **background daemon thread**, reads every ~0.2s
2. Calls `PressureSensor.get_pressure()` which collects 30 ADC samples via `_collect_pressure_samples()`
3. Each sample: `PressureSensor._read_adc_value()` -> `AnalogIn(adc, ADS.P0).value` -> `_convert_adc_to_pressure()`
4. Samples averaged with trimmed mean (removes min/max)
5. Result cached in `IOManager._cached_pressure`
6. `ControlPanel.get_pressure()` (every 1s, Kivy Clock) reads cached value and updates UI
7. Pressure value `-99.9` indicates sensor disconnected / hardware not available

**ADC Calibration Formula:**
```
slope (m) = (26496.0 - 4080.0) / (30.0 - (-31.35)) ≈ 365.44
pressure = (adc_value - adc_zero) / m
```

### 3.5 Current (Motor Amps)

| Location | Variable | Type | Description |
|---|---|---|---|
| `ControlPanel` | `current_amps` | `StringProperty` | Formatted current (e.g., `"3.50 A"`) |
| `IOManager` | `_cached_current` | `str` | Background-thread cached current |
| `IOManager` | `current_readings` | `deque(maxlen=60)` | Rolling window of ADC difference values |
| `IOManager` | `last_current_value` | `str` | Last good current value for failover |
| `IOManager` | `current_failure_count` | `int` | Consecutive read failures |
| `IOManager` | `_simulated_motor_current` | class var | For testing without hardware |

**Flow:**
1. `IOManager._sensor_reading_loop()` (same background thread as pressure) calls `get_current()`
2. `get_current()` calls `_collect_adc_readings()` - reads 60 samples from channels P2 and P3
3. Each sample: `difference = abs(channel2.value - channel3.value)`
4. Readings processed with outlier removal (`_process_current_readings()`)
5. Maximum value mapped to amps: `map_value(max_reading, 1248.0, 4640.0, 2.1, 8.0)`
6. Result cached in `IOManager._cached_current`
7. `ControlPanel.get_amps()` (every 1s, Kivy Clock) reads cached value and updates UI
8. GM fault check uses cached current: `>= 20.0A` = high current fault (CS9 only)

---

## 4. Adafruit Library Usage: `pin_mode()` and `get_pin()`

### 4.1 Libraries Used

| Library | Import | Purpose |
|---|---|---|
| `adafruit_mcp230xx.mcp23017.MCP23017` | `io_manager.py:29` | 16-channel I2C GPIO expander for relays/inputs |
| `adafruit_ads1x15.ads1115.ADS1115` | `io_manager.py:27` | 16-bit I2C ADC for current sensing |
| `adafruit_ads1x15.analog_in.AnalogIn` | `io_manager.py:28` | ADC channel abstraction |
| `board` | `io_manager.py:7`, `main.py:30` | Board pin definitions (SCL, SDA) |
| `busio` | `io_manager.py:8`, `main.py:31` | I2C bus interface |
| `digitalio.Direction` | `io_manager.py:11` | Pin direction constants (INPUT/OUTPUT) |

### 4.2 I2C Bus Initialization

**Location: `IOManager.__init__()` (io_manager.py:249-254)**
```python
self.i2c = busio.I2C(board.SCL, board.SDA)
self._adc = ADS.ADS1115(self.i2c)
self._mcp = MCP23017(self.i2c)
```
- Single I2C bus shared between MCP23017 and ADS1115
- Bus contention managed via `self._mcp_lock` (threading.Lock)

### 4.3 `get_pin()` Calls

**All `_mcp.get_pin()` calls occur in these locations:**

#### Location 1: `IOManager.__init__()` (io_manager.py:263-271)
```python
self.pins = {
    'motor':       self._mcp.get_pin(0),   # Output - motor relay
    'v1':          self._mcp.get_pin(1),   # Output - valve 1
    'v2':          self._mcp.get_pin(2),   # Output - valve 2
    'v5':          self._mcp.get_pin(3),   # Output - valve 5
    'shutdown':    self._mcp.get_pin(4),   # Output - shutdown relay
    'tls':         self._mcp.get_pin(8),   # Input  - tank level switch
    'panel_power': self._mcp.get_pin(10),  # Input  - panel power detect
}
```

#### Location 2: `IOManager._ensure_hardware_for_child_process()` (io_manager.py:703-711)
Same pin mapping, duplicated for child process I2C reinitialization after `fork()`.

#### Location 3: `IOManager.reset_i2c()` (io_manager.py:1946-1955)
Reinitializes all I2C devices including MCP23017, but **does NOT reassign pins** - instead calls `self.setup_pins()` which reconfigures existing pin references.

### 4.4 Pin Direction Configuration (`pin_mode` equivalent)

Adafruit's MCP23017 library uses `pin.direction = Direction.OUTPUT/INPUT` instead of a `pin_mode()` function.

**Location: `IOManager.setup_pins()` (io_manager.py:476-524)**
```python
# Output pins (relays)
for pin in ['motor', 'v1', 'v2', 'v5', 'shutdown']:
    self.pins[pin].direction = Direction.OUTPUT

# Input pins (sensors)
for pin in ['tls', 'panel_power']:
    self.pins[pin].direction = Direction.INPUT
```
- Includes retry logic (3 attempts per pin)
- Uses `_mcp_lock` for thread-safe I2C access
- Falls back to `reset_i2c()` if configuration fails

**Location: `IOManager._ensure_hardware_for_child_process()` (io_manager.py:714-734)**
```python
# Output pins for cycle control
for pin in ['motor', 'v1', 'v2', 'v5']:
    self.pins[pin].direction = Direction.OUTPUT

# Shutdown pin - preserves existing state from chip register
self.pins['shutdown'].direction = Direction.OUTPUT
self.pins['shutdown'].value = shutdown_was_on  # Read from OLAT register

# Input pins
for pin in ['tls', 'panel_power']:
    self.pins[pin].direction = Direction.INPUT
```

### 4.5 Pin Value Read/Write

**Writing (relay control):**
- `IOManager.set_mode()` (io_manager.py:798-829): Sets pin values per mode mapping with lock, retry, and verify
- `IOManager.set_rest()` (io_manager.py:569-606): Sets motor/v1/v2/v5 to False with retry
- `IOManager.set_bleed()` (io_manager.py:608-623): Direct pin writes without lock
- `IOManager.set_shutdown_relay()` (io_manager.py:1779-1803): Manages shutdown pin with profile awareness
- `IOManager.cleanup()` (io_manager.py:2335-2339): Sets cycle pins to False on exit

**Reading:**
- `IOManager.set_mode()` verifies writes: `actual_value = self.pins[pin].value` (io_manager.py:810)
- `IOManager._ensure_hardware_for_child_process()` reads GPIO register: `self._mcp.gpio` (io_manager.py:722)
- `OverfillCondition.check()` reads TLS: `context.app.io.pins['tls'].value` (alarm_manager.py:685)

### 4.6 ADC Channel Access

**Location: `IOManager.__init__()` (io_manager.py:253-254)**
```python
self._channel2 = AnalogIn(self._adc, ADS.P2)  # Motor current sense +
self._channel3 = AnalogIn(self._adc, ADS.P3)  # Motor current sense -
```

**Location: `PressureSensor.__init__()` (pressure_sensor.py:30)**
```python
self._channel = AnalogIn(self._adc, ADS.P0)   # Pressure sensor
```

**Reading values:**
- `IOManager._collect_adc_readings()`: `self._channel2.value`, `self._channel3.value` (io_manager.py:1626-1627)
- `PressureSensor._read_adc_value()`: `self._channel.value` (pressure_sensor.py:83)
- `PressureSensor.calibrate()`: `self._channel.value` (pressure_sensor.py:201)

---

## 5. Issues and Concerns with Current Adafruit Library Usage

### 5.1 Duplicated Pin Initialization (3 locations)
The pin mapping `{'motor': get_pin(0), 'v1': get_pin(1), ...}` is defined identically in:
1. `IOManager.__init__()` (line 263)
2. `IOManager._ensure_hardware_for_child_process()` (line 703)
3. Implicitly in `reset_i2c()` via `setup_pins()` (line 1972)

Any change to pin assignments must be updated in all three places.

### 5.2 I2C Bus Contention
- Single I2C bus shared between MCP23017 (GPIO) and ADS1115 (ADC)
- `_mcp_lock` only protects MCP operations, but ADC reads on the **same bus** have no lock
- `_collect_adc_readings()` checks `_mcp_lock.locked()` to abort if MCP needs the bus, but this is a race condition (check-then-act)
- Pressure sensor checks `_mcp_lock.locked()` via `_check_mcp_engaged()` - same race condition

### 5.3 Multiprocessing with I2C
- `process_mode()` spawns child processes that call `set_mode()` which writes to I2C
- `process_sequence()` spawns child processes that call `set_sequence()`
- I2C file descriptors don't survive `fork()`, requiring reinitialization in `_ensure_hardware_for_child_process()`
- This pattern creates **multiple processes accessing the same I2C bus** without inter-process locking
- `_mcp_lock` is a `threading.Lock`, not a multiprocessing lock - it does NOT protect across processes

### 5.4 Inconsistent Error Handling
- `set_mode()` has comprehensive retry/verify logic with lock (io_manager.py:798-834)
- `set_bleed()` does direct pin writes with no lock, no retry, bare `except: pass` (io_manager.py:608-623)
- `set_rest()` has retry logic but different lock strategy than `set_mode()`
- Some methods use `_mcp_lock.acquire()` manually, others don't lock at all

### 5.5 ADC Channel Initialization
- Channels are created during `__init__` and held as instance attributes
- `reset_i2c()` recreates ADC channels (io_manager.py:1949-1950) but `_ensure_hardware_for_child_process()` does NOT recreate ADC channels
- PressureSensor creates its own `AnalogIn` in its `__init__` but this channel becomes invalid after `reset_i2c()`
- `reset_i2c()` reinitializes `PressureSensor` but passes `self.app` instead of `mock_mode` (io_manager.py:1954) - potential bug

### 5.6 Mock Mode Inconsistencies
- `MockPin` and `MockADCChannel` are basic stubs that always succeed
- `PressureSensor` has its own `mock_mode` flag
- `IOManager.hardware_available` flag but not consistently checked everywhere
- `get_current()` checks `hardware_available`, but `set_mode()` does not

---

## 6. Redesign Plan for Adafruit Library Usage

### 6.1 Goals
1. **Single source of truth** for pin definitions and hardware configuration
2. **Proper I2C bus arbitration** across threads AND processes
3. **Clean hardware abstraction layer** separating business logic from Adafruit-specific code
4. **Eliminate multiprocessing for I2C access** - use threading instead
5. **Consistent error handling and recovery**

### 6.2 Proposed Architecture

```
HardwareAbstractionLayer (NEW)
    |
    +-- I2CBusManager (NEW) - single owner of busio.I2C
    |       |-- Provides thread-safe access via context manager
    |       +-- Handles bus reset/recovery
    |
    +-- PinController (NEW) - wraps MCP23017
    |       |-- PIN_MAP: single source of truth for pin assignments
    |       |-- set_output(pin_name, value) - thread-safe write with retry
    |       |-- read_input(pin_name) - thread-safe read
    |       |-- configure_all() - setup all pin directions
    |       +-- MockPinController for testing
    |
    +-- ADCController (NEW) - wraps ADS1115
    |       |-- CHANNEL_MAP: single source for channel assignments
    |       |-- read_channel(channel_name) - thread-safe read
    |       |-- read_differential(ch_pos, ch_neg) - for current sensing
    |       +-- MockADCController for testing
    |
    +-- PressureSensor (REFACTORED) - uses ADCController
    +-- CurrentSensor (NEW) - extracts current logic from IOManager
```

### 6.3 Step-by-Step Implementation Plan

#### Phase 1: Create Hardware Abstraction Layer

**Step 1: Create `controllers/hardware.py`**
- Define `PIN_MAP` constant dict with all pin assignments (single source of truth)
- Define `CHANNEL_MAP` constant dict with all ADC channel assignments
- Create `I2CBusManager` class:
  - Owns the single `busio.I2C` instance
  - Provides `threading.RLock`-based context manager for all bus access
  - Handles bus init, deinit, and reset
  - Singleton pattern (one bus per application)

**Step 2: Create `PinController` class in `controllers/hardware.py`**
- Takes `I2CBusManager` reference
- Creates MCP23017 instance
- Provides methods: `setup_pins()`, `set_output(name, value)`, `read_input(name)`, `get_mode_pins(mode_name)`
- All methods acquire I2C bus lock internally
- Built-in retry logic (configurable attempts)
- Verify-after-write on all output operations

**Step 3: Create `ADCController` class in `controllers/hardware.py`**
- Takes `I2CBusManager` reference
- Creates ADS1115 instance and AnalogIn channels
- Provides methods: `read_pressure_raw()`, `read_current_differential()`
- All methods acquire I2C bus lock internally
- Handles channel recreation after bus reset

**Step 4: Create `MockHardware` implementations**
- `MockI2CBusManager`, `MockPinController`, `MockADCController`
- Factory function: `create_hardware(mock=False)` returns real or mock implementations

#### Phase 2: Refactor Existing Code

**Step 5: Refactor `PressureSensor`**
- Remove direct `AnalogIn` access
- Accept `ADCController` instead of raw `adc`
- Call `adc_controller.read_pressure_raw()` instead of `self._channel.value`
- Remove `_check_mcp_engaged()` - bus arbitration handled by `I2CBusManager`
- Remove `mock_mode` flag - handled by `MockADCController`

**Step 6: Extract `CurrentSensor` from `IOManager`**
- Move `_collect_adc_readings()`, `_process_current_readings()`, `_calculate_current_value()`, `_handle_current_failure()` into new `CurrentSensor` class
- Accept `ADCController` instead of raw channel references
- Clean separation of concerns

**Step 7: Refactor `IOManager`**
- Remove all direct Adafruit imports (`board`, `busio`, `MCP23017`, `ADS1115`, `AnalogIn`, `Direction`)
- Accept `HardwareAbstractionLayer` in constructor
- Replace `self.pins[name].value = x` with `self.pin_controller.set_output(name, x)`
- Replace `self.pins[name].value` reads with `self.pin_controller.read_input(name)`
- Remove `_mcp_lock` - handled by `I2CBusManager`
- Remove `MockPin`, `MockADCChannel` - handled by mock controllers
- Remove `_init_mock_hardware()` - handled by factory

#### Phase 3: Eliminate Multiprocessing for I2C

**Step 8: Replace `multiprocessing.Process` with `threading.Thread` for mode/cycle**
- `process_mode()`: Use `threading.Thread` instead of `multiprocessing.Process`
- `process_sequence()`: Use `threading.Thread` instead of `multiprocessing.Process`
- Remove `_ensure_hardware_for_child_process()` entirely
- Replace `multiprocessing.Event` with `threading.Event` for stop signals
- The `I2CBusManager` RLock naturally handles thread safety

**Rationale:** The current multiprocessing architecture was likely chosen for CPU isolation, but all the heavy work is I/O-bound (I2C bus operations, `time.sleep()` delays). Threading is more appropriate because:
- I2C file descriptors survive across threads but NOT across `fork()`
- No need for `_ensure_hardware_for_child_process()` reinitialization
- `threading.Lock` works across threads (unlike `threading.Lock` across processes)
- Eliminates the entire class of "child process I2C reinitialization" bugs
- Simpler process lifecycle management

**Step 9: Update `ModeManager`**
- Remove `_ensure_valid_mmap()` PID checking (no more child processes)
- Remove `_database_fallback_set/get` (mmap valid within single process)
- Simplify to thread-safe only (keep `threading.Lock`)

#### Phase 4: Cleanup and Testing

**Step 10: Remove dead code**
- Remove duplicate pin definitions
- Remove `_hardware_init_pid` tracking
- Remove `_ensure_hardware_for_child_process()`
- Remove `MockPin`, `MockADCChannel` from `io_manager.py`
- Remove direct `board`/`busio`/`digitalio` imports from `main.py`

**Step 11: Add hardware integration tests**
- Test `PinController` set/read cycle
- Test `ADCController` read operations
- Test bus contention under multi-threaded load
- Test mock implementations match real hardware interface
- Test bus recovery after simulated I2C errors

### 6.4 Migration Strategy

1. **Create new files alongside existing ones** - no breaking changes initially
2. **Add adapter layer** - IOManager creates hardware abstraction internally, delegates to it
3. **Gradual migration** - move one subsystem at a time (pins first, then ADC, then sensors)
4. **Test at each step** - run on hardware after each phase
5. **Remove old code** - only after full migration is verified on hardware

### 6.5 Risk Mitigation

- **Never change pin numbers and modes simultaneously** - verify pin mapping matches existing hardware
- **Keep ModeManager mmap approach** - it's working well for cross-component mode sharing
- **Maintain shutdown relay safety** - preserve the careful shutdown relay state management
- **Test on actual hardware** between each phase - I2C timing is sensitive to changes
- **Keep mock mode** as first-class citizen for development without hardware

---

## 7. File Reference

| File | Lines | Role |
|---|---|---|
| `main.py` | ~1400 | App entry point, Kivy properties, UI scheduling, cycle management |
| `controllers/io_manager.py` | ~2377 | Hardware I/O, mode/cycle control, MCP23017+ADS1115+pigpio |
| `controllers/pressure_sensor.py` | ~229 | ADC-to-pressure conversion, calibration |
| `utils/alarm_manager.py` | ~1273 | Alarm conditions (strategy pattern), AlarmManager coordinator |
| `utils/cycle_state_manager.py` | ~288 | Pause/resume cycle state for GM faults |
| `utils/data_handler.py` | ~440 | CSV data logging to USB/local |
| `utils/database_manager.py` | ~646 | SQLite abstraction layer |
| `utils/profile_handler.py` | ~252 | Profile-specific alarm configuration |
| `config/settings.py` | ~45 | TOML config loader, Kivy config |
