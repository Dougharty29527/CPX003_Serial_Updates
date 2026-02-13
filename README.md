# VST Green Machine Control Panel

Control panel software for the VST Green Machine vapor recovery system.

## Overview

The VST Green Machine Control Panel is a Python-based application that provides a user interface and control system for the Green Machine vapor recovery system. It monitors system status, manages alarms, and provides operational control for the hardware.

## Setup and Installation

1. Ensure Python 3.9+ is installed
2. Install required packages:
   ```bash
   pip3 install -r requirements.txt
   ```
3. Install and start the service:
   ```bash
   # Copy service file
   sudo cp service/gm_control_panel.service /etc/systemd/system/
   
   # Allow service user to run sudo without password
   echo "cpx003 ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/010_cpx003-nopasswd
   sudo chmod 440 /etc/sudoers.d/010_cpx003-nopasswd
   
   # Reload systemd and start service
   sudo systemctl daemon-reload
   sudo systemctl enable gm_control_panel
   sudo systemctl start gm_control_panel
   ```
5. Configure the system by modifying the configuration files in `vst_gm_control_panel/config/`

## Running the Application

The application can be launched using the provided `run.sh` script:

```bash
# Standard run
./run.sh

# Developer mode (provides additional logging and testing features)
./run.sh --dev

# Start with a specific screen
./run.sh --screen Maintenance
```

## Out-of-Box Experience (OOBE)

When first starting the application, you'll go through the Out-of-Box Experience (OOBE) which guides you through initial setup:

1. **Language Selection**: Choose between English and Spanish
2. **Profile Selection**: Select the appropriate profile (CS2, CS8, CS9, or CS12)
3. **GM Serial Entry**: Enter the Green Machine serial number
4. **Power Information**: Acknowledge power/shutdown information
5. **Date Verification**: Verify or modify the system date
6. **Timezone Verification**: Verify timezone or select a different one
7. **CRE Number**: Enter the Station CRE number for all profiles except CS2
8. **Contractor Certification**: Enter contractor certification number
9. **Contractor Password**: Enter contractor password
10. **Breaker Info**: Review breaker information (CS8 and CS12 profiles only)
11. **Quick Functionality Test**: Run a quick test of system functionality
12. **Pressure Calibration**: Calibrate the pressure sensor
13. **Overfill Override**: Configure overfill override settings
14. **Startup Code**: Enter the startup code (last 6 digits of Raspberry Pi serial number or "L0G1C")

### OOBE Flow Logic

The application startup flow checks the OOBE flags and directs the user to the appropriate screen:

- If all flags are false, it starts at the language selection screen
- If language is selected but profile is not, it starts at profile selection, and so on
- If all flags are true, it proceeds to the main screen as usual

### OOBE Navigation

The OOBE screens provide intuitive navigation with these features:

- **Back Button**: Allows returning to previous screens, skipping only specific completed screens (Quick Functionality Test, Pressure Calibration, and Overfill Override)
- **Forward Navigation**: Automatically skips specific completed screens when moving forward
- **Completion Tracking**: Each screen tracks its completion status independently
- **Secret Override**: The startup code screen accepts both the machine-specific code (last 6 digits of Raspberry Pi serial number) and a universal override code "C0D3CAF3"

### Resetting the OOBE

If you need to reset the OOBE process and start from the beginning:

```bash
# Reset all OOBE flags to start from the beginning
./test_oobe.py --reset
```

You can also set specific OOBE flags for testing different entry points:

```bash
# Start at profile selection screen
./test_oobe.py --language

# Start at GM serial screen
./test_oobe.py --language --profile

# Skip OOBE entirely
./test_oobe.py --language --profile --serial
```

## Project Structure

- `vst_gm_control_panel/`: Main application code
  - `assets/`: Images and other static assets
  - `components/`: Reusable UI components
  - `config/`: Configuration files and settings
  - `controllers/`: I/O and hardware controllers
  - `data/`: Database storage
  - `utils/`: Utility functions and classes
  - `views/`: Screen definitions and UI layouts
    - `oobe/`: Out-of-Box Experience screens
- `documentation/`: Technical documentation
- `tests/`: Automated tests

## System Architecture

The VST Green Machine Control Panel is a control system for managing vapor recovery operations. It monitors system pressure, controls operational cycles, manages alarms, and provides different operational modes based on user access levels.

### Key Components

#### Pressure System
- **Function**: Monitors system pressure through an analog sensor connected to an ADS1115 ADC
- **Normal Range**: Between -6.0 IWC and 2.0 IWC (inches water column)
- **Relationships**:
  - Triggers run cycles when pressure exceeds threshold (0.2 IWC in normal mode)
  - Initiates alarms when pressure is outside acceptable ranges
  - Used for leak detection during testing

#### Motor Control
- **Function**: Controls the vacuum pump motor through a relay
- **States**: ON/OFF
- **Protection**: Minimum 2-second off time between activations

#### Valve System
- **Components**: Three primary valves (V1, V2, V5) controlled via relays
- **Function**: Controls vapor flow paths during different operational modes
- **Configurations**: Different valve combinations create specific operational modes

#### Relay System
- **Components**: Motor relay, valve relays (V1, V2, V5), shutdown relay
- **Function**: Physical control of system components
- **Interface**: Controlled through MCP23017 I/O expander

### Operational Modes

#### Run Mode
- **Configuration**: Motor ON, V1 ON, V2 OFF, V5 ON
- **Purpose**: Main vacuum operation
- **Duration**: 120 seconds (production), 30 seconds (debug)
- **Trigger**: Automatically starts when pressure exceeds 0.2 IWC in normal operation

#### Rest Mode
- **Configuration**: Motor OFF, V1 OFF, V2 OFF, V5 OFF
- **Purpose**: System stabilization between active modes
- **Duration**: 15 seconds (production), 5 seconds (debug)

#### Purge Mode
- **Configuration**: Motor ON, V1 OFF, V2 ON, V5 OFF
- **Purpose**: Clears system with motor running and V2 open
- **Duration**: 50 seconds (production), 13 seconds (debug)

#### Burp Mode
- **Configuration**: Motor OFF, V1 OFF, V2 OFF, V5 ON
- **Purpose**: Brief pressure release
- **Duration**: 5 seconds (production), 2 seconds (debug)

#### Bleed Mode
- **Configuration**: Motor OFF, V1 OFF, V2 ON, V5 ON
- **Purpose**: Pressure bleeding
- **Duration**: Configurable or manual control

#### Leak Mode
- **Configuration**: Motor OFF, V1 ON, V2 ON, V5 ON
- **Purpose**: Configuration for leak testing
- **Duration**: 30 minutes (production), 3 minutes (debug)

### Operational Cycles

#### Run Cycle
- **Sequence**: run → rest → (purge → burp) × 6 → rest
- **Purpose**: Standard operational cycle for vapor recovery
- **Duration**: ~7 minutes 47 seconds
- **Trigger**: 
  - In normal mode: Starts when pressure exceeds 0.2 IWC
  - In test mode: Can be manually initiated

#### Manual Mode Cycle
- **Sequence**: 3 repetitions of standard run cycle
- **Purpose**: Extended operation for maintenance
- **Duration**: ~23 minutes 21 seconds
- **Access**: Level 2+ (Contractor)

#### Test Run Cycle
- **Sequence**: run → rest → run → rest → purge → rest
- **Purpose**: System testing with configurable timing
- **Access**: Level 1+ (Maintenance)

#### Functionality Test Cycle
- **Sequence**: 10 repetitions of: run → purge
- **Purpose**: Diagnostic sequence to verify component operation
- **Duration**: ~28 minutes 20 seconds
- **Access**: Level 1+ (Maintenance)

#### Leak Test Cycle
- **Sequence**: Sustained leak mode
- **Purpose**: Extended operation to check for system leaks
- **Duration**: 30 minutes (production), 3 minutes (debug)
- **Access**: Level 1+ (Maintenance)

## Access Levels

### Level 0 (Operator)
- View system status
- Acknowledge alarms
- Initiate run cycle

### Level 1 (Maintenance)
- All Level 0 functions
- Clear basic alarms
- Initiate test cycles
- Access maintenance screens

### Level 2 (Contractor)
- All Level 1 functions
- Manual mode control
- Clear system alarms
- Access contractor screens

### Level 3 (System)
- All Level 2 functions
- Modify system configuration
- Override shutdown
- Modify alarm parameters

### Level 4 (Administrator)
- All Level 3 functions
- Force clear all alarms
- Access administrative functions

## Alarm System

### Pressure-Related Alarms

#### Pressure Sensor Alarm
- **Trigger**: Pressure sensor reading falls below threshold
- **Action**: Stops current cycle, activates 72-hour shutdown protocol
- **Verification Time**: 30 seconds

#### Variable Pressure Alarm
- **Trigger**: Pressure doesn't change beyond threshold over time
- **Action**: Activates 72-hour shutdown protocol
- **Verification Time**: 60 minutes

#### Zero Pressure Alarm
- **Trigger**: Pressure reading stays near zero (±0.15 IWC) for extended period
- **Action**: Activates 72-hour shutdown protocol
- **Verification Time**: 60 minutes

#### Over Pressure Alarm
- **Trigger**: Pressure exceeds high threshold (default: 2.0 IWC)
- **Action**: Activates 72-hour shutdown protocol
- **Verification Time**: 30 minutes

#### Under Pressure Alarm
- **Trigger**: Pressure falls below low threshold (default: -6.0 IWC)
- **Action**: Activates 72-hour shutdown protocol
- **Verification Time**: 30 minutes

### 72-Hour Shutdown Protocol
- **Purpose**: Prevents continuous operation under alarm conditions
- **Stages**:
  1. **24 hours**: First warning notification
  2. **36 hours**: Second warning notification
  3. **47 hours**: Third warning notification (25 hours remaining)
  4. **71 hours**: Final warning notification (1 hour remaining)
  5. **72 hours**: Complete system shutdown

## Testing

### Testing Alarm Scenarios

The application supports both traditional and simplified command syntax for testing alarm scenarios:

```bash
# Traditional syntax
./tests/run_tests.sh set --stage 3 --alarm pressure_sensor   # Set stage 3 alarm (47-hour)
./tests/run_tests.sh clear --alarm variable_pressure         # Clear the alarm

# Simplified syntax
./tests/run_tests.sh alarm --set pressure_sensor --stage 3   # Set stage 3 alarm (47-hour)
./tests/run_tests.sh alarm --clear pressure_sensor           # Clear the alarm

# Custom time until shutdown
./tests/run_tests.sh set --stage shutdown --alarm pressure_sensor --hours 1     # 1 hour until shutdown
./tests/run_tests.sh alarm --set under_pressure --stage shutdown --minutes 10   # 10 minutes until shutdown
```

### Simulating Hardware Conditions

Hardware conditions like sensor failures can be simulated without physical changes:

```bash
# Traditional syntax
./tests/run_tests.sh simulate --sensor pressure_sensor --state disconnected

# Simplified syntax
./tests/run_tests.sh sim --sensor pressure --state off  # Disconnect pressure sensor
./tests/run_tests.sh sim --sensor pressure --state on   # Reconnect pressure sensor
```

### Controlling Individual Relays

The application provides direct control of individual relays for testing and debugging:

```bash
# Control specific relays
./tests/run_tests.sh relay --name motor --set on    # Turn on the motor relay
./tests/run_tests.sh relay --name v1 --set off      # Turn off valve 1
./tests/run_tests.sh relay --name v2 --set on       # Turn on valve 2
./tests/run_tests.sh relay --name v5 --set off      # Turn off valve 5
./tests/run_tests.sh relay --name shutdown --set on # Turn on shutdown relay
```

### Pressure Calibration

The application provides tools for pressure sensor calibration and testing:

```bash
# Set specific ADC zero value
./tests/run_tests.sh calibrate --zero 15600.0

# Use convenient presets
./tests/run_tests.sh calibrate --set high     # High pressure (over-pressure)
./tests/run_tests.sh calibrate --set low      # Low pressure (under-pressure)
./tests/run_tests.sh calibrate                # Auto-calibrate to current reading

# Show current calibration
./tests/run_tests.sh calibrate --status
```

### Testing Alarm Warnings

The 72-hour shutdown system can be tested using the `test_alarm_app.sh` script:

```bash
# Test 24-hour warning dialog
./tests/test_alarm_app.sh --warning1

# Test 47-hour warning dialog
./tests/test_alarm_app.sh --warning3 --alarm variable_pressure

# Test shutdown condition
./tests/test_alarm_app.sh --shutdown
```

For more details about testing, see the [Testing README](tests/README.md).

## Documentation

For comprehensive documentation of the system, please refer to our [Documentation Index](docs/index.md) which covers:

- [Architecture Overview](docs/architecture/index.md)
- [Core Components](docs/components/index.md)
- [Database System](docs/database/index.md)
- [Developer Guide](docs/developer-guide/index.md)
- [Testing Information](docs/testing/index.md)

## Contributing

Please follow these guidelines when contributing to the project:

1. Use descriptive commit messages
2. Follow PEP 8 style guide for Python code
3. Add tests for new functionality
4. Update documentation for changes
5. Refer to the [Developer Guide](docs/developer-guide/index.md) for detailed standards

## License

Vapor Systems Technologies, Inc. - All rights reserved.
