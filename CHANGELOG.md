# Changelog

All notable changes to the VST Green Machine Control Panel will be documented in this file.

## [0.6.0] - 2025-07-24

### Added
- Secret password override "C0D3CAF3" for startup code screen that works on all systems
- Improved OOBE navigation with better back button behavior
- Enhanced forward navigation that properly handles completed screens
- Centralized navigation methods in base OOBE screen class

### Fixed
- Fixed issue with application minimizing at startup by adding startup delays
- Fixed back button navigation for CS2 profile to properly skip screens not applicable to that profile
- Fixed translations on startup code screen to properly display in Spanish
- Improved translation handling to ensure all text elements are properly translated
- Fixed inconsistent translations database paths to use a single location in data/db/lang
- Fixed issue with back button canceling entire OOBE process
- Fixed navigation to skip only specific screens (QuickFunctionalityTest, PressureCalibration, OverfillOverride) when completed
- Fixed forward navigation to prevent skipping to main screen prematurely
- Fixed syntax errors in CRE number and contractor certification screens
- Ensured OOBE flags are properly reset when running ./test_oobe.py --reset
- Fixed contractor password screen to clear password field when navigating back to it
- Fixed issue with quick functionality test to only stop for specific alarm conditions (pressure sensor, overfill, vac pump, or shutdown)
- Fixed issue with zero pressure and variable pressure alarms not showing after functionality test
- Fixed startup crash caused by alarm_list_last_check attribute not being initialized before use
- Fixed inconsistent translations database paths in overfill_override_screen.py and quick_functionality_test_screen.py

## [Unreleased]

### Changed
- Completely refactored testing infrastructure for better organization and usability
- Added comprehensive help documentation for all test commands
- Reorganized tests folder structure for better maintainability
- Improved all testing documentation with clear examples
- Enhanced About screen with separated system status components and improved information display
- Added public About screen accessible from sidebar for basic system information

### Added
- Improved network status display with SORACOM connection state and signal strength
- Separated system status into distinct sections (Profile/Language, Pressure, Motor, Cycles)
- Added motor current monitoring to About screen
- Added run cycles and manual cycles counters to About screen
- New public About screen showing profile and device information (device name, panel SN, GM SN)
- New `run_tests.py` with unified interface for all testing functions
- Shared libraries for database operations, hardware simulation, and system utilities
- Support for short command options (e.g., `-s` for `--stage`, `-t` for `--type`)
- Improved error handling and feedback in all test operations
- Better signal handling for dynamic updates to running application
- New system status monitoring command
- Preset options for calibration operations

## [1.2.0] - 2025-04-01

### Added
- Support for CS12 profile in alarm handling
- New manual override feature for emergency scenarios
- Improved database error handling with retry mechanism

### Fixed
- Issue with pressure sensor calibration in extreme temperatures
- UI responsiveness when multiple alarms trigger simultaneously
- Problem with database locking during shutdown

## [1.1.0] - 2025-03-15

### Added
- Support for multiple language translations
- New diagnostics screen for troubleshooting
- Enhanced logging for better debugging

### Changed
- Improved UI appearance and responsiveness
- Reorganized settings screen for better usability
- Better error messages for hardware failures

### Fixed
- Various minor UI glitches
- Issue with alarm acknowledgment not being saved properly
- Problem with relay control timing

## [1.0.0] - 2025-02-01

### Added
- Initial release of the VST Green Machine Control Panel
- Basic control system for managing the vapor recovery process
- 72-hour shutdown functionality with staged warnings
- Basic alarm management and notification system
- User interface with main control screens
- Administrator functions for system configuration
