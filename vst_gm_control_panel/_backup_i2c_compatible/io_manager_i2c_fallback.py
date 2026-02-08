#!/usr/bin/env python3
"""
I2C module for handling MCP and ADC functionality.
"""

# Standard imports.
import board
import busio
from collections import deque
from datetime import datetime
from digitalio import Direction
import mmap
import multiprocessing
import os
import pigpio
import signal
import sqlite3
import struct
import threading
import time

# Constants for cleanup
CLEANUP_TIMEOUT = 2.0  # Maximum time to wait for cleanup in seconds
PROCESS_STOP_TIMEOUT = 0.5  # Time to wait for processes to stop gracefully

# Third-party imports.
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from adafruit_mcp230xx.mcp23017 import MCP23017
from kivymd.app import MDApp
from kivy.logger import Logger
from kivy.clock import Clock

# Local imports
from .pressure_sensor import PressureSensor


class MockPin:
    """Mock pin object for graceful operation without hardware"""
    def __init__(self):
        self._value = False
        self.direction = None
    
    @property
    def value(self):
        return self._value
    
    @value.setter
    def value(self, val):
        self._value = val


class MockADCChannel:
    """Mock ADC channel for graceful operation without hardware"""
    def __init__(self):
        self._value = 15422  # Default ADC zero value
    
    @property
    def value(self):
        return self._value
    
    @value.setter
    def value(self, val):
        self._value = val


class ModeManager:
    """
    Process-safe memory-mapped file manager for ultra-fast mode state operations.
    Replaces SQLite database for mode storage with ~1000x performance improvement.
    Now handles multiprocessing race conditions safely.
    """
    MODE_MAP = {'rest': 0, 'run': 1, 'purge': 2, 'burp': 3, 'bleed': 4, 'leak': 5}
    REVERSE_MAP = {v: k for k, v in MODE_MAP.items()}
    
    def __init__(self, file_path='/tmp/vst_mode.bin'):
        self.file_path = file_path
        self.struct_format = 'I'  # Single unsigned int for mode
        self.struct_size = 4
        self.file = None
        self.mmap = None
        self._process_id = os.getpid()  # Track which process owns this instance
        self._lock = threading.Lock()   # Thread safety within process
        self._init_mmap()
        Logger.info(f'ModeManager: Initialized with mmap file: {file_path} (PID: {self._process_id})')
    
    def _init_mmap(self):
        """Initialize memory-mapped file for mode storage."""
        try:
            # Create file if doesn't exist, initialize with 'rest' (0)
            if not os.path.exists(self.file_path):
                with open(self.file_path, 'wb') as f:
                    f.write(struct.pack(self.struct_format, 0))  # rest = 0
                Logger.debug(f'ModeManager: Created new mode file: {self.file_path}')
            
            self.file = open(self.file_path, 'r+b')
            self.mmap = mmap.mmap(self.file.fileno(), self.struct_size)
        except Exception as e:
            Logger.error(f'ModeManager: Failed to initialize mmap: {e}')
            raise
    
    def _ensure_valid_mmap(self):
        """Ensure mmap is valid for current process - handles multiprocessing race conditions."""
        current_pid = os.getpid()
        
        # If we're in a different process, reinitialize
        if current_pid != self._process_id:
            Logger.debug(f'ModeManager: Process changed from {self._process_id} to {current_pid}, reinitializing')
            self._process_id = current_pid
            self._cleanup_current()
            self._init_mmap()
            return True
            
        # Check if mmap is still valid
        try:
            if not self.mmap or self.mmap.closed:
                Logger.debug('ModeManager: mmap invalid, reinitializing')
                self._cleanup_current()
                self._init_mmap()
                return True
        except (ValueError, OSError):
            Logger.debug('ModeManager: mmap error detected, reinitializing')
            self._cleanup_current()
            self._init_mmap()
            return True
            
        return False
    
    def _cleanup_current(self):
        """Clean up current mmap resources safely."""
        try:
            if self.mmap:
                self.mmap.close()
                self.mmap = None
            if self.file:
                self.file.close()
                self.file = None
        except Exception:
            pass  # Ignore cleanup errors during recovery
    
    def _database_fallback_set(self, mode_str):
        """Fallback to database when mmap fails - maintains system safety."""
        try:
            # Import here to avoid circular imports
            import sqlite3
            db_path = '/home/cpx003/vst_gm_control_panel/vst_gm_control_panel/data/db/app.db'
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE IF NOT EXISTS gm (id INTEGER PRIMARY KEY, key TEXT UNIQUE, value TEXT)')
            cursor.execute('INSERT OR REPLACE INTO gm (key, value) VALUES (?, ?)', ('mode_fallback', mode_str))
            conn.commit()
            conn.close()
            Logger.info(f'ModeManager: Used database fallback to set mode: {mode_str}')
            return True
        except Exception as e:
            Logger.error(f'ModeManager: Database fallback failed: {e}')
            return False
    
    def _database_fallback_get(self):
        """Fallback to database when mmap fails - maintains system safety."""
        try:
            import sqlite3
            db_path = '/home/cpx003/vst_gm_control_panel/vst_gm_control_panel/data/db/app.db'
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE IF NOT EXISTS gm (id INTEGER PRIMARY KEY, key TEXT UNIQUE, value TEXT)')
            cursor.execute('SELECT value FROM gm WHERE key = ?', ('mode_fallback',))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else 'rest'
        except Exception as e:
            Logger.error(f'ModeManager: Database fallback read failed: {e}')
            return 'rest'  # Safe default
    
    def set_mode(self, mode_str):
        """
        Process-safe ultra-fast mode write operation (replaces update_mode_safely).
        Typically completes in <0.1ms vs 10-20ms for SQLite.
        Now handles multiprocessing race conditions safely.
        """
        with self._lock:
            try:
                self._ensure_valid_mmap()
                mode_int = self.MODE_MAP.get(mode_str, 0)
                self.mmap[:self.struct_size] = struct.pack(self.struct_format, mode_int)
                self.mmap.flush()
                return True
            except (ValueError, OSError) as e:
                # Handle mmap closed or invalid errors gracefully with fallback
                Logger.debug(f'ModeManager: mmap unavailable during set_mode("{mode_str}"): {e}')
                return self._database_fallback_set(mode_str)
            except Exception as e:
                Logger.error(f'ModeManager: Failed to set mode "{mode_str}": {e}')
                return self._database_fallback_set(mode_str)
    
    def get_mode(self):
        """
        Process-safe ultra-fast mode read operation (replaces gm_db.get_setting('mode')).
        Typically completes in <0.01ms vs 5-10ms for SQLite.
        Now handles multiprocessing race conditions safely.
        """
        with self._lock:
            try:
                self._ensure_valid_mmap()
                mode_int = struct.unpack(self.struct_format, self.mmap[:self.struct_size])[0]
                mode_str = self.REVERSE_MAP.get(mode_int, 'rest')
                return mode_str
            except (ValueError, OSError) as e:
                # Handle mmap closed or invalid errors gracefully with fallback
                Logger.debug(f'ModeManager: mmap unavailable during get_mode(): {e}')
                return self._database_fallback_get()
            except Exception as e:
                Logger.error(f'ModeManager: Failed to read mode: {e}')
                return self._database_fallback_get()
    
    def cleanup(self):
        """Clean up memory-mapped file resources safely."""
        with self._lock:
            self._cleanup_current()
            Logger.debug(f'ModeManager: Cleanup completed for process {self._process_id}')


class IOManager:
    """
    Input Output module.
    """

    # Class variable for simulated motor current
    _simulated_motor_current = None

    def __init__(self, gain=1):
        # Register signal handler for SIGTERM only
        signal.signal(signal.SIGTERM, self._handle_signal)
        # SIGINT (Ctrl+C) is handled by main.py
        
        self.app = MDApp.get_running_app()
        
        # Initialize ultra-fast memory-mapped mode manager (replaces database)
        self.mode_manager = ModeManager()
        Logger.info('IOManager: Initialized ModeManager for ultra-fast mode operations')
        
        # Hardware availability tracking
        self.hardware_available = False
        self.hardware_error = None
        
        # Initialize hardware with graceful degradation
        try:
            # Attempt hardware initialization
            self.i2c = busio.I2C(board.SCL, board.SDA)
            self._adc = ADS.ADS1115(self.i2c)
            self._mcp = MCP23017(self.i2c)
            self.adc_gain = gain
            self._channel2 = AnalogIn(self._adc, ADS.P2)
            self._channel3 = AnalogIn(self._adc, ADS.P3)
            self.current_readings = deque(maxlen=60)
            self.current_failure_count = 0
            self.max_current_failure_count = 10
            self.last_current_value = '0.00'
            
            # Initialize pressure sensor
            self.pressure_sensor = PressureSensor(self._adc)
            self.pin_delay = 0.01
            self.pins = {
                'motor': self._mcp.get_pin(0),
                'v1': self._mcp.get_pin(1),
                'v2': self._mcp.get_pin(2),
                'v5': self._mcp.get_pin(3),
                'shutdown': self._mcp.get_pin(4),
                'tls': self._mcp.get_pin(8),
                'panel_power': self._mcp.get_pin(10)
            }
            
            self.hardware_available = True
            self._hardware_init_pid = os.getpid()  # Track which process initialized hardware
            Logger.info('IOManager: Hardware initialized successfully')
            
        except Exception as e:
            # Hardware initialization failed - enter graceful degradation mode
            self.hardware_error = str(e)
            self._hardware_init_pid = os.getpid()
            Logger.warning(f'IOManager: Hardware unavailable - running in mock mode: {e}')
            self._init_mock_hardware()
        self.mode_process = None
        self.cycle_process = None
        self._stop_mode_event = multiprocessing.Event()
        self._stop_cycle_event = multiprocessing.Event()
        self.purge_timer = None
        self.purge_check = False
        self.mode = 'rest'
        self._mcp_lock = threading.Lock()  # Thread-safe I2C bus coordination
        self._initialization_complete = False
        self.setup_pins()
        self.set_rest()
        self._initialization_complete = True
        self.buzzer_pin = 27
        self.pi = pigpio.pi()
        self.buzzer_stop_event = threading.Event()
        self.manual_cycle_count = 0
        self._cleanup_in_progress = False
        self._in_bleed_mode = False
        self._last_shutdown_relay_state = None  # Track relay state to reduce logging spam
        
        # Cycle state tracking for pause/resume functionality
        self._current_sequence = None
        self._current_step = 0
        self._step_start_time = 0
        self._is_manual_cycle = False
        self._cycle_state_manager = None
        self._step_progress_file = '/tmp/vst_cycle_progress.json'
        
        # GM fault monitoring state (CS9 profile only)
        self.gm_fault_count = 0
        self.high_current_detected = False
        self.high_current_start_time = 0
        self.low_current_detected = False
        self.low_current_start_time = 0
        self.gm_fault_in_rest_period = False
        self._gm_fault_check_event = None
        self._rest_period_callback = None
        
        # Background sensor reading thread for non-blocking UI
        # Thread is started later via start_background_sensors() after app.io is assigned
        self._sensor_lock = threading.Lock()
        self._sensor_stop_event = threading.Event()
        self._cached_pressure = '-99.9'  # Cached pressure value
        self._cached_current = '0.00'    # Cached current value
        self._sensor_thread = None

    def _init_mock_hardware(self):
        """
        Initialize mock hardware for graceful operation without physical devices.
        Allows the application to run for UI testing and development.
        """
        # Create mock I2C components
        self.i2c = None
        self._adc = None
        self._mcp = None
        self.adc_gain = 1
        
        # Create mock ADC channels
        self._channel2 = MockADCChannel()
        self._channel3 = MockADCChannel()
        self.current_readings = deque(maxlen=60)
        self.current_failure_count = 0
        self.max_current_failure_count = 10
        self.last_current_value = '0.00'
        
        # Initialize mock pressure sensor
        self.pressure_sensor = PressureSensor(None, mock_mode=True)
        
        self.pin_delay = 0.01
        
        # Create mock pins that simulate hardware without errors
        self.pins = {
            'motor': MockPin(),
            'v1': MockPin(),
            'v2': MockPin(),
            'v5': MockPin(),
            'shutdown': MockPin(),
            'tls': MockPin(),
            'panel_power': MockPin()
        }
        
        Logger.info('IOManager: Mock hardware initialized - UI will function but no physical I/O')

    def start_background_sensors(self):
        '''Start background thread for sensor readings. Call after IOManager is assigned to app.io.'''
        if self._sensor_thread is not None and self._sensor_thread.is_alive():
            return  # Thread already running
        
        self._sensor_stop_event.clear()
        self._sensor_thread = threading.Thread(
            target=self._sensor_reading_loop,
            name='SensorReadingThread',
            daemon=True
        )
        self._sensor_thread.start()
        Logger.info('IOManager: Background sensor reading thread started')

    def _stop_sensor_thread(self):
        '''Stop the background sensor reading thread.'''
        self._sensor_stop_event.set()
        if self._sensor_thread is not None and self._sensor_thread.is_alive():
            self._sensor_thread.join(timeout=2.0)
            if self._sensor_thread.is_alive():
                Logger.warning('IOManager: Sensor thread did not stop gracefully')
        self._sensor_thread = None
        Logger.info('IOManager: Background sensor reading thread stopped')

    def _sensor_reading_loop(self):
        '''Background loop that reads sensors without blocking the UI thread.'''
        Logger.info('IOManager: Sensor reading loop started')
        
        while not self._sensor_stop_event.is_set():
            try:
                # Read pressure (only if hardware available and not mock mode)
                if self.hardware_available and hasattr(self, 'pressure_sensor'):
                    try:
                        pressure = self.pressure_sensor.get_pressure()
                        with self._sensor_lock:
                            self._cached_pressure = pressure if pressure is not None else '-99.9'
                    except Exception as e:
                        Logger.debug(f'IOManager: Pressure read error in background: {e}')
                # ==============================================================
                # REV 10 PATCH: When I2C hardware is unavailable (MCP23017 gone),
                # pull pressure from ESP32 serial data instead of local ADC.
                # ESP32 reads ADS1015 at 60Hz with rolling averages and sends
                # computed values in its status packet every 15 seconds.
                # ==============================================================
                elif not self.hardware_available:
                    try:
                        serial_mgr = self.app.serial_manager if hasattr(self.app, 'serial_manager') else None
                        if serial_mgr and serial_mgr.esp32_last_update is not None:
                            pressure_val = serial_mgr.esp32_pressure
                            with self._sensor_lock:
                                self._cached_pressure = f'{pressure_val:.2f}'
                    except Exception as e:
                        Logger.debug(f'IOManager: Serial pressure fallback error: {e}')
                
                # Read current (only if hardware available)
                if self.hardware_available:
                    try:
                        current = self.get_current()
                        with self._sensor_lock:
                            self._cached_current = current if current is not None else '-99.9'
                    except Exception as e:
                        Logger.debug(f'IOManager: Current read error in background: {e}')
                # ==============================================================
                # REV 10 PATCH: When I2C hardware is unavailable, pull motor
                # current from ESP32 serial data instead of local ADS1115 ADC.
                # ESP32 reads differential channels P2-P3 at 60Hz.
                # ==============================================================
                elif not self.hardware_available:
                    try:
                        serial_mgr = self.app.serial_manager if hasattr(self.app, 'serial_manager') else None
                        if serial_mgr and serial_mgr.esp32_last_update is not None:
                            current_val = serial_mgr.esp32_current
                            with self._sensor_lock:
                                self._cached_current = f'{current_val:.2f}'
                    except Exception as e:
                        Logger.debug(f'IOManager: Serial current fallback error: {e}')
                
                # Short sleep between readings - keeps UI responsive
                for _ in range(2):
                    if self._sensor_stop_event.is_set():
                        break
                    time.sleep(0.1)
                    
            except Exception as e:
                Logger.error(f'IOManager: Error in sensor reading loop: {e}')
                time.sleep(1)  # Prevent tight loop on error
        
        Logger.info('IOManager: Sensor reading loop stopped')

    def get_cached_pressure(self):
        '''Get the cached pressure reading (non-blocking).'''
        with self._sensor_lock:
            return self._cached_pressure

    def get_cached_current(self):
        '''Get the cached current reading (non-blocking).'''
        with self._sensor_lock:
            return self._cached_current

    def _handle_signal(self, signum, frame):
        """Handle termination signals by initiating cleanup and exiting."""
        if not self._cleanup_in_progress:
            print(f'\nReceived signal {signum}, initiating cleanup...')
            self._cleanup_in_progress = True
            self.cleanup()
            # Exit the process after cleanup to ensure systemctl stop works quickly
            os._exit(0)

    @staticmethod
    def map_value(x, in_min, in_max, out_min, out_max):
        """
        Map the value to a new range.
        """
        return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

    @staticmethod
    def _calculate_average(readings):
        '''
        Calculate the average of the readings.
        '''
        if readings is None or len(readings) == 0:
            return 0

        if len(readings) > 2:
            readings = sorted(readings)
            return sum(readings[1:-1]) / (len(readings) - 2)

        return sum(readings) / len(readings)

    def _log(self, level, message):
        '''
        Log message with specified level.
        '''
        level = level.lower()
        if hasattr(Logger, level):
            getattr(Logger, level)(f'IOController: {message}')
        else:
            Logger.warning(f'IOController: Invalid log level "{level}". Message: {message}')

    def setup_pins(self):
        """
        Setup the pins for the MCP23017 with retries and error handling.
        """
        max_attempts = 3
        
        def configure_pin(pin_name, direction):
            """Configure a single pin with retry logic"""
            for attempt in range(max_attempts):
                try:
                    self.pins[pin_name].direction = direction
                    if attempt > 0:
                        Logger.debug(f'IOManager: ERROR RETRY - Pin {pin_name} configured successfully on attempt {attempt + 1}')
                    return True
                except (OSError, IOError) as e:
                    Logger.debug(f'IOManager: ERROR RETRY - Pin {pin_name} configuration attempt {attempt + 1}/{max_attempts} failed: {e}')
                    if attempt == max_attempts - 1:
                        Logger.debug(f'IOManager: ERROR RETRY - Pin {pin_name} configuration failed after all {max_attempts} attempts')
                        return False
                    time.sleep(0.1)  # Brief delay before retry
            return False

        try:
            self._mcp_lock.acquire()
            
            # Configure output pins
            output_success = True
            for pin in ['motor', 'v1', 'v2', 'v5', 'shutdown']:
                if not configure_pin(pin, Direction.OUTPUT):
                    output_success = False
                    break
                    
            # Configure input pins
            input_success = True
            for pin in ['tls', 'panel_power']:
                if not configure_pin(pin, Direction.INPUT):
                    input_success = False
                    break
                    
            # If any configuration failed, try resetting I2C
            if not (output_success and input_success):
                self.reset_i2c()
                
        except Exception as e:
            Logger.debug(f'IOManager: ERROR RETRY - Exception during pin setup: {e}')
            pass
        finally:
            if self._mcp_lock.locked():
                self._mcp_lock.release()

    def _is_vac_pump_alarm_active(self):
        """
        Check if vac pump alarm is currently active.
        """
        try:
            vac_pump_alarm = self.app.gm_db.get_setting('vac_pump_alarm')
            vac_pump_failure_count = self.app.alarms_db.get_setting('vac_pump_failure_count')
            
            is_active = vac_pump_alarm and vac_pump_failure_count is not None
            return is_active
        except Exception as e:
            self._log('error', f'Error checking vac pump alarm status: {e}')
            return False

    def set_rest(self):
        """
        Set to rest mode.
        NOTE: This method only sets cycle-related pins (motor, v1, v2, v5).
        The shutdown relay is managed separately during initialization and shutdown operations.
        """
        # Ensure I2C is valid for child processes
        self._ensure_hardware_for_child_process()
        
        max_attempts = 3
        
        # Function to set a single pin with retry
        def set_pin_safely(pin_name, value):
            for attempt in range(max_attempts):
                try:
                    self.pins[pin_name].value = value
                    if attempt > 0:
                        Logger.debug(f'IOManager: ERROR RETRY - Pin {pin_name} set to {value} successfully on attempt {attempt + 1}')
                    return True
                except (OSError, IOError) as e:
                    Logger.debug(f'IOManager: ERROR RETRY - Setting pin {pin_name} to {value} attempt {attempt + 1}/{max_attempts} failed: {e}')
                    if attempt == max_attempts - 1:
                        Logger.debug(f'IOManager: ERROR RETRY - Pin {pin_name} setting failed after all {max_attempts} attempts, resetting I2C')
                        # Try resetting I2C bus on last attempt
                        self.reset_i2c()
                        return False
                    time.sleep(0.1)  # Brief delay before retry
            return False

        try:
            # Manage shutdown relay based on system state
            if not self._initialization_complete:
                # During initialization, default to enabling shutdown relay (safe state)
                shutdown_value = not self.app.shutdown
                shutdown_success = set_pin_safely('shutdown', shutdown_value)
            else:
                # After initialization, DON'T change shutdown relay state in set_rest()
                # The relay is managed by specific alarm handlers and toggle_shutdown()
                # Changing it here would override alarm-driven relay control
                shutdown_success = True
            
            # Set cycle-related pins to rest state
            pin_success = True
            for pin in ['motor', 'v1', 'v2', 'v5']:
                if not set_pin_safely(pin, False):
                    pin_success = False
                    
            # Update mode using ultra-fast memory-mapped file (replaces database)
            db_success = False
            for attempt in range(max_attempts):
                try:
                    self.mode_manager.set_mode('rest')
                    db_success = True
                    break
                except Exception as db_error:
                    Logger.warning(f'IOManager: ModeManager set_mode attempt {attempt + 1} failed: {db_error}')
                    if attempt >= max_attempts - 1:
                        pass
                    continue
            
            # If any operation failed, try resetting I2C bus
            if not all([shutdown_success, pin_success, db_success]):
                self.reset_i2c()
                    
        except Exception as e:
            # Final attempt to reset I2C bus
            self.reset_i2c()

    def set_bleed(self):
        """
        Set to bleed mode.
        """
        if self.app.shutdown:
            return
        # Ensure I2C is valid for child processes
        self._ensure_hardware_for_child_process()
        
        try:
            for pin in ['motor', 'v1']:
                self.pins[pin].value = False
            for pin in ['v2', 'v5']:
                self.pins[pin].value = True
        except Exception as e:
            pass

    def set_pin_delay(self, pin_delay):
        """
        Purpose:
        - Set the pin delay.
        """
        self.pin_delay = pin_delay

    def get_mode_times(self, cycle_type='normal'):
        '''
        Get mode times based on debug or production mode and cycle type.
        
        Args:
            cycle_type: 'normal' for regular run cycles, 'test' for system/test mode
        '''
        times = {
            'production': {
                'run_time': 120,
                'rest_time': 15,
                'purge_time': 50,      # Normal purge: 50 seconds
                'test_purge_time': 30, # Test purge: 30 seconds
                'burp_time': 5
            },
            'debug': {
                'run_time': 30,
                'rest_time': 5,
                'purge_time': 50,      # Normal purge: 50 seconds
                'test_purge_time': 30, # Test purge: 30 seconds
                'burp_time': 2
            }
        }
        mode = 'debug' if self.app.debug else 'production'
        
        # Select appropriate purge time based on cycle type
        if cycle_type == 'test':
            purge_time = times[mode]['test_purge_time']
        else:
            purge_time = times[mode]['purge_time']
        
        run_time = times[mode]['run_time']
        rest_time = times[mode]['rest_time']
        burp_time = times[mode]['burp_time']
        
        return run_time, rest_time, purge_time, burp_time

    def sleep_with_check(self, delay):
        """
        Purpose:
        - Sleep for the specified delay.
        """
        start_time = time.monotonic()
        end_time = start_time + delay
        while time.monotonic() < end_time:
            if self._stop_mode_event.is_set() or self._stop_cycle_event.is_set():
                return False
            remaining_time = end_time - time.monotonic()
            if remaining_time > 0:
                time.sleep(min(0.01, remaining_time))  # Sleep for the smaller of 0.01 or remaining time.
        return True

    
    def _ensure_hardware_for_child_process(self):
        """
        Reinitialize I2C hardware if running in a child process.
        I2C file descriptors don't survive fork(), so we need fresh connections.
        IMPORTANT: Preserves shutdown relay state - child processes should not alter it.
        """
        current_pid = os.getpid()
        if not hasattr(self, '_hardware_init_pid') or current_pid == self._hardware_init_pid:
            return  # Same process, hardware is valid
        
        Logger.debug(f'IOManager: Child process {current_pid} reinitializing I2C (parent was {self._hardware_init_pid})')
        
        try:
            # Create fresh I2C connection for this child process
            self.i2c = busio.I2C(board.SCL, board.SDA)
            self._mcp = MCP23017(self.i2c)
            
            # Reinitialize pins with fresh MCP connection
            self.pins = {
                'motor': self._mcp.get_pin(0),
                'v1': self._mcp.get_pin(1),
                'v2': self._mcp.get_pin(2),
                'v5': self._mcp.get_pin(3),
                'shutdown': self._mcp.get_pin(4),
                'tls': self._mcp.get_pin(8),
                'panel_power': self._mcp.get_pin(10)
            }
            
            # Setup pin directions for cycle-related pins only
            for pin in ['motor', 'v1', 'v2', 'v5']:
                self.pins[pin].direction = Direction.OUTPUT
            
            # Setup shutdown relay - read current physical state from chip BEFORE setting direction
            # The MCP23017 chip retains its state; we just need a fresh Python connection
            # Read GPIO register directly to get current output latch state for pin 4
            try:
                # Read OLATA register (0x14) to get current output latch state
                current_olat = self._mcp.gpio
                shutdown_was_on = bool(current_olat & (1 << 4))  # Pin 4 is shutdown
            except Exception:
                # If read fails, default to enabled (safe state for normal operation)
                shutdown_was_on = not getattr(self.app, 'shutdown', False)
            
            self.pins['shutdown'].direction = Direction.OUTPUT
            self.pins['shutdown'].value = shutdown_was_on
            Logger.debug(f'IOManager: Child process preserved shutdown relay state: {shutdown_was_on}')
            
            # Setup input pins
            for pin in ['tls', 'panel_power']:
                self.pins[pin].direction = Direction.INPUT
            
            self._hardware_init_pid = current_pid
            self.hardware_available = True
            Logger.info(f'IOManager: Child process {current_pid} I2C reinitialized successfully')
            
        except Exception as e:
            Logger.error(f'IOManager: Child process {current_pid} failed to reinitialize I2C: {e}')
            self.hardware_available = False

    def set_mode(self, mode):
        """
        Purpose:
        - Set the pins for the specified mode.
        """
        # Ensure I2C is valid for child processes
        self._ensure_hardware_for_child_process()
        
        modes = {
            'run': {'motor': True, 'v1': True, 'v2': False, 'v5': True},
            'rest': {'motor': False, 'v1': False, 'v2': False, 'v5': False},
            'purge': {'motor': True, 'v1': False, 'v2': True, 'v5': False},
            'burp': {'motor': False, 'v1': False, 'v2': False, 'v5': True},
            'bleed': {'motor': False, 'v1': False, 'v2': True, 'v5': True},
            'leak': {'motor': False, 'v1': True, 'v2': True, 'v5': True}
        }
        max_attempts = 3
        
        if mode not in modes:
            self.log_notification_safely(f'Invalid mode: {mode}')
            Logger.debug(f'IOManager: MODE CHANGE - Invalid mode requested: {mode}')
            return
            
        try:
            # Check if we're entering or exiting bleed mode
            entering_bleed = mode == 'bleed' and not self._in_bleed_mode
            exiting_bleed = mode != 'bleed' and self._in_bleed_mode
            
            # Debug logging for mode changes
            if self.mode != mode:
                Logger.debug(f'Mode: {mode.title()} - {modes[mode]}')
            
            self.mode = mode
            # Update bleed mode state
            self._in_bleed_mode = (mode == 'bleed')
            
            # Only log when entering bleed mode
            if entering_bleed:
                self._log('info', 'Pressure -0.01 below low limit 0, entering BLEED mode.')
                Logger.debug('IOManager: MODE CHANGE - Entering BLEED mode due to low pressure')
            
            # Update mode using ultra-fast memory-mapped file (replaces database)
            for attempt in range(max_attempts):
                try:
                    self.mode_manager.set_mode(mode)
                    if attempt > 0:
                        Logger.debug(f'IOManager: MODE CHANGE - ModeManager update succeeded on attempt {attempt + 1}')
                    break
                except Exception as e:
                    if attempt >= max_attempts - 1:
                        Logger.debug(f'IOManager: MODE CHANGE - ModeManager update failed after {max_attempts} attempts')
                        raise
                    Logger.debug(f'IOManager: MODE CHANGE - ModeManager update attempt {attempt + 1} failed, retrying')
                    
            for pin, value in modes[mode].items():
                if self._stop_mode_event.is_set():
                    break
                    
                success = False
                try:
                    for attempt in range(max_attempts):
                        self._mcp_lock.acquire()
                        try:
                            self.pins[pin].value = value
                            
                            # Verify the pin was set correctly
                            actual_value = self.pins[pin].value
                            if actual_value == value:
                                success = True
                                if attempt > 0:
                                    Logger.debug(f'IOManager: MODE CHANGE - Pin {pin} set to {value} on attempt {attempt + 1}')
                                break
                            else:
                                Logger.debug(f'IOManager: MODE CHANGE - Pin {pin} retry {attempt + 1}/{max_attempts} failed')
                                self.reset_i2c()
                        finally:
                            if self._mcp_lock.locked():
                                self._mcp_lock.release()
                            
                    if self.pin_delay:
                        self.sleep_with_check(self.pin_delay)
                        
                except IOError as e:
                    Logger.debug(f'IOManager: MODE CHANGE - IOError setting pin {pin}: {e}')
                    
            time.sleep(0.2)
            active_pins = self.get_values()
            
        except Exception as e:
            if self._mcp_lock.locked():
                self._mcp_lock.release()

    def set_cycle_state_manager(self, cycle_state_manager):
        """Set the cycle state manager for pause/resume functionality."""
        self._cycle_state_manager = cycle_state_manager

    def pause_current_cycle(self):
        """
        Pause the currently running cycle for GM fault handling.
        
        Returns:
            bool: True if cycle was paused successfully
        """
        try:
            if not self.cycle_process or not self.cycle_process.is_alive():
                self._log('warning', 'No active cycle to pause')
                return False
                
            # Load current step progress from child process
            self._load_step_progress()
                
            # Calculate elapsed time in current step
            elapsed_in_step = 0
            if self._step_start_time > 0:
                elapsed_in_step = time.time() - self._step_start_time
                
            # Save cycle state BEFORE stopping the cycle
            if self._cycle_state_manager and self._current_sequence:
                self._log('debug', f'Saving cycle state: sequence={len(self._current_sequence)} steps, current_step={self._current_step}, elapsed={elapsed_in_step:.1f}s')
                success = self._cycle_state_manager.save_cycle_state(
                    self._current_sequence,
                    self._current_step,
                    elapsed_in_step,
                    self._is_manual_cycle
                )
                if not success:
                    self._log('error', 'Failed to save cycle state for pause')
                    return False
            else:
                self._log('error', f'Cannot save state: manager={self._cycle_state_manager is not None}, sequence={self._current_sequence is not None}')
                return False
            
            # Stop the current cycle
            self.stop_cycle()
            
            # Set to rest mode
            self.set_rest()
            
            self._log('info', f'Cycle paused successfully at step {self._current_step}')
            return True
            
        except Exception as e:
            self._log('error', f'Error pausing cycle: {e}')
            return False

    def resume_paused_cycle(self):
        """
        Resume a previously paused cycle.
        
        Returns:
            bool: True if cycle was resumed successfully
        """
        try:
            if not self._cycle_state_manager:
                self._log('error', 'No cycle state manager available for resume')
                return False
                
            # Load the saved state
            state_data = self._cycle_state_manager.load_cycle_state()
            if not state_data:
                self._log('warning', 'No saved cycle state found for resume')
                return False
                
            # Create resume sequence
            resume_sequence = self._cycle_state_manager.create_resume_sequence(state_data)
            if not resume_sequence:
                self._log('warning', 'No sequence to resume')
                self._cycle_state_manager.clear_cycle_state()
                return False
                
            # Start the resume sequence
            is_manual = state_data.get('is_manual', False)
            self._log('info', f'Resuming cycle with {len(resume_sequence)} remaining steps')
            
            # Process the resume sequence
            self.process_sequence(resume_sequence)
            
            # Clear the saved state
            self._cycle_state_manager.clear_cycle_state()
            
            return True
            
        except Exception as e:
            self._log('error', f'Error resuming cycle: {e}')
            return False

    def log_notification_safely(self, message):
        """
        Log a notification with a fresh database connection.
        Safe to use in child processes.
        
        Args:
            message: The notification message to log
        """
        try:
            # Create a direct connection to the notifications database
            db_path = os.path.join('/home/cpx003/vst_gm_control_panel/vst_gm_control_panel/data/db', 'notifications.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # First, create the table if it doesn't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS sys
            (id INTEGER PRIMARY KEY, datetime TEXT, notification TEXT);
            ''')
            
            # Add the notification directly
            timestamp = datetime.now().isoformat()
            cursor.execute('INSERT INTO sys (datetime, notification) VALUES (?, ?)', 
                          (timestamp, message))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error logging notification: {e}")

    def set_sequence(self, sequence):
        """
        Set the pins for the specified sequence - simplified version based on working 0.4.10.
        """
        self.purge_check = False
        try:
            for i, (mode, delay) in enumerate(sequence):
                # Use safe logging method that creates a fresh connection
                self.log_notification_safely(f'Starting {mode} mode.')
                
                if self._stop_cycle_event.is_set():
                    break
                    
                self.process_mode(mode)
                
                if mode == 'purge':
                    if self.purge_check is False:
                        self.start_purge_timer()
                else:
                    if self.purge_timer is not None:
                        self.cancel_purge_timer()
                        
                self.sleep_with_check(delay)
                
        except KeyboardInterrupt:
            self._end_sequence()
        except Exception as e:
            self._end_sequence()
        finally:
            self._end_sequence()

    def _load_step_progress(self):
        """Load current step progress from file."""
        try:
            import json
            import os
            if os.path.exists(self._step_progress_file):
                with open(self._step_progress_file, 'r') as f:
                    progress_data = json.load(f)
                    self._current_step = progress_data.get('current_step', 0)
                    self._step_start_time = progress_data.get('step_start_time', time.time())
                    return True
        except Exception as e:
            self.log_notification_safely(f'Error loading step progress: {e}')
        return False

    def process_mode(self, mode):
        """
        Purpose:
        - Run the specified mode in a new process - simplified version based on working 0.4.10.
        """
        self._stop_mode_event.clear()
        self.mode_process = multiprocessing.Process(target=self.set_mode, args=(mode,))
        self.mode_process.start()


    def process_sequence(self, sequence, is_manual=False):
        """
        Run the specified sequence in a new process - simplified version based on working 0.4.10.
        """
        try:
            # Check if we should stop
            if not sequence:
                return

            # Clear stop events
            self._stop_cycle_event.clear()
            self._stop_mode_event.clear()

            # Start the sequence
            self.cycle_process = multiprocessing.Process(target=self.set_sequence, args=(sequence,))
            self.cycle_process.start()

        except Exception as e:
            self.log_notification_safely(f'Failed to start cycle process: {e}')
            # Ensure proper cleanup
            self._end_sequence()
            self.set_rest()

    def _end_sequence(self, is_manual=False):
        '''
        End the current sequence - simplified version based on working 0.4.10.
        '''
        # Set rest mode first (hardware operation - safe in child process)
        self.set_mode('rest')
        self.mode = 'rest'
        
        # Check if we're in a child process - skip Kivy operations if so
        # Kivy Clock and app operations keep child processes alive indefinitely
        current_pid = os.getpid()
        is_child = hasattr(self, '_hardware_init_pid') and current_pid != self._hardware_init_pid
        
        if is_child:
            # In child process: only do hardware cleanup, then exit
            # Parent process will detect cycle completion via is_alive() check
            Logger.debug(f'IOManager: Child process {current_pid} ending sequence, skipping Kivy ops')
            return
        
        # Parent process: do full cleanup including Kivy operations
        self.cycle_process = None
        
        # Reset states - no GM fault monitoring for manual mode
        self.app.toggle_run_cycle_state(False)
        if self._mcp_lock.locked():
            self._mcp_lock.release()
        
        # Only stop GM fault monitoring if it was started for non-manual cycles
        if not is_manual:
            self.stop_gm_fault_check()

    def get_mode(self):
        """
        Return the current mode using ultra-fast memory-mapped file (replaces database).
        """
        return self.mode_manager.get_mode()


    def get_values(self):
        """
        Return the names of the pins that are True based on current mode.
        Uses ModeManager instead of I2C reads to avoid blocking the UI.
        """
        modes = {
            'run': {'motor': True, 'v1': True, 'v2': False, 'v5': True},
            'rest': {'motor': False, 'v1': False, 'v2': False, 'v5': False},
            'purge': {'motor': True, 'v1': False, 'v2': True, 'v5': False},
            'burp': {'motor': False, 'v1': False, 'v2': False, 'v5': True},
            'bleed': {'motor': False, 'v1': False, 'v2': True, 'v5': True},
            'leak': {'motor': False, 'v1': True, 'v2': True, 'v5': True}
        }
        mode = self.mode_manager.get_mode()
        if mode is not None and mode in modes:
            active_pins = [pin for pin, value in modes[mode].items() if value]
            if active_pins:
                return ', '.join(active_pins)
        return 'None'

    def check_current_during_purge(self):
        """
        Check the current during purge mode.
        """
        current = self.get_current()
        if float(current) < 2.0:
            # Use safe logging method that creates a fresh connection
            self.log_notification_safely(f'Current failure detected during purge: {current} A')
            self.log_current_failure(current)
        self.purge_timer = None

    def start_purge_timer(self):
        """
        Start the purge timer when mode changes to purge.
        """
        self.purge_check = True
        if self.purge_timer is not None:
            self.purge_timer.cancel() 
        self.purge_timer = threading.Timer(35, self.check_current_during_purge)
        self.purge_timer.start()

    def cancel_purge_timer(self):
        """
        Cancel the purge timer when mode changes from purge.
        """
        self.purge_timer.cancel()
        self.purge_timer = None

    def run_cycle(self, is_manual=False):
        """
        Purpose:
        - Set the sequence for a run cycle.
        
        Args:
            is_manual (bool): Whether this is part of a manual mode cycle
        """
        # Explicit safety check - never allow run cycles on protected administrative screens
        if hasattr(self.app, 'sm') and self.app.sm.current in [
            'Admin',
            'ClearAlarms',
            'CodeEntry',
            'Contractor',
            'FunctionalityTest',
            'LeakTest',
            'Maintenance',
            'OverfillOverride',
            'Shutdown',
            'System',
            'SystemConfig'
        ]:
            # Ensure we're in rest mode
            self.set_rest()
            return

        # Should be exactly 7 minutes and 47 seconds.
        run_time, rest_time, purge_time, burp_time = self.get_mode_times('normal')

        if self.cycle_process is not None and self.cycle_process.is_alive():
            return

        if not self.app.manual_mode:
            run_cycle_count = self.app.gm_db.get_setting('run_cycle_count')
            if run_cycle_count is None:
                run_cycle_count = 1
            else:
                run_cycle_count = int(run_cycle_count) + 1
            self.app.gm_db.add_setting('run_cycle_count', run_cycle_count)

        self.app.toggle_run_cycle_state(True)

        try:
            sequence = [
                ('run', run_time), ('rest', 2),
                ('purge', purge_time), ('burp', burp_time),
                ('purge', purge_time), ('burp', burp_time),
                ('purge', purge_time), ('burp', burp_time),
                ('purge', purge_time), ('burp', burp_time),
                ('purge', purge_time), ('burp', burp_time),
                ('purge', purge_time), ('burp', burp_time),
                ('rest', 15)  # Always 15 second rest at end before next cycle
                ]
            self.process_sequence(sequence)

        finally:
            # Save the current time as the end time of the last run cycle
            current_time = datetime.now().isoformat()
            self.app.gm_db.add_setting('last_run_cycle', current_time)

    def manual_mode(self):
        """
        Start a single manual cycle - simplified version based on working 0.4.10 implementation.
        No GM fault monitoring or diagnostic bypasses - just simple single cycle execution.
        Each call performs ONE complete cycle (run + 6 purge/burp pairs + rest).
        """
        run_time, rest_time, purge_time, burp_time = self.get_mode_times()

        if self.cycle_process is not None and self.cycle_process.is_alive():
            return

        self.app.toggle_manual_mode_state(True)

        # Single cycle: 1 run + 6 purge/burp pairs + final rest
        sequence = [
            ('run', run_time), ('rest', 2),
            ('purge', purge_time), ('burp', burp_time),
            ('purge', purge_time), ('burp', burp_time),
            ('purge', purge_time), ('burp', burp_time),
            ('purge', purge_time), ('burp', burp_time),
            ('purge', purge_time), ('burp', burp_time),
            ('purge', purge_time), ('burp', burp_time),
            ('rest', 15)  # Final rest at end of cycle
        ]
        self.process_sequence(sequence)

        self.log_notification_safely('Manual cycle completed.')

    def test_purge(self, rest_time=None):
        """
        Execute a single test purge cycle.
        
        Args:
            rest_time: Override the default rest time (seconds)
        """
        # Explicit safety check - never allow test runs on protected administrative screens
        if hasattr(self.app, 'sm') and self.app.sm.current in [
            'ClearAlarms',
            'CodeEntry',
            'Contractor',
            'FunctionalityTest',
            'LeakTest',
            'Maintenance',
            'ManualMode',
            'OverfillOverride',
            'Shutdown'
        ]:
            # Ensure we're in rest mode
            self.set_rest()
            return
        
        # Check if a cycle is already running
        if self.cycle_process is not None and self.cycle_process.is_alive():
            self.log_notification_safely('Test purge ignored - cycle already in progress')
            return
            
        # Get purge time from the test method (uses 30-second test_purge_time)
        _, _, purge_time, _ = self.get_mode_times('test')
        
        # Use explicitly passed rest_time or get from app
        if rest_time is not None:
            test_rest_time = rest_time
        else:
            try:
                test_rest_time = int(self.app.test_rest_time)
            except (ValueError, TypeError, AttributeError) as e:
                test_rest_time = 5  # Default
                self.log_notification_safely(f'Error getting rest_time: {e}, using default: {test_rest_time}')
        
        # Create a simple purge sequence
        sequence = [
            ('purge', purge_time),
            ('rest', test_rest_time)
        ]
        
        # Start the sequence in a separate process
        self._stop_cycle_event.clear()  # Reset the stop event
        self.process_sequence(sequence)
    
    def test_run(self, run_time=None, rest_time=None):
        """
        Execute a single test run cycle with configurable duration.
        
        Args:
            run_time: Override the default run time (seconds)
            rest_time: Override the default rest time (seconds)
        """
        # Explicit safety check - never allow test runs on protected administrative screens
        if hasattr(self.app, 'sm') and self.app.sm.current in [
            'ClearAlarms',
            'CodeEntry',
            'Contractor',
            'FunctionalityTest',
            'LeakTest',
            'Maintenance',
            'ManualMode',
            'OverfillOverride',
            'Shutdown'
        ]:
            # Ensure we're in rest mode
            self.set_rest()
            return
        
        # Add debounce mechanism to prevent rapid test run starts
        current_time = time.time()
        last_test_start = getattr(self, 'last_test_start_time', 0)
        debounce_period = 5  # 5 seconds debounce
        
        if current_time - last_test_start < debounce_period:
            self.log_notification_safely(
                f'Test run debounced - ignoring request (last run was {current_time - last_test_start:.1f}s ago)'
            )
            return
        
        # Store the start time for future debounce checks
        self.last_test_start_time = current_time
        
        # Check if a cycle is already running
        if self.cycle_process is not None and self.cycle_process.is_alive():
            self.log_notification_safely('Test run ignored - cycle already in progress')
            return

        # Use explicitly passed parameters if provided, otherwise fall back to app values
        if run_time is not None:
            test_run_time = run_time
        else:
            # Get run_time - this is a StringProperty in the app
            try:
                test_run_time = int(self.app.test_cycle_run_time)
            except (ValueError, TypeError, AttributeError) as e:
                # Handle conversion errors
                test_run_time = 15  # Default
                self.log_notification_safely(f'Error getting run_time: {e}, using default: {test_run_time}')
        
        if rest_time is not None:
            test_rest_time = rest_time
        else:
            # Get rest_time - this is a StringProperty in the app
            try:
                test_rest_time = int(self.app.test_rest_time)
            except (ValueError, TypeError, AttributeError) as e:
                # Handle conversion errors
                test_rest_time = 5  # Default
                self.log_notification_safely(f'Error getting rest_time: {e}, using default: {test_rest_time}')
        
        # Create a simple run sequence with the specified timing values
        sequence = [
            ('run', test_run_time),
            ('rest', test_rest_time)
        ]
        
        # Start the sequence in a separate process
        self._stop_cycle_event.clear()  # Reset the stop event
        self.process_sequence(sequence)

    def functionality_test(self):
        """
        Set the sequence for a functionality test.
        """
        # Explicit safety check - never allow functionality tests on protected administrative screens
        if hasattr(self.app, 'sm') and self.app.sm.current in [
            'Admin',
            'ClearAlarms',
            'CodeEntry',
            'Contractor',
            'LeakTest',
            'Main',
            'Faults',
            'TimeEntry',
            'Maintenance',
            'ManualMode',
            'OverfillOverride',
            'Shutdown',
            'System',
            'SystemConfig'
        ]:
            # Ensure we're in rest mode
            self.set_rest()
            return
            
        if self.app.debug:
            run_time = 6
            purge_time = 6
        else:
            run_time = 60
            purge_time = 60

        if self.cycle_process is not None and self.cycle_process.is_alive():
            return

        try:
            sequence = [('run', run_time), ('purge', purge_time)]
            for _ in range(9):
                sequence.append(('run', run_time))
                sequence.append(('purge', purge_time))
            self.process_sequence(sequence)
        except Exception as e:
            self._log('error', f'Error in functionality test: {e}')

    def canister_clean(self):
        """
        Set the sequence for a canister clean cycle.
        """
        # Explicit safety check - never allow canister clean on protected administrative screens
        # Note: CanisterClean screen is allowed (not in blocked list) so canister clean can run on its own screen
        if hasattr(self.app, 'sm') and self.app.sm.current in [
            'Admin',
            'ClearAlarms',
            'CodeEntry',
            'Contractor',
            'FunctionalityTest',
            'LeakTest',
            'Main',
            'Faults',
            'TimeEntry',
            'Maintenance',
            'ManualMode',
            'OverfillOverride',
            'Shutdown',
            'System',
            'SystemConfig'
        ]:
            # Ensure we're in rest mode
            self.set_rest()
            return
            
        if self.app.debug:
            clean_time = 60  # 1 minute for debug
        else:
            clean_time = 7200  # 2 hours = 7200 seconds

        self.process_sequence([
            ('run', clean_time)  # Motor ON, V1 ON, V2 OFF, V5 ON
        ])

    def efficiency_test_fill_run(self):
        """
        Set the sequence for an efficiency test fill/run cycle.
        """
        # Explicit safety check - never allow efficiency test on protected administrative screens
        if hasattr(self.app, 'sm') and self.app.sm.current in [
            'Admin',
            'ClearAlarms',
            'CodeEntry',
            'Contractor',
            'FunctionalityTest',
            'LeakTest',
            'Main',
            'Faults',
            'TimeEntry',
            'Maintenance',
            'ManualMode',
            'OverfillOverride',
            'Shutdown',
            'System',
            'SystemConfig'
        ]:
            # Ensure we're in rest mode
            self.set_rest()
            return

        if self.app.debug:
            fill_run_time = 30  # 30 seconds for debug
        else:
            fill_run_time = 120  # 2 minutes = 120 seconds

        self.process_sequence([
            ('run', fill_run_time)  # Motor ON, V1 ON, V2 OFF, V5 ON
        ])

    def efficiency_test_purge(self):
        """
        Set the sequence for an efficiency test purge cycle.
        """
        # Explicit safety check - never allow efficiency test on protected administrative screens
        if hasattr(self.app, 'sm') and self.app.sm.current in [
            'Admin',
            'ClearAlarms',
            'CodeEntry',
            'Contractor',
            'FunctionalityTest',
            'LeakTest',
            'Main',
            'Faults',
            'TimeEntry',
            'Maintenance',
            'ManualMode',
            'OverfillOverride',
            'Shutdown',
            'System',
            'SystemConfig'
        ]:
            # Ensure we're in rest mode
            self.set_rest()
            return

        # Get standard purge timing
        _, _, purge_time, burp_time = self.get_mode_times()

        # Create sequence for 6 purge/burp cycles
        sequence = []
        for _ in range(6):
            sequence.extend([
                ('purge', purge_time),
                ('burp', burp_time)
            ])
        sequence.append(('rest', 2))  # End with rest mode

        self.process_sequence(sequence)

    def leak_test(self):
        """
        Set the sequence for a leak test.
        """
        # Explicit safety check - never allow leak tests on protected administrative screens
        if hasattr(self.app, 'sm') and self.app.sm.current in [
            'Admin',
            'ClearAlarms',
            'CodeEntry',
            'Contractor',
            'FunctionalityTest',
            'Main',
            'Faults',
            'TimeEntry',
            'Maintenance',
            'ManualMode',
            'OverfillOverride',
            'Shutdown',
            'System',
            'SystemConfig'
        ]:
            # Ensure we're in rest mode
            self.set_rest()
            return
            
        if self.app.debug:
            leak_time = 60 * 3
        else:
            leak_time = 60 * 30

        self.process_sequence([
            ('leak', leak_time)
        ])

    def stop_cycle(self):
        """
        Stop the current cycle with proper cleanup and robust null safety.
        """
        # Set stop events first
        self._stop_cycle_event.set()
        self._stop_mode_event.set()
        
        # Stop mode process first if it exists - with robust null safety
        mode_proc = getattr(self, 'mode_process', None)
        if mode_proc is not None:
            try:
                if hasattr(mode_proc, 'is_alive') and mode_proc.is_alive():
                    if hasattr(mode_proc, 'terminate'):
                        mode_proc.terminate()
                    if hasattr(mode_proc, 'join'):
                        mode_proc.join(timeout=0.5)
            except Exception as e:
                self.log_notification_safely(f'Error stopping mode process: {e}')
            finally:
                self.mode_process = None

        # Then stop cycle process if it exists - with robust null safety
        cycle_proc = getattr(self, 'cycle_process', None)
        if cycle_proc is not None:
            try:
                if hasattr(cycle_proc, 'is_alive') and cycle_proc.is_alive():
                    if hasattr(cycle_proc, 'terminate'):
                        cycle_proc.terminate()
                    if hasattr(cycle_proc, 'join'):
                        cycle_proc.join(timeout=0.5)
            except Exception as e:
                self.log_notification_safely(f'Error stopping cycle process: {e}')
            finally:
                self.cycle_process = None

        # Reset state
        self.app.toggle_run_cycle_state(False)
        self.app.toggle_manual_mode(False)
        if self._mcp_lock.locked():
            self._mcp_lock.release()
        
        # Ensure pins are in safe state
        try:
            self.set_rest()
        except Exception as e:
            self.log_notification_safely(f'Error setting rest state: {e}')

    def stop_mode(self):
        """
        Stop the current mode with proper cleanup.
        """
        try:
            # Capture reference to avoid race condition
            mode_proc = getattr(self, 'mode_process', None)
            if mode_proc and mode_proc.is_alive():
                # Set stop event and wait briefly
                self._stop_mode_event.set()
                time.sleep(0.1)  # Give process a chance to stop gracefully
                
                # Terminate if still running
                if mode_proc.is_alive():
                    mode_proc.terminate()
                    mode_proc.join(timeout=0.5)
                    
                    # Kill as last resort
                    if mode_proc.is_alive():
                        os.kill(mode_proc.pid, signal.SIGKILL)
                
            # Clear reference
            self.mode_process = None
                
            # Always ensure flags are cleared
            self._stop_mode_event.set()
            if self._mcp_lock.locked():
                self._mcp_lock.release()
            
        except Exception as e:
            self._log('error', f'Error stopping mode: {e}')
            # Ensure references are cleared even on error
            self.mode_process = None
            if self._mcp_lock.locked():
                self._mcp_lock.release()


    def _collect_adc_readings(self):
        '''
        Collect 60 ADC readings with MCP priority - aborts immediately if MCP needs bus access
        '''
        current_readings_batch = []
        failed_readings = 0
        for i in range(60):
            # Check BEFORE each read to give MCP immediate priority
            if self._mcp_lock.locked():
                Logger.debug(f'MotorCurrent: MCP needs priority, aborting ADC collection at {i}/60 samples')
                break
                
            try:
                value2 = self._channel2.value
                value3 = self._channel3.value
                if value2 is not None and value3 is not None:
                    difference = abs(value2 - value3)
                    current_readings_batch.append(difference)
                else:
                    failed_readings += 1
            except Exception as e:
                failed_readings += 1
                
        if failed_readings > 0:
            Logger.debug(f'MotorCurrent: ADC collection completed: {len(current_readings_batch)}/60 successful')
        return current_readings_batch

    def _handle_current_failure(self):
        '''
        Handle current reading failure by incrementing failure count
        and returning cached value if available, otherwise error value.
        '''
        self.current_failure_count += 1
        self._log('debug', f'Current reading failure #{self.current_failure_count}/{self.max_current_failure_count}')
        Logger.debug(f'MotorCurrent: ERROR RETRY - Current reading failure #{self.current_failure_count}/{self.max_current_failure_count}')
        
        # If we haven't exceeded max failures AND we have a good last value, use it
        if (self.current_failure_count <= self.max_current_failure_count and
            hasattr(self, 'last_current_value') and
            self.last_current_value != '-99.9'):
            self._log('debug', f'Using cached current value: {self.last_current_value}A (failure {self.current_failure_count}/{self.max_current_failure_count})')
            Logger.debug(f'MotorCurrent: ERROR RETRY - Using cached current value: {self.last_current_value}A (failure {self.current_failure_count}/{self.max_current_failure_count})')
            return self.last_current_value
        # Too many consecutive failures, return error value
        self._log('warning', f'Max current failures exceeded ({self.current_failure_count}/{self.max_current_failure_count}), returning error value')
        Logger.debug(f'MotorCurrent: ERROR RETRY - Max current failures exceeded ({self.current_failure_count}/{self.max_current_failure_count}), returning error value')
        return '-99.9'


    def _process_current_readings(self, readings):
        '''
        Process current readings by removing outliers and finding maximum value.
        Returns the maximum current reading after outlier removal.
        '''
        # Add all readings to the main buffer (60 samples = 1 second of data)
        for reading in readings:
            self.current_readings.append(reading)

        # Convert deque to list for processing
        current_readings = list(self.current_readings)

        # Remove min/max outliers
        if len(current_readings) <= 2:  # Not enough data to remove outliers
            max_current = max(current_readings)
        else:
            sorted_readings = sorted(current_readings)
            trimmed_readings = sorted_readings[1:-1]
            max_current = max(trimmed_readings)

        return max_current

    def _calculate_current_value(self, max_reading):
        '''
        Calculate current value from ADC reading using calibration mapping.
        Returns the calculated current value as float.
        '''
        return self.map_value(max_reading, 1248.0, 4640.0, 2.1, 8.0)

    def _format_and_cache_result(self, current_value):
        '''
        Format current value to 2 decimal places, cache result, and reset failure count.
        Returns formatted current value as string.
        '''
        result = f'{current_value:.2f}'
        if self.current_failure_count > 0:
            self._log('debug', f'Current reading recovered, resetting failure count from {self.current_failure_count} to 0')
            Logger.debug(f'MotorCurrent: ERROR RETRY - Current reading recovered, resetting failure count from {self.current_failure_count} to 0')
        self.current_failure_count = 0
        self.last_current_value = result
        return result

    def get_current(self):
        '''
        Get the current reading from the sensor.
        Returns error value in mock mode.
        '''
        # Return error value in mock mode to indicate hardware disconnection
        if not self.hardware_available:
            return "-99.9"
            
        try:
            # Collect ADC readings
            readings = self._collect_adc_readings()
            
            if not readings:
                self._log('debug', 'No ADC readings collected for current measurement')
                Logger.debug('MotorCurrent: ERROR RETRY - No ADC readings collected for current measurement')
                return self._handle_current_failure()

            # Process readings to get maximum value
            max_reading = self._process_current_readings(readings)
            
            # Check if we have valid readings after processing
            if len(self.current_readings) == 0:
                self._log('debug', 'No valid current readings after processing')
                Logger.debug('MotorCurrent: ERROR RETRY - No valid current readings after processing')
                return self._handle_current_failure()
            
            # Calculate current value
            current_value = self._calculate_current_value(max_reading)
            
            # Format and cache result
            return self._format_and_cache_result(current_value)
            
        except IOError as e:
            self._log('error', f'Error reading current from ADC: {e}')
            Logger.debug(f'MotorCurrent: ERROR RETRY - IOError in get_current(): {e}')
            return self._handle_current_failure()


    def log_current_failure(self, current_value):
        """
        Log failures in DB.
        """
        try:
            # Connect directly to the alarms database
            db_path = os.path.join('/home/cpx003/vst_gm_control_panel/vst_gm_control_panel/data/db', 'app.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create the table if it doesn't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS alarms
            (id INTEGER PRIMARY KEY, key TEXT UNIQUE, value TEXT);
            ''')
            
            # Get current failure count
            cursor.execute('SELECT value FROM alarms WHERE key = ?', ('vac_pump_failure_count',))
            result = cursor.fetchone()
            
            # Calculate new failure count
            if result and result[0]:
                failure_count = int(result[0]) + 1
            else:
                failure_count = 1
                
            # Save new failure count
            cursor.execute('INSERT OR REPLACE INTO alarms (key, value) VALUES (?, ?)',
                          ('vac_pump_failure_count', str(failure_count)))
            conn.commit()
            conn.close()
            
            self.log_notification_safely(f"Updated vac_pump_failure_count to {failure_count}")
        except Exception as e:
            self.log_notification_safely(f"Error updating vac_pump_failure_count: {e}")

    def set_shutdown_relay(self, state: bool, alarm_type: str = None):
        """
        Set the shutdown relay to a specific state with profile-aware control.
        
        Args:
            state: True to turn on the relay, False to turn it off
            alarm_type: Type of alarm requesting the change (for profile checking)
        """
        try:
            # Check if this alarm type is allowed to control the shutdown relay for current profile
            if not state and alarm_type and not self._should_alarm_control_relay(alarm_type):
                # This alarm type is not allowed to turn off the relay for this profile
                self._log('debug', f'Shutdown relay control blocked for {alarm_type} on profile {self.app.profile}')
                return
            
            # Only log if the state is actually changing
            if self._last_shutdown_relay_state != state:
                self.pins['shutdown'].value = state
                Logger.debug(f'Mode: Shutdown relay - {state}')
                self._last_shutdown_relay_state = state  # Update tracked state
            else:
                # State hasn't changed, just set it silently
                self.pins['shutdown'].value = state
            
            # =================================================================
            # REV 10 PATCH: Send shutdown command to ESP32 via serial.
            # When state=False (shutdown activated), send {"mode":"shutdown"}
            # which is the ONLY way to set ESP32 DISP_SHUTDN (GPIO13) LOW.
            # When state=True (normal), ESP32 already starts with GPIO13 HIGH
            # on every boot, so we send mode 0 (rest) to confirm safe state.
            # =================================================================
            try:
                serial_mgr = self.app.serial_manager if hasattr(self.app, 'serial_manager') else None
                if serial_mgr:
                    if not state:
                        # Shutdown activated — tell ESP32 to pull DISP_SHUTDN LOW
                        serial_mgr.send_shutdown_command()
                    # Note: state=True (re-enable) requires ESP32 reboot to reset GPIO13 HIGH.
                    # ESP32 DISP_SHUTDN is only set LOW by explicit command, starts HIGH on boot.
            except Exception as serial_e:
                self._log('error', f'Error sending shutdown via serial: {serial_e}')
            
        except Exception as e:
            self._log('error', f'Error setting shutdown relay: {e}')
    
    def _should_alarm_control_relay(self, alarm_type: str) -> bool:
        """
        Check if the given alarm type should be allowed to control the shutdown relay
        based on the current profile.
        
        Args:
            alarm_type: The type of alarm ('pressure_sensor', 'vac_pump', 'gm_fault', '72_hour_shutdown')
            
        Returns:
            True if this alarm type can control the relay, False otherwise
        """
        try:
            current_profile = getattr(self.app, 'profile', 'CS8')
            
            # 72-hour shutdown can always control the relay (all profiles)
            if alarm_type == '72_hour_shutdown':
                return True
            
            # For CS9 profile, these specific alarms can control the relay
            if current_profile == 'CS9':
                allowed_alarms = ['pressure_sensor', 'vac_pump', 'gm_fault', '72_hour_shutdown']
                return alarm_type in allowed_alarms
            
            # For all other profiles (CS2, CS8, CS12), only 72-hour shutdown can control the relay
            return alarm_type == '72_hour_shutdown'
            
        except Exception as e:
            self._log('error', f'Error checking alarm relay control permission: {e}')
            # Default to allowing control to maintain safety (fail-safe)
            return True
    
    def re_evaluate_shutdown_relay_for_profile_change(self):
        """
        Re-evaluate shutdown relay state when profile changes.
        
        This method checks all currently active alarms and determines if any of them
        should control the shutdown relay under the new profile settings.
        """
        try:
            profile = self.app.profile
            self._log('info', f'IOManager: Re-evaluating shutdown relay for profile change to {profile}')
            
            # CRITICAL: Check if system is in shutdown mode FIRST
            if hasattr(self.app, 'shutdown') and self.app.shutdown:
                self._log('info', f'IOManager: System in shutdown mode, keeping relay disabled')
                self.set_shutdown_relay(False, '72_hour_shutdown')
                return
            
            # Get currently active alarms
            active_alarms = []
            if hasattr(self.app, 'alarm_manager'):
                active_alarms = self.app.alarm_manager.get_active_alarms()
            
            # Check if any active alarm should control the relay under new profile
            should_disable_relay = False
            controlling_alarm = None
            
            for alarm_name in active_alarms:
                if self._should_alarm_control_relay(alarm_name):
                    should_disable_relay = True
                    controlling_alarm = alarm_name
                    break
            
            # Update relay state based on evaluation
            if should_disable_relay:
                self.set_shutdown_relay(False, controlling_alarm)
                self._log('info', f'IOManager: Profile change - shutdown relay disabled due to {controlling_alarm} alarm')
            else:
                # Only enable if no controlling alarms are active AND not in shutdown mode
                self.set_shutdown_relay(True, 'profile_change')
                self._log('info', f'IOManager: Profile change - shutdown relay enabled (no controlling alarms for {profile})')
                
        except Exception as e:
            self._log('error', f'IOManager: Error re-evaluating shutdown relay for profile change: {e}')
            
    def shutdown(self):
        """
        Shutdown the system.
        """
        self.set_rest()
        self.set_shutdown_relay(False, '72_hour_shutdown')

    def buzzer(self, freq, dur):
        """
        Repeatedly activate the buzzer until the stop event is set, with cleanup for interrupts.
        """
        try:
            while not self.buzzer_stop_event.is_set():
                # Check if pi is still available before each cycle
                if self.pi is None:
                    break
                self.pi.set_PWM_frequency(self.buzzer_pin, freq)
                self.pi.set_PWM_dutycycle(self.buzzer_pin, 10)  # Volume (reduced from 15)
                time.sleep(dur)  # Duration of each beep
                if self.pi is None:
                    break
                self.pi.set_PWM_dutycycle(self.buzzer_pin, 0)  # Silence between beeps
                time.sleep(dur)  # Interval between beeps
        except AttributeError:
            pass  # pi was set to None during cleanup
        finally:
            # Ensure the buzzer is turned off if the loop is interrupted
            if self.pi is not None:
                try:
                    self.pi.set_PWM_dutycycle(self.buzzer_pin, 0)
                except (AttributeError, Exception):
                    pass  # pi was set to None or other error during cleanup

    def start_buzzer(self, freq, dur):
        """
        Start the buzzer in a separate thread.
        """
        self.buzzer_stop_event.clear()
        self.buzzer_thread = threading.Thread(target=self.buzzer, args=(freq, dur))
        self.buzzer_thread.daemon = True
        self.buzzer_thread.start()

    def stop_buzzer(self):
        """
        Stop the buzzer.
        """
        self.buzzer_stop_event.set()
        if hasattr(self, 'buzzer_thread') and self.buzzer_thread.is_alive():
            self.buzzer_thread.join(timeout=1.0)
        
        # Add check to ensure pi is not None before trying to use it
        if hasattr(self, 'pi') and self.pi is not None:
            try:
                self.pi.set_PWM_dutycycle(self.buzzer_pin, 0)  # Ensure buzzer is off
            except Exception as e:
                self._log('error', f'Error stopping buzzer: {e}')

    def reset_i2c(self):
        """
        Reset the I2C bus with retries and proper cleanup.
        """
        max_attempts = 3
        
        def init_i2c_devices():
            # Initialize I2C bus with lower frequency for stability
            # self.i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)
            self.i2c = busio.I2C(board.SCL, board.SDA)
            # Initialize ADC
            self._adc = ADS.ADS1115(self.i2c)
            self._channel2 = AnalogIn(self._adc, ADS.P2)
            self._channel3 = AnalogIn(self._adc, ADS.P3)
            # Initialize MCP
            self._mcp = MCP23017(self.i2c)
            # Reinitialize pressure sensor with new ADC
            self.pressure_sensor = PressureSensor(self._adc, self.app)
            return True

        for attempt in range(max_attempts):
            try:
                # Clean up existing I2C resources
                if hasattr(self, 'i2c') and self.i2c is not None:
                    try:
                        self.i2c.deinit()
                    except Exception:
                        pass
                
                # Brief delay before reinitializing
                time.sleep(0.1)
                
                # Initialize devices
                if init_i2c_devices():
                    # Reconfigure pins
                    self.setup_pins()
                    return True
                    
            except Exception as e:
                self._log('error', f'Error during I2C reset attempt {attempt + 1}: {e}')
                if attempt == max_attempts - 1:
                    pass
                time.sleep(0.2 * (attempt + 1))  # Increasing delay between attempts
        
        return False

    def check_gm_fault(self, *args):
        '''Check motor current for GM fault conditions - CS9 PROFILE ONLY.
        
        SIMPLIFIED Logic:
        1. High current for 2+ seconds: Increment counter and pause/resume
        2. Low current for 2+ seconds: Reset counter to 0
        3. At counter = 3: Trigger vac pump alarm
        
        Note: Uses cached current value from main app (updated every 3s) to avoid
        redundant ADC reads while still checking every 2s for safety.
        '''
        # Double-check profile in case it changed during operation
        if self.app.profile != 'CS9':
            self._log('info', f'GM Fault: Profile changed to {self.app.profile}, stopping monitoring')
            self.stop_gm_fault_check()
            return
            
        # Check if vac pump alarm is already active - if so, stop monitoring
        if self._is_vac_pump_alarm_active():
            self._log('info', 'GM Fault: Vac pump alarm active, stopping monitoring')
            self.stop_gm_fault_check()
            return
            
        # Skip monitoring during rest period to prevent race conditions
        if self.gm_fault_in_rest_period:
            return
            
        try:
            # Use cached current value to avoid blocking UI thread
            # Background sensor thread updates this value every ~0.2 seconds
            current_str = self.get_cached_current()
            try:
                current = float(current_str)
            except (ValueError, TypeError):
                current = 0.0
            current_time = time.time()
            
            if current >= 20.0:
                # Current is HIGH
                if not self.high_current_detected:
                    # First high reading - start 2-second confirmation timer
                    self.high_current_detected = True
                    self.high_current_start_time = current_time
                    self._log('info', f'GM Fault: High current detected ({current:.2f}A), starting confirmation')
                else:
                    # Check if we've been high for 2+ seconds
                    time_in_high_current = current_time - self.high_current_start_time
                    
                    if time_in_high_current >= 2.0:
                        # High current confirmed for 2+ seconds - increment counter and handle
                        self.gm_fault_count += 1
                        self._log('info', f'GM Fault: High current {current:.2f}A confirmed for 2+ seconds. Counter: {self.gm_fault_count}')
                        
                        # Reset high current detection to prevent multiple increments
                        self.high_current_detected = False
                        self.high_current_start_time = 0
                        
                        # Check if we need to trigger vac pump alarm at count 3
                        if self.gm_fault_count >= 3:
                            # Stop the cycle
                            self.stop_cycle()
                            # Set vac pump alarm
                            self._set_vac_pump_alarm()
                            # Turn OFF shutdown relay for vac pump alarm (CS9 profile only)
                            self.set_shutdown_relay(False, 'vac_pump')
                            self._log('info', 'GM Fault: Triggered vac pump alarm and disabled shutdown relay (3 faults)')
                            # Stop monitoring GM faults since we've triggered the alarm
                            self.stop_gm_fault_check()
                            return
                        else:
                            # Count is 1 or 2 - pause cycle, rest for 2 seconds, then resume
                            # Shutdown relay will be turned OFF during pause
                            self._log('info', f'GM Fault: Count {self.gm_fault_count} - initiating pause/resume sequence')
                            self._handle_gm_fault_pause_resume()
                
                # Reset low current detection since we're high again
                self.low_current_detected = False
                self.low_current_start_time = 0
                
            else:
                # Current is LOW
                if not self.low_current_detected:
                    # First low reading - start 2-second confirmation timer (only log if we had a previous high state)
                    self.low_current_detected = True
                    self.low_current_start_time = current_time
                    if self.gm_fault_count > 0:
                        self._log('info', f'GM Fault: Low current detected ({current}A), starting confirmation')
                else:
                    # Check if we've been low for 2+ seconds
                    time_in_low_current = current_time - self.low_current_start_time
                    if time_in_low_current >= 2.0:
                        # Reset everything - confirmed low for 2+ seconds
                        if self.gm_fault_count > 0:
                            self._log('info', 'GM Fault: Low current confirmed for 2+ seconds. Counter reset to 0')
                            self.gm_fault_count = 0
                        self.high_current_detected = False
                        self.low_current_detected = False
                        self.low_current_start_time = 0
                        self.high_current_start_time = 0
                
                # Reset high current detection since we're low
                self.high_current_detected = False
                self.high_current_start_time = 0
                
        except (ValueError, TypeError) as e:
            self._log('warning', f'GM Fault Check: Error reading current: {e}')
            # On error, assume safe state (low current)
            self.high_current_detected = False
            self.low_current_detected = False
            self.low_current_start_time = 0
            self.high_current_start_time = 0

    def start_gm_fault_check(self, reset_counter=True, reset_timing_state=True):
        '''Start periodic GM fault checking using single-threaded state machine - CS9 PROFILE ONLY.
        
        Args:
            reset_counter (bool): Whether to reset the GM fault counter. Set to False when resuming after pause.
            reset_timing_state (bool): Whether to reset timing state flags. Set to False when resuming after pause.
        '''
        # Only start GM fault checking for CS9 profile
        if self.app.profile != 'CS9':
            return
            
        if reset_counter:
            self.gm_fault_count = 0  # Reset counter at start
            self._log('info', 'GM Fault: Starting monitoring (counter reset)')
        else:
            self._log('info', f'GM Fault: Resuming monitoring (counter: {self.gm_fault_count})')
            
        if reset_timing_state:
            self.high_current_detected = False  # Reset high current state flag
            self.high_current_start_time = 0  # Reset high current timer
            self.low_current_detected = False  # Reset low current state flag
            self.low_current_start_time = 0  # Reset low current timer
            
        self._gm_fault_check_event = None  # Initialize event reference
        self._gm_fault_check_event = Clock.schedule_interval(self.check_gm_fault, 2)  # Check every 2 seconds

    def stop_gm_fault_check(self):
        '''Stop periodic GM fault checking and clean up rest period callbacks.'''
        
        # Stop the main GM fault monitoring
        if hasattr(self, '_gm_fault_check_event') and self._gm_fault_check_event:
            self._gm_fault_check_event.cancel()
            self._gm_fault_check_event = None
        else:
            # Fallback to unschedule if event reference is missing
            Clock.unschedule(self.check_gm_fault)
        
        # Clean up rest period state and callbacks
        self.gm_fault_in_rest_period = False
        if hasattr(self, '_rest_period_callback') and self._rest_period_callback:
            self._rest_period_callback.cancel()
            self._rest_period_callback = None

    def _handle_gm_fault_pause_resume(self):
        """
        Handle the pause/resume sequence when GM fault counter increments.
        SIMPLE: Pause → Rest for EXACTLY 2 seconds → Resume (regardless of current)
        """
        try:
            self._log('info', 'GM Fault: Starting pause/resume sequence')
            
            # Check if there's an active cycle to pause
            if not (hasattr(self, 'cycle_process') and self.cycle_process and self.cycle_process.is_alive()):
                self._log('debug', 'GM Fault: No active cycle to pause, skipping pause/resume')
                return
            
            # Step 1: Pause the current cycle
            self._log('info', 'GM Fault: Pausing current cycle')
            pause_success = self.pause_current_cycle()
            
            if not pause_success:
                self._log('error', 'GM Fault: Failed to pause cycle, continuing without pause/resume')
                return
            
            # Step 2: Enter rest period mode - STOP GM fault monitoring to prevent race conditions
            self._log('info', 'GM Fault: Entering 2-second rest period - stopping GM fault monitoring')
            self.gm_fault_in_rest_period = True
            self.set_rest()
            
            # Turn OFF shutdown relay during GM fault pause (CS9 profile only)
            self.set_shutdown_relay(False, 'gm_fault')
            self._log('info', 'GM Fault: Shutdown relay disabled during pause')
            
            # Cancel any existing rest period callback to prevent overlaps
            if self._rest_period_callback:
                self._rest_period_callback.cancel()
                self._log('debug', 'GM Fault: Cancelled existing rest period callback')
            
            # Step 3: Resume after EXACTLY 2 seconds (no current monitoring)
            def resume_after_2_seconds(dt):
                try:
                    # Check if we're still in rest period (could have been cancelled)
                    if not self.gm_fault_in_rest_period:
                        self._log('debug', 'GM Fault: Rest period was cancelled, aborting callback')
                        return
                        
                    self._log('info', 'GM Fault: 2-second rest period completed, resuming cycle')
                    self._complete_rest_period_and_resume()
                        
                except Exception as resume_error:
                    self._log('error', f'GM Fault: Error during resume: {resume_error}')
                    self._complete_rest_period_and_resume()
            
            # Schedule resume for EXACTLY 2 seconds from now
            self._rest_period_callback = Clock.schedule_once(resume_after_2_seconds, 2.0)
            
        except Exception as e:
            self._log('error', f'GM Fault: Error in pause/resume sequence: {e}')
            # Ensure we're in a safe state
            self._complete_rest_period_and_resume()
    
    def _complete_rest_period_and_resume(self):
        """Complete the rest period and resume the cycle with proper cleanup."""
        try:
            # Clear rest period flag to re-enable GM fault monitoring
            self.gm_fault_in_rest_period = False
            
            # Cancel any pending rest period callback
            if self._rest_period_callback:
                self._rest_period_callback.cancel()
                self._rest_period_callback = None
            
            # Re-enable shutdown relay when resuming from GM fault pause
            # (relay will stay OFF if count reaches 3 and triggers vac pump alarm)
            self.set_shutdown_relay(True, 'gm_fault')
            self._log('info', 'GM Fault: Shutdown relay re-enabled for cycle resume')
            
            # Attempt to resume the cycle
            self._log('info', 'GM Fault: Attempting to resume paused cycle')
            resume_success = self.resume_paused_cycle()
            
            if resume_success:
                self._log('info', 'GM Fault: Successfully resumed cycle after GM fault pause - GM monitoring re-enabled')
            else:
                self._log('warning', 'GM Fault: Failed to resume cycle, cycle may have completed or been cleared')
                
        except Exception as e:
            self._log('error', f'GM Fault: Error completing rest period and resume: {e}')
            # Ensure we're in a safe state
            self.gm_fault_in_rest_period = False
            if self._rest_period_callback:
                self._rest_period_callback.cancel()
                self._rest_period_callback = None
            try:
                self.set_rest()
            except Exception as rest_error:
                self._log('error', f'GM Fault: Error setting rest mode after resume failure: {rest_error}')


    def _set_vac_pump_alarm(self):
        """Set the vac pump alarm in the database."""
        try:
            # Connect directly to the alarms database
            db_path = os.path.join('/home/cpx003/vst_gm_control_panel/vst_gm_control_panel/data/db', 'app.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create tables if they don't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS alarms
            (id INTEGER PRIMARY KEY, key TEXT UNIQUE, value TEXT);
            ''')
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS gm
            (id INTEGER PRIMARY KEY, key TEXT UNIQUE, value TEXT);
            ''')
            
            # Set vac pump alarm
            cursor.execute('INSERT OR REPLACE INTO alarms (key, value) VALUES (?, ?)',
                          ('vac_pump_failure_count', '10'))
            cursor.execute('INSERT OR REPLACE INTO gm (key, value) VALUES (?, ?)',
                          ('vac_pump_alarm', 'True'))
            
            conn.commit()
            conn.close()
            
            self._log('info', 'GM Fault: Set vac pump alarm in database')
        except Exception as e:
            self._log('error', f'GM Fault: Error setting vac pump alarm: {e}')

    def cleanup(self):
        """
        Cleanup resources on exit with timeout protection.
        """
        cleanup_start = time.time()
        print("Cleaning up IOManager resources...")

        def timeout_reached():
            return time.time() - cleanup_start > CLEANUP_TIMEOUT

        try:
            # Stop GM fault monitoring
            self.stop_gm_fault_check()
            
            # Set all stop events immediately
            self._stop_cycle_event.set()
            self._stop_mode_event.set()
            if hasattr(self, 'buzzer_stop_event'):
                self.buzzer_stop_event.set()
            
            # Stop sensor reading thread
            if hasattr(self, '_sensor_stop_event'):
                self._sensor_stop_event.set()
            if hasattr(self, '_sensor_thread') and self._sensor_thread is not None:
                try:
                    if self._sensor_thread.is_alive():
                        self._sensor_thread.join(timeout=PROCESS_STOP_TIMEOUT)
                except:
                    pass  # Silence cleanup errors
                finally:
                    self._sensor_thread = None

            # Stop processes with timeout protection and better null safety
            processes_to_stop = []
            
            # Stop cycle process - silence all errors
            try:
                if hasattr(self, 'cycle_process') and self.cycle_process is not None:
                    if self.cycle_process.is_alive():
                        self.cycle_process.terminate()
                        self.cycle_process.join(timeout=PROCESS_STOP_TIMEOUT)
                        if self.cycle_process.is_alive():
                            os.kill(self.cycle_process.pid, signal.SIGKILL)
            except:
                pass  # Silence all cleanup errors
            finally:
                self.cycle_process = None

            # Stop mode process - silence all errors
            try:
                if hasattr(self, 'mode_process') and self.mode_process is not None:
                    if self.mode_process.is_alive():
                        self.mode_process.terminate()
                        self.mode_process.join(timeout=PROCESS_STOP_TIMEOUT)
                        if self.mode_process.is_alive():
                            os.kill(self.mode_process.pid, signal.SIGKILL)
            except:
                pass  # Silence all cleanup errors
            finally:
                self.mode_process = None

            # Stop buzzer with timeout
            if not timeout_reached() and hasattr(self, 'buzzer_thread') and self.buzzer_thread.is_alive():
                self.buzzer_thread.join(timeout=PROCESS_STOP_TIMEOUT)

            # Set cycle pins to safe state with timeout (exclude shutdown relay)
            if not timeout_reached():
                try:
                    # Only turn off cycle-related pins, NOT the shutdown relay
                    # Shutdown relay should only be turned off during actual shutdown or alarm conditions
                    for pin in ['motor', 'v1', 'v2', 'v5']:
                        if timeout_reached():
                            break
                        if hasattr(self, 'pins') and pin in self.pins:
                            self.pins[pin].value = False
                except Exception as e:
                    self._log('error', f'Error setting pins to safe state: {e}')

            # Stop pigpio with timeout
            if not timeout_reached() and hasattr(self, 'pi') and self.pi is not None:
                try:
                    self.pi.set_PWM_dutycycle(self.buzzer_pin, 0)
                    self.pi.stop()
                except Exception as e:
                    self._log('error', f'Error stopping pigpio: {e}')

            # Clean up ModeManager resources
            if not timeout_reached() and hasattr(self, 'mode_manager'):
                try:
                    self.mode_manager.cleanup()
                    Logger.info('IOManager: ModeManager cleanup completed')
                except Exception as e:
                    self._log('error', f'Error cleaning up ModeManager: {e}')

            if timeout_reached():
                self._log('warning', "Cleanup timed out - some resources may not be properly cleaned up")
            else:
                self._log('info', "IOManager cleanup completed successfully")

        except Exception as e:
            self._log('error', f"Error during cleanup: {e}")
        finally:
            # Always clear references
            self.mode_process = None
            self.cycle_process = None
            self.pi = None
            if self._mcp_lock.locked():
                self._mcp_lock.release()
            if hasattr(self, 'mode_manager'):
                try:
                    self.mode_manager.cleanup()
                except Exception:
                    pass  # Silence cleanup errors