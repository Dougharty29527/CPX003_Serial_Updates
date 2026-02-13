# CPX003 Serial Updates - ESP32 IO Board Integration

This repository contains updated Python files for the VST GM Control Panel that provide full compatibility with the enhanced ESP32 IO Board firmware (Rev 10.8+).

## 📋 Overview

The CPX003 Serial Updates implement a unified serial communication protocol between the Linux control panel and ESP32 IO Board, featuring real-time sensor data streaming, advanced control commands, and data backfill capabilities.

## 🔧 Key Features

### 1. **Unified Serial Command Structure**
- **Real-time Sensor Packets (5Hz)**: Pressure, current, overfill, relay mode, failsafe status
- **Command Messages**: Structured JSON commands for device control
- **Status Messages**: Comprehensive system status updates (15s intervals)
- **Data Backfill**: Automatic SD card data recovery after passthrough mode

### 2. **Additional Control Commands**
- **Shutdown/Normal Mode**: Emergency site shutdown and restoration
- **Pressure Calibration**: Zero-point calibration for pressure sensors
- **Fast Polling**: 15-second BlueCherry polling (60-minute timeout)
- **Failsafe Control**: Enable/disable autonomous failsafe operation
- **Manual Relay Control**: Direct relay override for testing

### 3. **Data Backfill from SD Card**
- **Automatic Recovery**: ESP32 sends stored data after passthrough reboot
- **Filtered Data**: Only data from passthrough period is transmitted
- **Efficient Format**: JSON array with timestamp filtering
- **CBOR Integration**: Same data sent to CBOR for cellular transmission

## 📁 File Structure

```
CPX003_Serial_Updates/
├── main.py                              # Main application entry point
├── vst_gm_control_panel/
│   ├── controllers/
│   │   └── io_manager.py               # IO control and sensor management
│   └── utils/
│       └── modem.py                    # Serial communication handler
└── README.md                           # This documentation
```

## 🔄 Communication Protocol

### Real-time Sensor Packets (5Hz)
```json
{
  "pressure": -14.22,
  "current": 0.07,
  "overfill": 0,
  "sdcard": "OK",
  "relayMode": 1,
  "failsafe": 0,
  "shutdown": 0
}
```

### Command Messages
```json
{"type":"cmd","cmd":"fast_poll","val":1}      // Enable fast polling
{"type":"cmd","cmd":"enable_failsafe"}        // Enable failsafe
{"type":"cmd","cmd":"cal"}                    // Calibrate pressure
{"type":"data","mode":"shutdown"}             // Emergency shutdown
```

### Data Backfill Messages
```json
{
  "backfill": [
    {"timestamp":"2024-01-15 14:30:15","pressure":-12.45,"current":0.08,"mode":1,"error":0},
    {"timestamp":"2024-01-15 14:30:20","pressure":-12.42,"current":0.08,"mode":1,"error":0}
  ]
}
```

## 🚀 Installation & Setup

1. **Clone this repository**:
   ```bash
   git clone https://github.com/yourusername/CPX003_Serial_Updates.git
   cd CPX003_Serial_Updates
   ```

2. **Install dependencies**:
   ```bash
   pip install kivy pyserial
   ```

3. **Configure serial port**:
   - Update serial port settings in `modem.py` for your ESP32 connection
   - Default: `/dev/ttyUSB0` (Linux) or `COM3` (Windows)

4. **Run the application**:
   ```bash
   python main.py
   ```

## 📊 Enhanced Features

### **Fast Sensor Packet Parsing**
- **Real-time Updates**: 5Hz sensor data for immediate system monitoring
- **Error Handling**: Graceful handling of invalid data with fallback values
- **Calibration Support**: Automatic pressure calibration factor updates

### **Advanced Control Commands**
- **Failsafe Management**: Enable/disable autonomous operation
- **Emergency Controls**: Site shutdown and restoration capabilities
- **Performance Monitoring**: Fast polling for rapid diagnostics

### **Data Recovery System**
- **SD Card Integration**: Automatic data logging during all operations
- **Backfill Protocol**: Seamless data recovery after connectivity issues
- **Timestamp Filtering**: Efficient data retrieval for specific time periods

## 🔧 Technical Details

### Serial Communication
- **Baud Rate**: 115200
- **Protocol**: JSON over RS-232
- **Error Handling**: Robust parsing with automatic reconnection

### ESP32 Integration
- **Firmware Compatibility**: Rev 10.8+ with enhanced serial protocol
- **ADC Sampling**: 60Hz rolling averages for stable sensor readings
- **EEPROM Storage**: Persistent configuration and calibration data

### Python Implementation
- **Kivy Framework**: Cross-platform GUI for Linux/Windows
- **Threading**: Non-blocking serial communication
- **Logging**: Comprehensive debug and error logging

## 📈 Performance Characteristics

- **Sensor Update Rate**: 5Hz (200ms intervals)
- **Cellular Data Transmission**: 8020 bytes/hour @ 15s updates
- **SD Card Logging**: Continuous CSV format with timestamps
- **Memory Usage**: Optimized for long-term operation

## 🔒 Safety Features

- **Watchdog Integration**: Automatic system monitoring and recovery
- **Failsafe Operation**: Autonomous control when serial communication fails
- **Fault Code System**: Comprehensive error reporting and diagnostics
- **Emergency Shutdown**: Hardware-level site safety controls

## 📝 Recent Updates

### Version Changes
- **Added fast sensor packet parsing** for real-time data streaming
- **Implemented unified command structure** for all ESP32 controls
- **Added data backfill functionality** for SD card recovery
- **Enhanced error handling** and logging capabilities
- **Integrated failsafe controls** and emergency commands

### Compatibility
- **ESP32 Firmware**: Rev 10.8+ with serial protocol enhancements
- **Python Version**: 3.7+ with Kivy framework
- **Operating Systems**: Linux (primary), Windows (secondary)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly with ESP32 hardware
5. Submit a pull request

## 📞 Support

For issues or questions:
- Check the ESP32 firmware documentation
- Review serial protocol logs
- Verify hardware connections and baud rates

## 📄 License

This project is part of the VST GM Control Panel system. See main project for licensing details.