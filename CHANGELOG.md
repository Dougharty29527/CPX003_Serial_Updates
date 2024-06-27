# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2024-06-26

### Added
- Manual time entry option added to settings menu.
- Pressure sensor calibration added to test screen.
- Option to reboot machine added to test screen.
- Device name, software, and software version added to diagnostics menu.

## Changed

- Spanish translation of "Ejectar Ciclos" updated to "Ciclos".

## [0.1.0] - 2024-06-24

### Added

- Initial release of VST Control Panel software milestone 1.
- Added database manager for storing user, application, and green machine information.
- Added logger module for reporting errors, separated into module specific logs.
- Added language handler for translating text.
- Added adc module for handling pressure sensor operations.
- Added mcp module for handling relay operations.
- Added translations database to hold EN and ES translations.
- Added "Test" screen for testing purposes.
- Added application landing page, "Main" screen.
- Added top bar to all screens.
- Added side bar to all screens.
- Added dropdown menu to sidebar.
- Added status bar to "Main".
- Added diagnostics menu to "Test".
- Added run cycle sequence.
- Added debug run cycle sequence (changes mode times to: run=10, rest=1, purge=5, burp=2)
