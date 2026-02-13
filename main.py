#!/usr/bin/python3

'''
Green Machine Control Panel Application:

This is the main application file for the VST Green Machine Control Panel,
an industrial control system for vapor recovery equipment at gas stations.

The application provides:
- Multi-profile support (CS2, CS8, CS9, CS12) for different equipment configurations
- Comprehensive alarm management with 72-hour shutdown protocols
- Hardware I/O control via I2C (pressure sensors, relays, motor control)
- Multi-language support (English/Spanish)
- User access control with 5 permission levels
- Out-of-box experience (OOBE) for initial setup
- Real-time monitoring and automated cycle management

Author: Tommy Wallace
Date: June 2025
License: Vapor Systems Technologies
'''

# Initial config for kivy must be imported first
from config.settings import app_config, app_info

# Standard library imports
import argparse
import asyncio
import atexit
import board
import busio
from datetime import datetime, timedelta
import digitalio
import locale
import os
import pwmio
import signal
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from zoneinfo import ZoneInfo

# Kivy framework imports for UI
from kivy.logger import Logger
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, StringProperty
from kivy.uix.screenmanager import NoTransition, ScreenManager
from kivymd.app import MDApp
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.screen import MDScreen
from kivymd.uix.widget import Widget

# Third party imports
from materialyoucolor.utils.platform_utils import SCHEMES

# Local application imports - Main screens
from views import (
    DateVerificationScreen,
    MainScreen, FaultsScreen, CodeEntryScreen, MaintenanceScreen,
    FunctionalityTestScreen, LeakTestScreen, ContractorScreen, ManualModeScreen,
    OverfillOverrideScreen, SystemScreen, SystemConfigScreen,
    TimeEntryScreen, ShutdownScreen, AdminScreen, AdjustmentsScreen,
    ProfileScreen, CanisterCleanScreen, EfficiencyTestScreen, AboutScreen,
    PublicAboutScreen
)
# Local application imports - Out-of-Box Experience (OOBE) screens
from views.oobe import (
    LanguageSelectionScreen, ProfileSelectionScreen, PowerInfoScreen, GMSerialScreen,
    PanelSerialScreen, TimezoneSelectionScreen, CRENumberScreen, ContractorCertificationScreen,
    ContractorPasswordScreen, BreakerInfoScreen, QuickFunctionalityTestScreen,
    PressureCalibrationScreen, OOBEOverfillOverrideScreen, StartupCodeScreen
)
# Local application imports - UI components
from components import (
    TimeoutDialog, Diagnostics, DropdownMenu, StatusBar,
    TopBar, NavDrawerItem, SideBar, NoDragMDBottomSheet,
    AlarmDialog, ConfirmationDialog, LogoutDialog
)
# Local application imports - Hardware controllers
from controllers import IOManager
# Local application imports - Utility modules
from utils import (
    AlarmManager, DatabaseManager,
    DataHandler, LanguageHandler, ProfileHandler,
    LogArchiver, DatabaseCleaner, CycleStateManager, alarm_reload,
    modem
)


class ControlPanel(MDApp):
    '''
    - Hardware I/O management (pressure sensors, relays, motor control)
    - Alarm monitoring and 72-hour shutdown protocols
    - User interface and screen management
    - Database operations and configuration management
    - Multi-profile support (CS2, CS8, CS9, CS12)
    - Multi-language support (English/Spanish)
    - User access control and authentication
    '''
    
    # System Status Properties
    active = BooleanProperty(False)                    # True when system is actively running cycles
    activity_status = StringProperty('IDLE')           # Current activity status display text
    gm_status = StringProperty('IDLE')                 # Green Machine status display text
    current_mode = StringProperty('rest')              # Current operational mode (rest, run, purge, etc.)
    
    # Alarm Management Properties
    alarm = BooleanProperty(False)                     # True when any alarm is active
    active_alarms = StringProperty('...')              # Display text for active alarms
    alarm_cycle_index = NumericProperty(0)             # Index for cycling through alarm display
    alarm_list = ListProperty([])                      # List of currently active alarm names
    alarm_silenced = BooleanProperty(False)            # True when alarms have been silenced
    buzzer_triggered = BooleanProperty(False)          # True when alarm buzzer is active
    dialog = BooleanProperty(False)                    # True when alarm dialog is displayed
    pressure_sensor_alarm = BooleanProperty(False)    # True when pressure sensor alarm is active
    
    # Hardware Status Properties
    active_relays = StringProperty('none')             # Names of currently active relays
    active_relay_string = StringProperty('')          # Formatted string of relay states
    last_relays = StringProperty('')                  # Previous relay state for change detection
    current_amps = StringProperty()                   # Current motor amperage reading
    current_pressure = StringProperty()               # Current pressure reading with units
    current_run_cycle_count = StringProperty()        # Total number of run cycles completed
    
    # Operational Mode Properties
    bleed = BooleanProperty(False)                     # True when in bleed mode (pressure relief)
    functionality_test = BooleanProperty(False)        # True when functionality test is running
    canister_clean = BooleanProperty(False)            # True when canister cleaning cycle is running
    efficiency_test = BooleanProperty(False)           # True when efficiency test is running
    leak_test = BooleanProperty(False)                 # True when leak test is running
    manual_mode = BooleanProperty(False)               # True when in manual operation mode
    
    # User Interface Properties
    language = StringProperty('EN')                    # Current language (EN/ES)
    current_time = StringProperty()                    # Current time display text
    current_date = StringProperty()                    # Current date display text
    debug = BooleanProperty(False)                     # True when in debug mode (shorter cycle times)
    debug_mode_string = StringProperty('DEBUG')       # Debug mode display text
    
    # User Access Control Properties
    admin_mode = BooleanProperty(False)                # True when admin privileges are active
    user_access_level = NumericProperty(0)             # Current user access level (0-4)
    user_access_time = StringProperty('')              # Time when access was granted
    last_screen_update = NumericProperty(0)            # Timestamp of last screen interaction
    target_screen = StringProperty('')                 # Screen to navigate to after authentication
    
    # System Configuration Properties
    profile = StringProperty('CS8')                    # Equipment profile (CS2, CS8, CS9, CS12)
    gm_part_number = StringProperty()                  # GM Part Number display
    high_limit_string = StringProperty('2.0')          # High pressure limit display
    low_limit_string = StringProperty('-6.0')          # Low pressure limit display
    pin_delay_string = StringProperty('10 ms')         # I/O pin delay display
    variable_limit_string = StringProperty('+/-0.2')   # Variable pressure limit display
    zero_limit_string = StringProperty('+/-0.15')      # Zero pressure limit display
    vac_failure_limit_string = StringProperty('10')    # Vacuum pump failure limit display
    run_threshold_string = StringProperty('0.2')       # Run cycle trigger threshold display
    run_cycle_check_interval_string = StringProperty('720 min')  # Run cycle check interval display
    
    # Shutdown Management Properties
    shutdown = BooleanProperty(False)                  # True when system is in shutdown mode
    shutdown_pending = BooleanProperty(False)          # True when shutdown is pending
    shutdown_time_remaining = StringProperty('')       # Time remaining until shutdown
    modified_shutdown_time = NumericProperty(0)        # Custom shutdown time for testing
    # Shutdown warning acknowledgment flags
    shutdown_first_warning_acknowledged = BooleanProperty(False)   # 48 hours remaining
    shutdown_second_warning_acknowledged = BooleanProperty(False)  # 36 hours remaining
    shutdown_third_warning_acknowledged = BooleanProperty(False)   # 25 hours remaining
    shutdown_fourth_warning_acknowledged = BooleanProperty(False)  # 1 hour remaining
    
    # Test Mode Properties
    test_mode = BooleanProperty(False)                 # True when in system test mode
    test_mode_start = NumericProperty(0)               # Timestamp when test mode started
    test_run_time = NumericProperty(3600 * 4)          # Total test mode duration (4 hours)
    test_low_limit = StringProperty('-0.55')           # Test mode low pressure limit
    test_high_limit = StringProperty('-0.35')          # Test mode high pressure limit
    test_rest_time = StringProperty('5')               # Test mode rest time between cycles
    test_cycle_run_time = StringProperty('15')         # Test mode individual cycle duration
    test_cycle = BooleanProperty(False)                # True when test cycle is running
    test_cycle_counter = NumericProperty(0)            # Counter for test cycles
    test_shutdown_time = BooleanProperty(False)        # True when using custom shutdown time
    
    # Timing and Cycle Properties
    run_cycle = BooleanProperty(False)                 # True when run cycle is active
    run_cycle_interval = NumericProperty(43140)        # Interval between automatic run cycles
    timeout_dialog = BooleanProperty(False)            # True when timeout dialog is shown
    silenced = BooleanProperty(False)                  # True when alarms are silenced
    silenced_time = NumericProperty(0)                 # Timestamp when alarms were silenced
    
    # Hardware Control Properties (for developer mode display)
    motor = BooleanProperty(False)                     # Motor relay state
    v1 = BooleanProperty(False)                        # Valve 1 relay state
    v2 = BooleanProperty(False)                        # Valve 2 relay state
    v5 = BooleanProperty(False)                        # Valve 5 relay state
    tls = BooleanProperty(False)                       # Tank level switch state
    
    # Database manager instance (shared across application)
    _database = DatabaseManager()
    
    def on_profile(self, instance, value):
        """Handle profile changes by updating alarms and rebuilding screens"""
        Logger.info(f'Application: Profile changed to {value}')
        
        # Ensure profile_handler is available before proceeding
        if not hasattr(self, 'profile_handler') or self.profile_handler is None:
            Logger.warning('Application: profile_handler not available during profile change')
            return
            
        # Save the new profile
        self.profile_handler.save_profile(value)
        
        # Update GM part number for the new profile
        new_part_number = self.get_gm_part_number()
        Logger.info(f'Application: Updating GM part number from {self.gm_part_number} to {new_part_number}')
        self.gm_part_number = new_part_number
        
        # Force property change notification to update UI immediately
        self.property('gm_part_number').dispatch(self)
        
        # Reload alarms for new profile
        self.profile_handler.load_alarms()
        
        # Re-evaluate shutdown relay state for new profile with a small delay
        # to ensure alarm manager has processed the profile change
        if hasattr(self, 'io') and hasattr(self.io, 're_evaluate_shutdown_relay_for_profile_change'):
            Clock.schedule_once(lambda dt: self.io.re_evaluate_shutdown_relay_for_profile_change(), 0.5)
            
        # Rebuild faults screen if it exists
        if hasattr(self, 'sm'):
            faults_screen = self.sm.get_screen('Faults')
            if faults_screen:
                faults_screen.update_alarm_screen()
    # Remove duplicate property definitions - they're already defined above
    _database = DatabaseManager()

    def __init__(self, developer_mode=False, startup_screen='Main', **kwargs):
        """
        Initialize the Control Panel application
        
        Args:
            developer_mode (bool): Enable developer features and debug output
            startup_screen (str): Initial screen to display ('Main' by default)
            **kwargs: Additional arguments passed to MDApp
        """
        super().__init__(**kwargs)
        self._dir = os.path.dirname(__file__)
        self.developer_mode = developer_mode
        self.startup_screen = startup_screen
        # Log initialization with timestamp and developer mode status
        Logger.debug(
            f'Application: {self.dt()} | {self.developer_mode}'
        )
        # Register signal handler for clean Ctrl+C shutdown
        signal.signal(signal.SIGINT, self._handle_sigint)

    def build(self):
        """
        Build and initialize the main application
        
        This is the main entry point called by Kivy to set up the application.
        It configures all core components, UI elements, and starts monitoring.
        
        Returns:
            ScreenManager: The main screen manager for the application
        """
        self._configure_application()
        self._setup_core_components()
        self._register_handlers()
        self._setup_periodic_updates()
        self._configure_ui()
        self._setup_modem()
        self._display_application_info()
        return self.sm

    def dt(self):
        """
        Get current timestamp formatted for logging
        
        Returns:
            str: Formatted timestamp string (YYYYMMDD HH:MM:SS)
        """
        return datetime.now().strftime('%Y%m%d %H:%M:%S')

    def _configure_application(self):
        """
        Configure basic application settings and load configuration
        
        Loads the main configuration file and initializes application metadata
        """
        self.config = app_config
        self._get_app_info()
        self._setup_databases()

    def _get_app_info(self):
        """
        Load application metadata from configuration
        
        Sets up device name, software version, and UI properties
        """
        self.app_info = app_info
        self.device_name = socket.gethostname().upper()
        self.icon = self.app_info.get('icon', '')
        self.title = self.app_info.get('title', '')
        self.software = self.app_info.get('software', {}).get('name', '')
        # GM part number will be set after profile is loaded in _load_machine_settings()
        self.software_version = self.app_info.get('software', {}).get('version', '')

    def get_gm_part_number(self):
        """Retrieve the GM part number based on the current profile"""
        profile_part_numbers = {
            'CS2': 'VST-GM3-CS2A-101',
            'CS8': 'VST-GM3-CS8A-101',
            'CS9': 'VST-GM3-CS9A-101',
            'CS12': 'VST-GM3-CS12A-101'
        }
        return profile_part_numbers.get(self.profile, 'GM-12345-UNKNOWN')

    def _display_application_info(self, *args):
        """Log application information for debugging and monitoring"""
        Logger.info(f'Software: {self.software}')
        Logger.info(f'Version: v{self.software_version}')
        Logger.info(f'Device Name: {self.device_name}')

    def _clear_terminal(self):
        """Clear the terminal screen (cross-platform)"""
        os.system('clear' if os.name == 'posix' else 'cls')

    def _setup_databases(self):
        """
        Initialize all database connections and cleanup managers
        
        Creates database managers for each configured database and sets up
        automatic cleanup processes for notifications and system tables
        """
        # Create database managers from configuration
        db_configs = self.config.get('db', {})
        for attr, db_info in db_configs.items():
            table = db_info['table']
            path = db_info['path']
            setattr(self, attr, self._database.from_table(table, path))
        
        # Initialize database cleanup managers for automatic maintenance
        self.notifications_cleaners = []
        # System notifications cleaner
        self.notifications_cleaners.append(DatabaseCleaner(
            db_manager=self.sys_notifs,
            table_name="system",
            config=self.config
        ))
        # User notifications cleaner
        self.notifications_cleaners.append(DatabaseCleaner(
            db_manager=self.usr_notifs,
            table_name="user",
            config=self.config
        ))
        # Sys table cleaner (also in notifications.db)
        self.notifications_cleaners.append(DatabaseCleaner(
            db_manager=self.sys_notifs,  # Using the same db manager as it's in the same database
            table_name="sys",
            config=self.config
        ))

    def run_stabilize_pi(self):
        '''Run the stabilize_pi script if 24 hours have elapsed since last run.'''
        try:
            last_run = self.gm_db.get_setting('last_stabilize_run')
            current_time = datetime.now()
            
            if last_run is None or (current_time - datetime.fromisoformat(last_run)) >= timedelta(days=1):
                Logger.info(
                    f'Application: Running system optimization (stabilize_pi.py) | {self.dt()}'
                )
                script_path = os.path.join(self._dir, 'utils', 'stabilize_pi.py')
                result = subprocess.run(['sudo', '-E', 'python3', script_path],
                                     capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.gm_db.add_setting('last_stabilize_run', current_time.isoformat())
        except Exception as e:
            pass

    def _setup_core_components(self):
        """
        Initialize all core application components and managers
        
        Sets up alarm management, I/O control, data handling, language support,
        profile management, and system monitoring components
        """
        # Initialize core management components
        self.alarm_manager = AlarmManager()
        self.profile_handler = ProfileHandler()
        self.language_handler = LanguageHandler()
        self.data_handler = DataHandler()
        self.local_data_handler = DataHandler('/home/cpx003/vst_gm_control_panel')
        self.cycle_state_manager = CycleStateManager()
        
        # Set up log archiving for maintenance
        logfile_path = '/home/cpx003/vst_gm_control_panel/vst_gm_control_panel/logfile.csv'
        self.log_archiver = LogArchiver(
            log_path=logfile_path,
            config=self.config
        )
        
        # Initialize hardware I/O manager
        self.io = IOManager()
        # Start background sensor reading thread now that app.io is available
        self.io.start_background_sensors()
        # Connect cycle state manager to I/O for coordination
        self.io.set_cycle_state_manager(self.cycle_state_manager)
        
        # Load default settings and machine configuration
        self.default_all()
        self._load_machine_settings()
        
        # Run system optimization if needed
        self.run_stabilize_pi()

    def _setup_modem(self):
        """
        Initialize serial communication for ESP32 data transmission
        
        Sets up SerialManager for sending telemetry data via UART
        """
        self._clear_terminal()
        self.serial_manager = modem.SerialManager(self.data_handler)
        self.serial_manager.start()

    def _load_machine_settings(self):
        """
        Load saved machine configuration and user preferences
        
        Restores language settings, equipment profile, and cycle counts
        from the database
        """
        # Load operational data
        self.get_cycle_count()
        
        # Load user language preference
        self.language_handler.load_user_language()
        Logger.info(f'Language: {self.language}')
        
        # Load equipment profile and trigger property change handler
        loaded_profile = self.profile_handler.load_profile()
        # Always set profile to trigger the on_profile handler
        self.profile = loaded_profile
        Logger.info(f'Profile: {self.profile}')
        
        # Set GM part number based on loaded profile
        self.gm_part_number = self.get_gm_part_number()
        Logger.info(f'GM Part Number: {self.gm_part_number}')
        
        # Force property change notification to update UI
        self.property('gm_part_number').dispatch(self)

    def _set_pressure_defaults(self, pressure_defaults):
        '''Set the pressure limits for the application.'''
        self.variable_limit_string = f'+/-{pressure_defaults.get("variable_pressure", 0.2)}'
        self.zero_limit_string = f'+/-{pressure_defaults.get("zero_pressure", 0.15)}'
        self.low_limit_string = str(pressure_defaults.get("under_pressure", '-6.0'))
        self.high_limit_string = str(pressure_defaults.get("over_pressure", '2.0'))
        Logger.debug(f'Pressure: Defaults set. | {self.dt()}')

    def _set_cycle_defaults(self, cycle_defaults):
        '''Set the run cycle defaults for the application.'''
        self.vac_failure_limit_string = str(cycle_defaults.get("vac_pump_failure", '10'))
        self.run_cycle_interval = cycle_defaults.get("run_cycle_check_interval", 43200)
        self.run_threshold_string = str(cycle_defaults.get("run_cycle", '0.2'))
        # Set pin delay (coming from interface thresholds in the config but used here)
        interface_defaults = self.config.get('system', {}).get('thresholds', {}).get('interface', {})
        self.io.set_pin_delay(interface_defaults.get('pin_delay', 0.01))
        # Set user-friendly display strings
        self.run_cycle_check_interval_string = '720 min'  # Derived from run_cycle_check_interval
        self.pin_delay_string = '10 ms'
        Logger.debug(f'Cycle: Defaults set. | {self.dt()}')

    def _register_handlers(self):
        '''Register cleanup and signal handlers'''
        atexit.register(self._cleanup_on_exit)
        alarm_reload.setup_signal_handlers(self)

    def set_update_intervals(self):
        ''' Set the update intervals for the application.'''
        intervals = [
            (self.one_second_updates, 1),
            (self.get_pressure, 1),
            (self.get_amps, 1),  # Update current display every 1 second for better responsiveness
            (self.get_gm_status, 3),
            (self.check_alarms, 3),
            (self.cycle_alarms, 10),
            (self.fifteen_second_updates, 15),
            (self.get_datetime, 30),
            (self.two_minute_updates, 60*2),
            (self.hourly_updates, 60*60),  # Run maintenance tasks hourly (every hour)
        ]
        for method, interval in intervals:
            Clock.schedule_interval(method, interval)
        Clock.schedule_once(self.language_handler.check_all_screens, 0)
        
        # Schedule stabilize_pi check after UI is initialized
        Clock.schedule_once(lambda dt: self.run_stabilize_pi(), 5)
        
        # Schedule delayed validation of shutdown relay after AlarmManager has time to validate alarms
        Clock.schedule_once(lambda dt: self._validate_shutdown_relay(), 5)

    def one_second_updates(self, *args):
        '''Group all one-second updates together.'''
        if self.developer_mode:
            self.get_active_relays()
        # get_amps() moved to 3-second interval for display stability

    def fifteen_second_updates(self, *args):
        '''Grouping all log file updates and data transmission.'''
        self.data_handler.write_log_entry()
        self.local_data_handler.write_log_entry()
        # Send data to ESP32 via serial
        payload = self.serial_manager.create_payload()
        if payload:
            self.serial_manager.send_data(payload)

    def two_minute_updates(self, *args):
        '''Group all two-minute updates together.'''
        self.check_last_run_cycle()
        self.access_timeout()

    def send_reload_signal(self):
        '''Send a reload signal to self to refresh alarm state.'''
        try:
            pid = os.getpid()
            Logger.info(f'Application: Sending reload signal to PID {pid}')
            os.kill(pid, signal.SIGUSR1)
            return True
        except Exception as e:
            Logger.error(f'Application: Failed to send reload signal: {e}')
            return False

    def hourly_updates(self, *args):
        '''Group all hourly maintenance tasks.'''
        self.archive_log_file()
        self.cleanup_db()
        self.run_stabilize_pi()

    def _validate_shutdown_relay(self):
        """
        Validate and correct shutdown relay state after initialization.
        
        This method runs 5 seconds after boot to ensure the shutdown relay
        is in the correct state based on actual alarm conditions and current profile,
        not stale database values from previous sessions.
        """
        try:
            Logger.info(f'Application: Validating shutdown relay state for profile {self.profile}')
            
            # Use the IOManager's re-evaluation method which considers profile-specific rules
            if hasattr(self.io, 're_evaluate_shutdown_relay_for_profile_change'):
                self.io.re_evaluate_shutdown_relay_for_profile_change()
                Logger.info('Application: Shutdown relay validation completed using profile-aware logic')
            else:
                # Fallback to original logic if method not available
                Logger.warning('Application: Profile-aware validation not available, using fallback logic')
                # Check if there's actually a vac pump alarm active
                is_alarm_active = self.io._is_vac_pump_alarm_active()
                
                if is_alarm_active:
                    # Verify this is a legitimate alarm by checking AlarmManager
                    vac_pump_failure_count = self.alarms_db.get_setting('vac_pump_failure_count')
                    vac_failure_limit = int(self.vac_failure_limit_string)
                    
                    if vac_pump_failure_count and int(vac_pump_failure_count) >= vac_failure_limit:
                        # Legitimate alarm - use profile-aware relay control
                        self.io.set_shutdown_relay(False, 'vac_pump')
                        Logger.info('Application: Validated vac pump alarm is active, applied profile-specific relay control')
                    else:
                        # Stale alarm data - enable shutdown relay
                        Logger.info('Application: Detected stale vac pump alarm data, enabling shutdown relay')
                        self.io.set_shutdown_relay(True, 'startup')
                else:
                    # No alarm - ensure shutdown relay is ON (unless system is in shutdown mode)
                    if not self.shutdown:
                        self.io.set_shutdown_relay(True, 'startup')
                    
        except Exception as e:
            Logger.error(f'Application: Error validating shutdown relay: {e}')
            # On error, default to safe state (relay enabled) unless in shutdown mode
            if not self.shutdown:
                try:
                    self.io.set_shutdown_relay(True, 'startup')
                except Exception as relay_error:
                    Logger.error(f'Application: Failed to set shutdown relay to safe state: {relay_error}')

    def _setup_periodic_updates(self):
        '''Initialize state and set up periodic updates'''
        self.alarm_list_last_check = set()
        self.get_pressure()
        self.get_datetime()
        self.set_update_intervals()

    def _configure_ui(self):
        '''Load and configure UI elements'''
        self._load_all_kv_files()
        self.dropdown_menu = DropdownMenu()
        self._configure_application_theme()
        self.sm = ScreenManager(transition=NoTransition())
        self._configure_screen_manager()

    def _load_all_kv_files(self):
        '''Load all .kv files in the application directory.'''
        for root, _, files in os.walk(self._dir):
            for file in files:
                if file.endswith('.kv'):
                    Builder.load_file(os.path.join(root, file))

    def _configure_application_theme(self):
        '''Configure the application theme.'''
        self.theme_cls.primary_palette = 'Steelblue'
        self.theme_cls.theme_style = 'Dark'
        self.success_color = '#2E7D32'
        self.admin_color = '#FFA500'

    def _configure_screen_manager(self):
        '''
        Configure the Screen Manager.
        '''
        screen_config = self.get_screen_map()
        for screen_name, screen_class in screen_config.items():
            instance = screen_class(self, name=screen_name)
            self.sm.add_widget(instance)
            
        # Check OOBE status and set initial screen
        # Only use the startup_screen from constructor if OOBE is complete
        oobe_screen = self._check_oobe_status()
        if oobe_screen != 'Main':  # If OOBE is not complete, use the OOBE screen
            self.startup_screen = oobe_screen
        self.sm.current = self.startup_screen
        
    def _check_oobe_status(self):
        '''
        Check the OOBE status and determine the startup screen.
        
        Returns:
            str: The name of the screen to start on
        '''
        # Initialize OOBE flags if they don't exist
        oobe_language = self.oobe_db.get_setting('language_selected', 'false')
        oobe_profile = self.oobe_db.get_setting('profile_selected', 'false')
        oobe_serial = self.oobe_db.get_setting('gm_serial_entered', 'false')
        oobe_power_info = self.oobe_db.get_setting('power_info_acknowledged', 'false')
        oobe_date_verified = self.oobe_db.get_setting('date_verified', 'false')
        oobe_timezone_verified = self.oobe_db.get_setting('timezone_verified', 'false')
        oobe_cre_number_entered = self.oobe_db.get_setting('cre_number_entered', 'false')
        oobe_contractor_certification_entered = self.oobe_db.get_setting('contractor_certification_entered', 'false')
        oobe_contractor_password_entered = self.oobe_db.get_setting('contractor_password_entered', 'false')
        oobe_breaker_info_acknowledged = self.oobe_db.get_setting('breaker_info_acknowledged', 'false')
        oobe_quick_functionality_test_completed = self.oobe_db.get_setting('quick_functionality_test_completed', 'false')
        oobe_pressure_calibration_completed = self.oobe_db.get_setting('pressure_calibration_completed', 'false')
        oobe_overfill_override_completed = self.oobe_db.get_setting('overfill_override_completed', 'false')
        oobe_startup_code_entered = self.oobe_db.get_setting('startup_code_entered', 'false')
        
        # Determine startup screen based on OOBE flags
        if oobe_language == 'false':
            return 'OOBELanguageSelection'
        elif oobe_profile == 'false':
            return 'OOBEProfileSelection'
        elif self.oobe_db.get_setting('panel_serial_entered', 'false') == 'false':
            return 'OOBEPanelSerial'
        elif oobe_serial == 'false':
            return 'OOBEGMSerial'
        elif oobe_power_info == 'false':
            return 'OOBEPowerInfo'
        elif oobe_date_verified == 'false':
            return 'OOBEDateVerification'
        elif oobe_timezone_verified == 'false':
            return 'OOBETimezoneSelection'
        elif oobe_cre_number_entered == 'false':
            # Get the selected profile from the database
            selected_profile = self.oobe_db.get_setting('profile', '')
            
            # If the profile is not CS2, navigate to the CRE number entry screen
            if selected_profile != 'CS2':
                return 'OOBECRENumber'
            else:
                # If the profile is CS2, mark CRE number entry as not required
                self.oobe_db.add_setting('cre_number_entered', 'true')
                # Continue to contractor certification screen
                return 'OOBEContractorCertification'
        elif oobe_contractor_certification_entered == 'false':
            return 'OOBEContractorCertification'
        elif oobe_contractor_password_entered == 'false':
            return 'OOBEContractorPassword'
        elif oobe_breaker_info_acknowledged == 'false':
            # Get the selected profile from the database
            selected_profile = self.oobe_db.get_setting('profile', '')
            
            # Only show breaker info screen for CS8 and CS12 profiles
            if selected_profile in ['CS8', 'CS12']:
                return 'OOBEBreakerInfo'
            else:
                # For other profiles, mark breaker info as not required
                self.oobe_db.add_setting('breaker_info_acknowledged', 'true')
                # Continue to quick functionality test screen
                return 'OOBEQuickFunctionalityTest'
        elif oobe_quick_functionality_test_completed == 'false':
            return 'OOBEQuickFunctionalityTest'
        elif oobe_pressure_calibration_completed == 'false':
            return 'OOBEPressureCalibration'
        elif oobe_overfill_override_completed == 'false':
            return 'OOBEOverfillOverride'
        elif oobe_startup_code_entered == 'false':
            return 'OOBEStartupCode'
        
        # If all OOBE steps are complete, use the default startup screen
        if self.shutdown:
            return 'Shutdown'
        return 'Main'

    def default_all(self):
        '''Restore default application and gm settings.'''
        # Get threshold defaults directly from the configuration
        pressure_defaults = self.config.get('system', {}).get('thresholds', {}).get('pressure', {})
        cycle_defaults = self.config.get('system', {}).get('thresholds', {}).get('cycles', {})
        interface_defaults = self.config.get('system', {}).get('thresholds', {}).get('interface', {})
        # Set UI theme
        self.theme_cls.primary_palette = 'Steelblue'
        # Apply defaults to UI and functionality
        self._set_pressure_defaults(pressure_defaults)
        self._set_cycle_defaults(cycle_defaults)
        # Handle debug mode
        if self.debug and hasattr(self, 'sm'):
            test_screen = self.sm.get_screen('Test')
            if test_screen:
                test_screen.toggle_debug()
        # Save all threshold defaults to database
        for key, value in pressure_defaults.items():
            self.thresholds_db.add_setting(key, value)
        for key, value in cycle_defaults.items():
            self.thresholds_db.add_setting(key, value)
        for key, value in interface_defaults.items():
            self.thresholds_db.add_setting(key, value)
        # Load alarm settings
        self.profile_handler.load_alarms()
        Logger.info('Application: Restored all default settings.')

    def get_screen_map(self):
        '''Map screen name to associated class.'''
        return {
            # Main application screens
            'Main': MainScreen,
            'Maintenance': MaintenanceScreen,
            'CodeEntry': CodeEntryScreen,
            'FunctionalityTest': FunctionalityTestScreen,
            'LeakTest': LeakTestScreen,
            'Faults': FaultsScreen,
            'Contractor': ContractorScreen,
            'ManualMode': ManualModeScreen,
            'OverfillOverride': OverfillOverrideScreen,
            'System': SystemScreen,
            'SystemConfig': SystemConfigScreen,
            'TimeEntry': TimeEntryScreen,
            'Shutdown': ShutdownScreen,
            'Admin': AdminScreen,
            'Adjustments': AdjustmentsScreen,
            'profile': ProfileScreen,
            'CanisterClean': CanisterCleanScreen,
            'EfficiencyTest': EfficiencyTestScreen,
            'About': AboutScreen,
            'PublicAbout': PublicAboutScreen,
            
            # OOBE screens
            'OOBELanguageSelection': LanguageSelectionScreen,
            'OOBEProfileSelection': ProfileSelectionScreen,
            'OOBEPowerInfo': PowerInfoScreen,
            'OOBEDateVerification': DateVerificationScreen,
            'OOBETimezoneSelection': TimezoneSelectionScreen,
            'OOBEGMSerial': GMSerialScreen,
            'OOBEPanelSerial': PanelSerialScreen,
            'OOBECRENumber': CRENumberScreen,
            'OOBEContractorCertification': ContractorCertificationScreen,
            'OOBEContractorPassword': ContractorPasswordScreen,
            'OOBEBreakerInfo': BreakerInfoScreen,
            'OOBEQuickFunctionalityTest': QuickFunctionalityTestScreen,
            'OOBEPressureCalibration': PressureCalibrationScreen,
            'OOBEOverfillOverride': OOBEOverfillOverrideScreen,
            'OOBEStartupCode': StartupCodeScreen
        }

    def stop_any_cycle(self):
        '''Stop any active cycle except manual mode cycles.'''
        # Don't stop manual mode cycles when navigating between screens
        if not self.manual_mode:
            self.io.stop_mode()
            self.io.stop_cycle()
        self.functionality_test = False
        self.leak_test = False
        self.canister_clean = False
        self.efficiency_test = False

    def stop_all_cycles_including_manual(self):
        '''Stop ALL active cycles including manual mode - for shutdown/emergency situations.'''
        self.io.stop_mode()
        self.io.stop_cycle()
        self.functionality_test = False
        self.leak_test = False
        self.canister_clean = False
        self.efficiency_test = False
        self.manual_mode = False

    def switch_screen(self, screen_name='Main'):
        '''Switch to the specified screen.'''
        if self.user_access_level > 0:
            self.last_screen_update = time.time()
        else:
            self.last_screen_update = 0
        if self.functionality_test:
            self.toggle_functionality_test(False)
        if self.leak_test:
            self.toggle_leak_test(False)
        if self.shutdown and screen_name == 'Main':
            screen_name = 'Shutdown'
        self.sm.current = screen_name
        Logger.info(f'Screen: {screen_name} (admin_mode: {self.admin_mode}, access_level: {self.user_access_level})')

    def elevated_switch_screen(self, screen_name):
        '''Check the user permissions for allowing access to elevated screens.'''
        # Store both the target screen and current screen
        self.target_screen = screen_name
        current_screen = self.sm.current
        
        # Check admin mode first to ensure full access
        if self.admin_mode:
            self.switch_screen(screen_name)
        # Then check developer mode or regular access
        elif self.developer_mode or self._has_access(screen_name):
            self.switch_screen(screen_name)
        else:
            # Store current screen in code entry screen for return path
            code_entry_screen = self.sm.get_screen('CodeEntry')
            code_entry_screen.previous_screen = current_screen
            
            # Go to code entry screen for password verification
            self.stop_any_cycle()
            self.switch_screen('CodeEntry')

    def _has_access(self, screen_name):
        '''
        Check if the user has access to the specified screen.
        Access is determined by the screen's location in views/kv/N directories.
        A user can only access screens in their level's directory and level 0.
        '''
        # Find the screen's .kv file
        screen_path = None
        for root, _, files in os.walk(os.path.join(self._dir, 'views', 'kv')):
            for file in files:
                if file.endswith(f'{screen_name.lower()}_screen.kv'):
                    screen_path = os.path.join(root, file)
                    break
            if screen_path:
                break

        if not screen_path:
            return False

        # Get the directory level
        dir_level = os.path.basename(os.path.dirname(screen_path))

        # Level 0 screens are accessible to all authenticated users
        if dir_level == '0':
            return self.user_access_level > 0

        try:
            # For other levels, allow access if user level is greater than or equal to required level
            return self.user_access_level >= int(dir_level)
        except ValueError:
            return False
            
    def screen_time_elapsed(self):
        '''Get the time elapsed since the last screen update.'''
        current_time = time.time()
        return current_time - self.last_screen_update

    def update_user_access(self, access_level):
        '''Update the user access level.'''
        previous_level = self.user_access_level
        self.user_access_level = access_level
        Logger.info(f'Application: User access level changed from {previous_level} to {self.user_access_level} (admin_mode: {self.admin_mode})')

    def access_timeout(self, *args):
        '''Reset the user access level after a timeout.'''
        if self.user_access_level == 4 and self._is_admin_timeout():
            self._handle_admin_timeout()
        if self.user_access_level > 0 and self._is_access_timeout():
            self._handle_general_timeout()

    def _is_access_timeout(self):
        interface_defaults = self.config.get('system', {}).get('thresholds', {}).get('interface', {})
        access_timeout = interface_defaults.get('access_timeout', 14400)
        return self.screen_time_elapsed() >= access_timeout

    def _is_admin_timeout(self):
        admin_timeout = 60 * 5
        return self.screen_time_elapsed() >= admin_timeout

    def _handle_general_timeout(self):
        self.target_screen = self.sm.current
        self.update_user_access(0)
        Logger.info('Application: User access timed out, returning to Main screen.')
        if not self.functionality_test:
            self.timeout_dialog()

    def _handle_admin_timeout(self):
        Logger.info('Application: Admin access timed out after 5 minutes, clearing admin mode.')
        self.admin_mode = False
        # Reset to no access instead of level 3 to force re-authentication
        self.update_user_access(0)
        # Show timeout dialog and return to main screen
        if self.sm.current == 'Admin':
            self.timeout_dialog()
            self.switch_screen('Main')
        Logger.info('Application: Admin mode cleared, requiring re-authentication.')

    # def access_timeout(self, *args):
    #     '''Reset the user access level after a timeout.'''
    #     interface_defaults = self.config.get('system', {}).get('thresholds', {}).get('interface', {})
    #     access_timeout = interface_defaults.get('access_timeout', 14400)
    #     admin_timeout = 60 * 5  # 5 minutes for admin timeout
    #     if self.user_access_level == 4 and self.screen_time_elapsed() >= admin_timeout:
    #         self.update_user_access(3)
    #         if self.sm.current == 'Admin':
    #             self.switch_screen('Maintenance')       
    #     # Handle regular timeout for all privileged users
    #     if self.user_access_level > 0 and self.screen_time_elapsed() >= access_timeout:
    #         self.target_screen = self.sm.current
    #         self.update_user_access(0)
    #         if not self.functionality_test:
    #             self.timeout_dialog()

    def logout_dialog(self):
        '''Display a timeout dialog.'''
        dialog = LogoutDialog()
        dialog.open_dialog(accept_method=lambda: self.logout())
        Logger.info('Application: User initiated logout.')

    def logout(self):
        '''Log the user out of the system.'''
        # Clear admin mode on logout
        Logger.info(f'Application: Logout initiated - clearing admin mode (was: {self.admin_mode})')
        self.admin_mode = False
        self.update_user_access(0)
        self.switch_screen('Main')

    def refresh_access_timeout(self, *args):
        '''Pause the access timeout.'''
        self.last_screen_update = time.time()

    def timeout_dialog(self):
        '''Display a timeout dialog.'''
        dialog = TimeoutDialog()
        dialog.open_dialog(
            accept_method=lambda: self.switch_screen('CodeEntry'),
            cancel_method=lambda: self.switch_screen('Main')
        )
        
    def get_datetime(self, *args):
        '''Get the current date and time.'''
        now_local = datetime.now()
        current_time = now_local.strftime('%H:%M')
        # Separating time and date locale for manual time entry functionality
        timezone_map = {'ES': 'Europe/Madrid', 'EN': 'America/New_York'}
        now_local = datetime.now(ZoneInfo(timezone_map.get(self.language, 'UTC')))
        self.set_locale()
        current_date = now_local.strftime('%A, %B %d')
        self.current_time = current_time
        self.current_date = current_date

    def set_locale(self):
        '''Set the locale for the application.'''
        locale_map = {'ES': 'es_ES.UTF-8', 'EN': 'en_US.UTF-8'}
        new_locale = locale_map.get(self.language, 'en_US.UTF-8')
        
        # Only change locale if it's different from current
        try:
            current_locale = locale.getlocale(locale.LC_TIME)[0]
            if current_locale != new_locale.split('.')[0]:
                locale.setlocale(locale.LC_TIME, new_locale)
                Logger.debug(f'Application: Locale changed to {new_locale}')
        except Exception as e:
            # If there's any error, force set the locale
            locale.setlocale(locale.LC_TIME, new_locale)
            Logger.debug(f'Application: Locale set to {new_locale}')

    def get_pressure(self, *args):
        '''Get the current pressure reading from cached value (non-blocking).'''
        # Use cached value from background thread to avoid blocking UI
        current_pressure = self.io.get_cached_pressure()
        if current_pressure is None:
            current_pressure = '-99.9'
        else:
            # Check if we got a valid reading (not sensor failure)
            if current_pressure != '-99.9':
                if not self.test_mode:
                    self.bleed = False
                    # Only start run cycle if not in any test mode
                    if (float(current_pressure) > float(self.run_threshold_string) and
                        not self.functionality_test and not self.leak_test and
                        not self.canister_clean and not self.efficiency_test):
                        self.start_run_cycle()
        Clock.schedule_once(lambda dt: self.update_pressure_ui(current_pressure), 0)

    # def read_pressure_with_retry(self, retries=5):
    #     '''Read pressure with retry logic.'''
    #     for _ in range(retries):
    #         pressure = self.io.pressure_sensor.get_pressure()
    #         if pressure is not None:
    #             return pressure
    #     return None

    def get_active_relays(self, *args):
        '''Get the active relays.'''
        current_relays = self.active_relays
        # Check if the relays string has changed
        if current_relays == self.last_relays:
            return  # No changes, so no need to update
        self.last_relays = current_relays  # Update the last known relays
        # Set relay states based on the current active relays string
        self.motor = 'motor' in current_relays
        self.v1 = 'v1' in current_relays
        self.v2 = 'v2' in current_relays
        self.v5 = 'v5' in current_relays
        self.tls = 'shutdown' in current_relays
        relay_states = [
            'o ' if self.motor else 'x ',
            'o ' if self.v1 else 'x ',
            'o ' if self.v2 else 'x ',
            'o ' if self.v5 else 'x ',
            'o ' if self.tls else 'x '
        ]
        self.active_relay_string = ''.join(relay_states)

    def user_defined_change(self):
        '''Change the theme if any default values are changed.'''
        self.theme_cls.primary_palette = 'Burlywood'
        Logger.info('Application: Default values modified by user.')

    def toggle_pressure_sensor_alarm(self, state):
        '''Toggle the pressure sensor alarm state.'''
        self.pressure_sensor_alarm = state
        Clock.unschedule(self.get_pressure)  # Unschedule current pressure updates
        if state:
            Clock.schedule_interval(self.get_pressure, 5)  # Schedule five second pressure updates during alarm
        else:
            Clock.schedule_interval(self.get_pressure, 1)  # Schedule one second pressure updates when alarm is off

    def get_amps(self, *args):
        '''Get the current motor amps from cached value (non-blocking).'''
        # Use cached value from background thread to avoid blocking UI
        current_amps = self.io.get_cached_current()
        Clock.schedule_once(lambda dt: self.update_amp_ui(current_amps), 0)

    def start_gm_fault_check(self, reset_counter=True, reset_timing_state=True):
        '''Delegate GM fault checking to IOManager - CS9 PROFILE ONLY.'''
        self.io.start_gm_fault_check(reset_counter, reset_timing_state)

    def stop_gm_fault_check(self):
        '''Delegate GM fault stopping to IOManager.'''
        self.io.stop_gm_fault_check()

    def update_amp_ui(self, current_amps, *args):
        '''Update the current amps on the UI.'''
        self.current_amps = f'{current_amps} A'

    def update_pressure_ui(self, current_pressure, *args):
        '''Update the pressure on the UI.'''
        if self.language == 'EN':
            self.current_pressure = f'{current_pressure} IWC'
        else:
            self.current_pressure = str(current_pressure)  # Ensure it's always a string for StringProperty

    def get_gm_status(self, *args):
        '''Get the current status of the Green Machine.'''
        gm = self.language_handler.translate('gm_status', 'GREEN MACHINE STATUS')
        
        # Check for hardware availability first
        if hasattr(self.io, 'hardware_available') and not self.io.hardware_available:
            hardware_warning = self.language_handler.translate(
                'hardware_disconnected',
                'CHECK I/O BOARD CONNECTION'
            )
            self.gm_status = f'⚠️ {hardware_warning}'
            
            # Set status bar to red error state
            if hasattr(self, 'sm'):
                try:
                    main_screen = self.sm.get_screen('Main')
                    if hasattr(main_screen, 'ids') and hasattr(main_screen.ids, 'status_bar'):
                        main_screen.ids.status_bar.set_hardware_error_state(True)
                except Exception:
                    pass  # Fail silently if status bar not accessible
            return
        else:
            # Hardware is available - restore normal status bar color
            if hasattr(self, 'sm'):
                try:
                    main_screen = self.sm.get_screen('Main')
                    if hasattr(main_screen, 'ids') and hasattr(main_screen.ids, 'status_bar'):
                        main_screen.ids.status_bar.set_hardware_error_state(False)
                except Exception:
                    pass  # Fail silently if status bar not accessible
        
        if self.shutdown:
            shutdown_key = self.language_handler.translate('shutdown', 'SHUTDOWN')
            self.gm_status = f'{gm.upper()}: {shutdown_key.upper()}'
            if not self.alarm:
                self.toggle_shutdown(False)
        else:
            if self.io.cycle_process is not None and self.io.cycle_process.is_alive() or self.bleed:
                status_key = 'gm_active'
                self.active = True
            else:
                status_key = 'gm_idle'
                self.active = False
                self.manual_mode = False
                
                # Cleanup: If cycle_process exists but is no longer alive, clean up
                if self.io.cycle_process is not None and not self.io.cycle_process.is_alive():
                    self.io.cycle_process = None
                    if self.io._mcp_lock.locked():
                        self.io._mcp_lock.release()
                    self.io.stop_gm_fault_check()
                    if self.run_cycle:
                        self.run_cycle = False
            if self.run_cycle:
                conditions = self.check_cycle_conditions('run_cycle')
                if conditions:
                    self.stop_any_cycle()
            status = self.language_handler.translate(status_key, status_key)
            self.activity_status = status.upper()
            self.gm_status = f'{gm.upper()}: {self.activity_status}'
        self.get_current_mode()

    def toggle_run_cycle_state(self, state):
        '''Set the run cycle state to True or False.'''
        self.run_cycle = state
        self.get_gm_status()

    def check_last_run_cycle(self, *args):
        '''Check the last run cycle and start a new one if necessary.'''
        last_run_cycle = self.gm_db.get_setting('last_run_cycle')
        if last_run_cycle is None:
            current_time = datetime.now().isoformat()
            self.gm_db.add_setting('last_run_cycle', current_time)
        else:
            last_run_time = datetime.fromisoformat(last_run_cycle)
            current_time = datetime.now()
            if current_time - last_run_time >= timedelta(seconds=self.run_cycle_interval):
                Logger.info(f'RunCycle: Last ran at {last_run_time}, starting new cycle.')
                self.start_run_cycle()

    def get_cycle_count(self):
        '''Get the current run cycle count.'''
        run_cycle_count = self.gm_db.get_setting('run_cycle_count')
        if run_cycle_count:
            self.current_run_cycle_count = str(run_cycle_count)
        else:
            self.current_run_cycle_count = '0'

    def start_run_cycle(self):
        '''Start the run cycle.'''
        # Skip run cycle if any test mode is active to prevent interference
        if self.canister_clean or self.efficiency_test or self.leak_test or self.functionality_test:
            Logger.debug('RunCycle: Skipped - test mode active')
            return
            
        conditions = self.check_cycle_conditions('run_cycle')
        if not conditions:
            # Only start if not already running
            if not (self.io.cycle_process and self.io.cycle_process.is_alive()):
                Logger.info('RunCycle: Starting run cycle - pressure exceeded threshold')
                self.toggle_run_cycle_state(True)
                self.io.run_cycle()
                self.get_cycle_count()
        else:
            self.stop_any_cycle()
            self.toggle_run_cycle_state(False)

    def check_cycle_conditions(self, cycle):
        '''
        Determine whether a cycle can run or not.
        Simplified version matching 0.4.10 for better reliability.
        '''
        if not hasattr(self, 'sm'):
            Logger.debug(f'CycleConditions: {cycle} - No screen manager, blocking')
            return True

        # Special handling for run_cycle to prevent interference with test modes
        if cycle == 'run_cycle' and (self.canister_clean or self.efficiency_test or self.leak_test or self.functionality_test):
            Logger.debug(f'CycleConditions: {cycle} - Blocked due to active test mode')
            return True

        if self.sm.current not in self._allowed_screens(cycle).get(cycle, set()):
            Logger.debug(f'CycleConditions: {cycle} - Screen {self.sm.current} not in allowed screens {self._allowed_screens(cycle).get(cycle, set())}, blocking')
            return True

        if self.shutdown:
            Logger.debug(f'CycleConditions: {cycle} - Shutdown active, blocking')
            return True

        # Check overfill condition
        overfill_blocked = self._check_overfill_condition()
        if overfill_blocked:
            Logger.debug(f'CycleConditions: {cycle} - Overfill condition detected, blocking')
            return True

        # Check vac pump condition
        vac_pump_blocked = self._check_vac_pump_condition()
        if vac_pump_blocked:
            Logger.debug(f'CycleConditions: {cycle} - Vac pump condition detected, blocking')
            return True

        if cycle != 'manual_mode':
            if cycle != 'test_mode':
                if cycle == 'run_cycle' and self.test_mode:
                    Logger.debug(f'CycleConditions: {cycle} - Run cycle blocked by test mode')
                    return True
                pressure_blocked = self._check_pressure_sensor_condition()
                if pressure_blocked:
                    Logger.debug(f'CycleConditions: {cycle} - Pressure sensor condition detected, blocking')
                    return True

        return False  # Allow the cycle to run

    def _allowed_screens(self, cycle):
        '''Check if the cycle is allowed on the current screen.'''

        # For test_mode, we allow all screens except specific excluded ones
        if cycle == 'test_mode':
            excluded_screens = {
                'ClearAlarms', 'CodeEntry', 'Contractor', 'FunctionalityTest', 'OOBEQuickFunctionalityTest'
                'LeakTest', 'Maintenance', 'ManualMode', 'OverfillOverride', 'Shutdown'
            }

            # Get all screen names from the screen manager
            all_screens = set(self.sm.screen_names)
            # Return all screens except excluded ones
            return {cycle: all_screens - excluded_screens}
        
        # For other cycles, use the original logic
        return {
            'run_cycle': {'Main', 'Faults', 'TimeEntry', 'PublicAbout'},
            'functionality_test': {'FunctionalityTest', 'OOBEQuickFunctionalityTest'},
            'leak_test': {'LeakTest'},
            'manual_mode': {'ManualMode'},
            'canister_clean': {'CanisterClean'},
            'efficiency_test': {'EfficiencyTest'}
        }

    def _check_overfill_condition(self):
        '''Check if the overfill condition is present.'''
        current_time = datetime.now()
        last_overfill_time = self.alarms_db.get_setting(f'last_overfill_time', None)
        # If the last overfill happened within the last 2 hours, we do not allow the cycle to start
        if last_overfill_time and (current_time - datetime.fromisoformat(last_overfill_time)) < timedelta(hours=2):
            Logger.warning(f'Alarm: Overfill. | {datetime.now():%Y%m%d %H:%M:%S}')
            return True

    def _check_vac_pump_condition(self):
        '''Check if the vacuum pump failure condition is present.'''
        vp_failure = self.alarms_db.get_setting('vac_pump_failure_count', None)
        if vp_failure and int(vp_failure) >= int(self.vac_failure_limit_string):
            Logger.warning(f'Alarm: Vacuum Pump. | {datetime.now():%Y%m%d %H:%M:%S}')
            return True

    def _check_pressure_sensor_condition(self):
        '''Check if a pressure sensor alarm is present.'''
        # Skip pressure sensor check for canister clean cycles
        if not self.run_cycle and not self.canister_clean:
            # Use cached value to avoid blocking UI
            p = self.io.get_cached_pressure()
            if p is None or p == '-99.9' or float(p) <= -40:
                Logger.warning(f'Alarm: Pressure Sensor. | {datetime.now():%Y%m%d %H:%M:%S}')
                return True

    def toggle_functionality_test(self, state):
        '''Toggle the functionality test state.'''
        self.functionality_test = state
        if state:
            self.io.functionality_test()
            Logger.info('FunctionalityTest: Initiated.')
        else:
            self.stop_any_cycle()

    def toggle_leak_test(self, state):
        '''Toggle the leak test state.'''
        self.leak_test = state
        if state:
            self.io.leak_test()
            Logger.info('LeakTest: Initiated.')
        else:
            self.stop_any_cycle()

    def toggle_manual_mode(self, state):
        '''
        Toggle the manual mode state and coordinate with IO manager.
        '''
        if state == self.manual_mode:
            return

        self.manual_mode = state

        if not state:
            # When disabling manual mode, ensure cycles are stopped
            self.stop_any_cycle()

    def toggle_manual_mode_state(self, state):
        '''
        Toggle the manual mode state (compatibility method for IOManager).
        '''
        self.manual_mode = state

    def start_test_mode(self, low_limit, high_limit, run_time, rest_time):
        '''Start system config (test) mode.'''
        # Reset cycle counter at startup
        self.test_cycle_counter = 0
        
        # Reset other test-related flags
        self.bleed = False
        self.test_cycle = False
        
        # Set flags and parameters
        self.test_mode = True
        self.test_mode_start = time.time()
        self.test_low_limit = low_limit
        self.test_high_limit = high_limit
        
        # Convert run_time to an integer for overall test duration
        try:
            self.test_run_time = int(run_time) if isinstance(run_time, str) else run_time
        except (ValueError, TypeError):
            # Default to 4 hours if conversion fails
            self.test_run_time = 3600 * 4
            
        # Store run and rest time for individual cycles
        self.test_cycle_run_time = str(run_time)
        self.test_rest_time = str(rest_time)
        
        # Log start of test mode
        Logger.info(
            f'TestMode: Initiated with low limit {low_limit}, high limit {high_limit}, run time {run_time}, rest time {rest_time}.'
        )
        
        # Schedule monitoring functions
        Clock.schedule_interval(self.check_test_mode, 10 * 60)  # Check 4-hour limit every 10 minutes
        Clock.schedule_interval(self.monitor_test_mode, 1)      # Check pressure and cycle conditions every second
        
    def check_test_mode(self, *args):
        '''Check if test mode has exceeded its maximum duration (4 hours).'''
        if not self.test_mode:
            return
            
        current_time = time.time()
        elapsed_time = current_time - self.test_mode_start
        
        # If 4 hours (14400 seconds) have passed, stop test mode
        if elapsed_time >= 4 * 3600:
            Logger.info('TestMode: Max duration exceeded, stopping test mode.')
            self.stop_test_mode()
        # Log remaining time every 10 minutes
        else:
            remaining_time = (4 * 3600) - elapsed_time
            
    def monitor_test_mode(self, *args):
        '''        
        1. If pressure is below low limit: Enter bleed mode until pressure rises
        2. If pressure is above high limit: Start a run cycle, then check counter
        3. If counter < 2 after a run cycle: Continue monitoring for another run
        4. If counter >= 2 after a run cycle: Do a purge, then reset counter
        5. If pressure is between limits: Stay in rest mode        
        '''
        if not self.test_mode:
            return
    
        try:
            # Get current pressure reading and convert to float
            current_pressure = float(self.current_pressure.replace(' IWC', '')) if self.language == 'EN' else float(self.current_pressure)
            
            # Check if a cycle is already running
            cycle_running = False
            if hasattr(self.io, 'cycle_process') and self.io.cycle_process is not None:
                cycle_running = self.io.cycle_process.is_alive()
                        
            # If cycle is no longer running but test_cycle flag is still set, reset it
            # This ensures proper state when a cycle completes
            if not cycle_running and self.test_cycle:
                self.toggle_test_cycle(False)
                self.io.set_rest()
            
            # If in bleed mode and pressure has recovered above low limit, exit bleed mode
            if self.bleed and current_pressure >= float(self.test_low_limit):
                self.bleed = False
                self.io.set_rest()
            
            # If a cycle is running, just let it complete and continue monitoring
            if cycle_running:
                return
            
            # CASE 1: Pressure BELOW low limit - enter/stay in BLEED mode
            if current_pressure < float(self.test_low_limit):
                if not self.bleed:
                    Logger.info(f'TestMode: Pressure {current_pressure} below low limit {self.test_low_limit}, entering BLEED mode.')
                    self.bleed = True
                    self.io.set_bleed()
                return
            
            # CASE 2: Pressure ABOVE high limit - execute the appropriate cycle
            if current_pressure >= float(self.test_high_limit):
                # Handle the case where we need to immediately go from bleed to run mode
                if self.bleed:
                    Logger.info(f'TestMode: Pressure {current_pressure} above high limit {self.test_high_limit}, exiting BLEED mode and preparing for RUN cycle.')
                    self.bleed = False
                
                # Ensure we're not in a cycle state (double check)
                if not self.test_cycle and not cycle_running:
                    if self.test_cycle_counter >= 2:
                        # After 2 run cycles, do a purge cycle
                        Logger.info(f'TestMode: Pressure {current_pressure} above high limit {self.test_high_limit}, performing PURGE cycle after 2 runs.')
                        self.toggle_test_cycle(True)
                        
                        try:
                            rest_time_int = int(self.test_rest_time)
                            self.io.test_purge(rest_time=rest_time_int)
                            # Reset the counter after purge
                            self.test_cycle_counter = 0
                            Logger.info('TestMode: PURGE cycle completed, counter reset to 0.')
                        except (ValueError, TypeError) as e:
                            Logger.warning(f'TestMode: Error with timing values: {e}, using defaults')
                            self.io.test_purge()
                            self.test_cycle_counter = 0
                    else:
                        # Do a run cycle
                        Logger.info(f'TestMode: Pressure {current_pressure} above high limit {self.test_high_limit}, starting RUN cycle.')
                        self.toggle_test_cycle(True)
                        
                        try:
                            run_time_int = int(self.test_cycle_run_time)
                            rest_time_int = int(self.test_rest_time)
                            self.io.test_run(run_time=run_time_int, rest_time=rest_time_int)
                            # Increment counter immediately after starting the run
                            self.test_cycle_counter += 1
                            Logger.info(f'TestMode: RUN cycle started, counter incremented to {self.test_cycle_counter}.')
                        except (ValueError, TypeError) as e:
                            Logger.warning(f'TestMode: Error with timing values: {e}, using defaults')
                            self.io.test_run()
                            self.test_cycle_counter += 1
                else:
                    # We should never get here, but just in case log it
                    Logger.warning('TestMode: Unexpected state - cycle already running when trying to start a new one.')
            # End of high pressure check
        except (ValueError, AttributeError) as e:
            pass

    def toggle_test_cycle(self, state):
        '''Toggle the test cycle state.'''
        self.test_cycle = state
        
    def stop_test_mode(self):
        '''Stop the test mode for the MCP.'''
        Logger.info('TestMode: Stopping test mode and resetting parameters to defaults.')
        # Unschedule all test mode monitoring first
        Clock.unschedule(self.monitor_test_mode)
        Clock.unschedule(self.check_test_mode)
        
        # Stop all active cycles
        self.stop_any_cycle()
        
        # Clear all flags that might interfere with button states
        self.test_mode = False
        self.bleed = False
        self.test_cycle = False
        
        # Always explicitly set to rest mode when stopping test mode
        self.io.set_rest()
            
        # Reset all test-related values to defaults
        self.test_mode_start = 0
        self.test_low_limit = '-0.55'
        self.test_high_limit = '-0.35'
        self.test_rest_time = '5'
        self.test_cycle_run_time = '15'
        self.test_cycle_counter = 0
        
        # Log the operation
        Logger.info('TestMode: Test mode stopped and all parameters reset to defaults.')
        
    def update_test_mode_values(self, low_limit, high_limit, run_time, rest_time):
        '''Update test mode parameter values.'''
        self.test_low_limit = low_limit
        self.test_high_limit = high_limit
        self.test_cycle_run_time = run_time
        self.test_rest_time = rest_time

    def get_current_mode(self):
        '''Get the current mode of the MCP using ultra-fast memory-mapped file (replaces database).'''
        try:
            mode = self.io.mode_manager.get_mode()
        except Exception as e:
            Logger.error(f'Main: Error reading mode from ModeManager: {e}')
            mode = None
        if mode is not None:
            mode_string = self.language_handler.translate(mode, mode)
            self.current_mode = mode_string.upper()
        active_relays = self.io.get_values()
        if active_relays is None or active_relays == 'None':
            relay_string = self.language_handler.translate('none', 'none')
            self.active_relays = relay_string
        else:
            self.active_relays = active_relays if active_relays else self.language_handler.translate('none', 'none')

    def open_bottom_sheet(self, sheet):
        '''Open the bottom sheet.'''
        sheet.drawer_type = 'modal'
        sheet.set_state('toggle')

    def check_alarms(self, *args):
        '''Check for active alarms and update the alarm property.'''
        self.alarm_manager.check_alarms()
        active_alarms = set(self.alarm_manager.get_active_alarms())
        self.alarm = bool(active_alarms)
        if not self.alarm and self.shutdown:
            # Silence any active alarms
            self.alarm_silenced = True
            self.buzzer_triggered = False
            if hasattr(self, 'io') and hasattr(self.io, 'stop_buzzer'):
                self.io.stop_buzzer()
            # Clear any acknowledgement dialogs
            self.dialog = False
            # Clear alarm container widgets that might contain silence buttons
            shutdown_screen = self.get_screen('Shutdown')
            if shutdown_screen:
                shutdown_screen.ids.alarm_container.clear_widgets()
            # Toggle shutdown state off and return to Main screen
            self.toggle_shutdown(False)
            self.switch_screen('Main')
        new_alarms = active_alarms - self.alarm_list_last_check
        cleared_alarms = self.alarm_list_last_check - active_alarms
        if new_alarms:
            if not self.alarm_silenced:
                self.alarm_acknowledge_dialog()
            self.cycle_alarms()
        self.alarm_list_last_check = active_alarms
        if not self.shutdown:
            if self.test_shutdown_time:
                self.get_shutdown_time_remaining(self.modified_shutdown_time)
            else:
                self.get_shutdown_time_remaining()
        active_alarms = self.get_active_alarm_names()

    def set_test_shutdown_time(self, new_time):
        '''Toggle the test shutdown time.'''
        self.modified_shutdown_time = new_time
        self.test_shutdown_time = True
        self.toggle_shutdown(False)
        Logger.info(f'Application: Test shutdown time set to {new_time} seconds.')

    def reset_test_shutdown_time(self):
        '''Reset the test shutdown time.'''
        self.test_shutdown_time = False
        self.modified_shutdown_time = 0
        Logger.info('Application: Test shutdown time reset to default.')
        
    def get_active_alarm_names(self):
        '''Get the names of the active alarms.'''
        active_alarms = self.alarm_manager.get_active_alarms()
        if self.shutdown and '72_hour_shutdown' not in active_alarms:
            active_alarms.append('72_hour_shutdown')
        return active_alarms

    def cycle_alarms(self, *args):
        '''Cycle through the active alarms.'''
        self.alarm_list = self.get_active_alarm_names()
        if self.shutdown_pending:
            self.alarm_list.append('shutdown_pending')
        num_alarms = len(self.alarm_list)
        alarms_str = self.language_handler.translate('alarms', 'ALARMS')
        none_str = self.language_handler.translate('none', 'NONE')
        if num_alarms == 0:
            self.active_alarms = f'{alarms_str}: {none_str}'
            self.alarm_cycle_index = 0
        else:
            self.alarm_cycle_index = (self.alarm_cycle_index + 1) % num_alarms
            current_alarm = self.alarm_list[self.alarm_cycle_index]
            current_alarm_str = None
            if current_alarm == 'shutdown_pending':
                self.cycle_shutdown_alarm()
            else:
                # Convert 72_hour_shutdown to seventy_two_hour_shutdown for translation consistency
                translation_key = current_alarm
                if current_alarm == '72_hour_shutdown':
                    translation_key = 'seventy_two_hour_shutdown'
                
                current_alarm_str = self.language_handler.translate(translation_key, current_alarm.upper())
            if current_alarm_str:
                if num_alarms == 1:
                    self.active_alarms = f'{alarms_str}: {current_alarm_str}'
                else:
                    self.active_alarms = f'{alarms_str}: {current_alarm_str} + {num_alarms - 1}'

    def cycle_shutdown_alarm(self, *args):
        '''Add shutdown time to alarm cycle index.'''
        if not self.shutdown:
            shutdown_string = self.language_handler.translate('shutdown_in', 'Shutdown in')
            self.active_alarms = f'{shutdown_string.upper()}: {self.shutdown_time_remaining}'

    def get_screen(self, screen_name):
        '''Retrieve the screen object.'''
        try:
            return self.sm.get_screen(screen_name)
        except KeyError:
            return None

    def get_screen_property(self, screen_name, property_name):
        '''Retrieve the property of a screen.'''
        try:
            screen = self.sm.get_screen(screen_name)
            return getattr(screen, property_name)
        except AttributeError:
            return None

    def _clear_all_dialogs_and_buzzers(self):
        """Clear any existing dialogs and stop buzzers - prevents dialog stacking"""
        try:
            # Stop buzzer if active
            if self.buzzer_triggered:
                self.io.stop_buzzer()
                self.buzzer_triggered = False
            
            # Clear dialog flag
            self.dialog = False
            
            # Dismiss ALL dialog types to prevent any stacking
            AlarmDialog.dismiss_current_dialog()
            ConfirmationDialog.dismiss_current_dialog()
            TimeoutDialog.dismiss_current_dialog()
            LogoutDialog.dismiss_current_dialog()
        except Exception:
            # Fail silently - don't break anything
            pass

    def alarm_acknowledge_dialog(self, *args):
        '''Display an alarm acknowledge dialog.'''
        # Check if there are actually any active alarms before showing the dialog
        if not self.alarm_list or len(self.alarm_list) == 0:
            return
        
        # Clear existing dialogs first - new dialog always replaces old one
        self._clear_all_dialogs_and_buzzers()
        
        # Create new dialog
        self.dialog = True
        dialog = ConfirmationDialog()
        title = self.language_handler.translate('alarm_detected', 'Alarm Detected')
        text_one = self.language_handler.translate(
            'alarm_detected_message_one',
            'One or more alarms are currently active.'
        )
        text_two = self.language_handler.translate(
            'alarm_detected_message_two',
            'Please address and resolve these alarms immediately to maintain optimal system performance.'
        )
        text_three = self.language_handler.translate(
            'alarm_detected_message_three',
            'Contact your service contractor for assistance.'
        )
        text_four = self.language_handler.translate(
            'alarm_detected_message_four',
            'Select "Acknowledge" to silence the alarm.'
        )
        text = f'{text_one} {text_two} {text_three}\n\n{text_four}'
        accept = self.language_handler.translate('acknowledge', 'Acknowledge')
        dialog.open_dialog(
            title=title,
            text=text,
            accept=accept,
            accept_method=self.silence_alarm
        )
        self.sound_alarm()

    def sound_alarm(self):
        '''Start the alarm.'''
        self.io.start_buzzer(700, 0.5)
        self.buzzer_triggered = True
        alarm_button = self.create_silence_button()
        Logger.info(f'Alarm: Buzzer triggered. | {datetime.now():%Y%m%d %H:%M:%S}')
        if self.shutdown:
            shutdown_screen = self.get_screen('Shutdown')
            shutdown_screen.ids.alarm_container.clear_widgets()
            shutdown_screen.ids.alarm_container.add_widget(alarm_button)
        else:
            main_screen = self.get_screen('Main')
            main_screen.ids.alarm_container.clear_widgets()
            main_screen.ids.alarm_container.add_widget(alarm_button)

    def create_silence_button(self):
        '''Create the silence button.'''
        text = self.language_handler.translate('silence_alarm', 'Silence Alarm')
        return MDButton(
            MDButtonText(
                text=text.upper(),
                font_style='Title',
                role='medium'
            ),
            radius='5dp',
            on_press=self.silence_alarm
        )

    def silence_alarm(self, *args):
        '''Silence the alarm.'''
        self.dialog = False
        self.alarm_silenced = True
        self.buzzer_triggered = False
        
        # NEW: Add user action logging (SAFE ADDITION)
        active_alarms = ', '.join(self.alarm_list) if self.alarm_list else 'shutdown'
        Logger.info(f'User: Alarm silenced - {active_alarms} | {datetime.now():%Y%m%d %H:%M:%S}')
        
        self.io.stop_buzzer()
        Clock.schedule_once(self.unsilence_alarm, 4*60*60)
        if self.shutdown:
            shutdown_screen = self.get_screen('Shutdown')
            shutdown_screen.ids.alarm_container.clear_widgets()
        else:
            main_screen = self.get_screen('Main')
            main_screen.ids.alarm_container.clear_widgets()

    def unsilence_alarm(self, *args):
        '''Unsilence the alarm.'''
        self.alarm_silenced = False
        if any(profile in self.profile for profile in ['CS8', 'CS12']):
            # Only show the alarm dialog if there are active alarms
            if self.alarm and self.alarm_list and len(self.alarm_list) > 0:
                self.alarm_acknowledge_dialog()

    def shutdown_warning_dialog(self, warning_level):
        '''Display a shutdown warning dialog.'''
        # Clear existing dialogs first - new dialog always replaces old one
        self._clear_all_dialogs_and_buzzers()
        
        # Mark that we're showing a dialog
        self.dialog = True
        dialog = AlarmDialog()
        shutdown_warning_message = '''
        Your station will be shut down due to an alarm condition.
        Immediate action is required to resolve the issue.
        Please contact your Service Contractor for assistance.
        For more details, check the Alarms screen.
        '''
        title_start = self.language_handler.translate('shutdown_warning', 'Warning: Station Shutdown in')
        title = title_start
        time_remaining = self.shutdown_time_remaining
        text = self.language_handler.translate(
            'shutdown_warning_message',
            shutdown_warning_message
        )
        # Define the accept method based on warning level
        if warning_level == 1:
            accept_method = lambda: self.shutdown_warning_acknowledged(1)
        elif warning_level == 2:
            accept_method = lambda: self.shutdown_warning_acknowledged(2)
        elif warning_level == 3:
            accept_method = lambda: self.shutdown_warning_acknowledged(3)
        elif warning_level == 4:
            accept_method = lambda: self.shutdown_warning_acknowledged(4)
        accept = self.language_handler.translate('acknowledge', 'Acknowledge')
        # Use the defined accept_method, not self.silence_alarm
        dialog.open_dialog(
            title=title,
            text=text,
            accept=accept,
            accept_method=accept_method
        )
        self.shutdown_warning_acknowledged(warning_level)
        self.sound_alarm()

    def shutdown_warning_acknowledged(self, warning_level):
        '''Acknowledge the shutdown warning.'''
        # NEW: Add logging (SAFE ADDITION)
        Logger.info(f'User: Shutdown warning level {warning_level} acknowledged | {datetime.now():%Y%m%d %H:%M:%S}')
        
        # SIMPLIFIED: Just set the current level (SAFER THAN EXISTING)
        if warning_level == 1:
            self.shutdown_first_warning_acknowledged = True
        elif warning_level == 2:
            self.shutdown_second_warning_acknowledged = True
        elif warning_level == 3:
            self.shutdown_third_warning_acknowledged = True
        elif warning_level == 4:
            self.shutdown_fourth_warning_acknowledged = True

    def get_shutdown_time_remaining(self, shutdown_time=72*60):
        '''Get the time remaining until shutdown.'''
        if not self.alarm:
            self.shutdown_pending = False
            if self.shutdown:
                self.toggle_shutdown(False)
            return

        current_time = datetime.now()
        profile = self.profile or 'CS8'
        alarm_keys = self._get_alarm_keys_for_profile(profile)
        if not alarm_keys:
            return

        closest_time_remaining = self._process_alarms(alarm_keys, shutdown_time, current_time)

        if closest_time_remaining:
            self._update_shutdown_time_remaining(closest_time_remaining)

    def _get_alarm_keys_for_profile(self, profile):
        return {
            'CS8': [
                'low_pressure', 'high_pressure', 'under_pressure', 'over_pressure',
                'pressure_sensor', 'zero_pressure', 'variable_pressure', 'digital_storage', 'vac_pump'
            ],
            'CS9': ['vac_pump', 'pressure_sensor'],
            'CS12': ['pressure_sensor']
        }.get(profile, [])

    def _process_alarms(self, alarm_keys, shutdown_time, current_time):
        closest_time_remaining = None
        for alarm_key in alarm_keys:
            if alarm_key not in self.alarm_list:
                continue

            alarm_time_str = self.alarms_db.get_setting(f'{alarm_key}_start_time', None)
            if not alarm_time_str:
                self.shutdown_pending = False
                continue

            alarm_time = datetime.fromisoformat(alarm_time_str)
            time_elapsed = current_time - alarm_time
            time_remaining = timedelta(minutes=shutdown_time) - time_elapsed

            if closest_time_remaining is None or time_remaining < closest_time_remaining:
                closest_time_remaining = time_remaining

            self._handle_shutdown_notifications(time_elapsed, shutdown_time, current_time, time_remaining)

        return closest_time_remaining

    def _handle_shutdown_notifications(self, time_elapsed, shutdown_time, current_time, time_remaining):
        total_shutdown_time = timedelta(minutes=shutdown_time)
        warning_levels = [
            (total_shutdown_time - timedelta(hours=1), 4),   # 71 hours elapsed (1 hour remaining)
            (total_shutdown_time - timedelta(hours=25), 3),  # 47 hours elapsed (25 hours remaining)
            (total_shutdown_time - timedelta(hours=36), 2),  # 36 hours elapsed (36 hours remaining)
            (total_shutdown_time - timedelta(hours=48), 1),  # 24 hours elapsed (48 hours remaining)
        ]

        if time_elapsed >= total_shutdown_time:
            # NEW: Clear dialogs before shutdown (SAFE ADDITION)
            self._clear_all_dialogs_and_buzzers()
            self.toggle_shutdown(True)
            return

        for threshold, level in warning_levels:
            if time_elapsed >= threshold:
                self.shutdown_pending = True
                self._trigger_warning_dialog(level)
                break  # Only one warning level triggers

    def _trigger_warning_dialog(self, level):
        dialog_flags = {
            1: 'shutdown_first_warning_acknowledged',
            2: 'shutdown_second_warning_acknowledged',
            3: 'shutdown_third_warning_acknowledged',
            4: 'shutdown_fourth_warning_acknowledged',
        }
        flag = dialog_flags.get(level)
        if flag and not getattr(self, flag):
            self.shutdown_warning_dialog(level)

    def _update_shutdown_time_remaining(self, time_remaining):
        total_seconds = time_remaining.total_seconds()
        
        # NEW: Prevent negative display (SAFE ADDITION)
        if total_seconds <= 0:
            self.shutdown_time_remaining = '00:00:00'
            return
        
        hours, remainder = divmod(int(total_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        self.shutdown_time_remaining = f'{hours:02}:{minutes:02}:{seconds:02}'

    def _handle_sigint(self, sig, frame):
        '''Handle SIGINT (Ctrl+C) signal by force exiting.'''
        # Bypass all cleanup and exit immediately
        import signal
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        os.kill(os.getpid(), signal.SIGINT)
    
    def _cleanup_on_exit(self):
        '''Ensure clean shutdown of all components on exit.'''
        Logger.info('Application: Application exiting, performing cleanup..')
        try:
            try:
                Logger.debug('Application: Closing all database connections...')
                DatabaseManager.close_all_connections()
                Logger.debug('Application: Database connections closed')
            except Exception as db_error:
                Logger.debug(f'Application: Error closing database connections: {db_error}')
            if hasattr(self, 'io'):
                Logger.debug('Application: Cleaning up IOManager resources...')
                self.io.cleanup()
                Logger.debug('Application: IOManager cleanup complete')
            else:
                Logger.warning('Application: IOManager not initialized, skipping IO cleanup')
            Logger.debug('Application: Cleanup complete')
        except Exception as e:
            Logger.error(f'Application: Error during cleanup: {e}')
    
    def toggle_shutdown(self, state):
        '''Toggle the shutdown state.'''
        self.shutdown = state
        if self.shutdown:
            self.stop_all_cycles_including_manual()
            if not self.buzzer_triggered:
                self.sound_alarm()
            self.io.shutdown()
            self.switch_screen('Shutdown')
        else:
            # Reset all shutdown warning acknowledgements
            self.shutdown_first_warning_acknowledged = False
            self.shutdown_second_warning_acknowledged = False
            self.shutdown_third_warning_acknowledged = False
            self.shutdown_fourth_warning_acknowledged = False
            self.shutdown_pending = False
            self.io.set_rest()
            
            # Re-enable shutdown relay when 72-hour alarm is cleared
            self.io.set_shutdown_relay(True)
            Logger.info('Application: 72-hour shutdown cleared, shutdown relay re-enabled')
            
            # Clear the 72_hour_shutdown alarm from the database
            self.gm_db.add_setting('72_hour_shutdown_alarm', False)
            
            # Also clear the 72_hour_shutdown alarm start time
            self.alarms_db.add_setting('72_hour_shutdown_start_time', None)
            
            # Stop the buzzer and clear the alarm button
            self.io.stop_buzzer()
            self.buzzer_triggered = False
            
            # Clear the alarm button from both screens
            if hasattr(self, 'sm'):
                main_screen = self.get_screen('Main')
                if main_screen:
                    main_screen.ids.alarm_container.clear_widgets()
                
                shutdown_screen = self.get_screen('Shutdown')
                if shutdown_screen:
                    shutdown_screen.ids.alarm_container.clear_widgets()
            
            # If currently on the shutdown screen, go back to main screen
            if hasattr(self, 'sm') and self.sm.current == 'Shutdown':
                self.switch_screen('Main')

    def change_test_mode_duration(self, new_duration):
        '''Change the test mode duration.'''
        self.test_run_time = new_duration

    def archive_log_file(self, *args):
        '''Archive the log file if needed.'''
        if hasattr(self, 'log_archiver'):
            Logger.debug('Logfile: Starting log archive check...')
            Logger.debug(f'Logfile: Path: {self.log_archiver.log_path}')
            Logger.debug(f'Logfile: Archive dir: {self.log_archiver.archive_dir}')
            Logger.debug(f'Logfile: Max lines: {self.log_archiver.max_lines}')
            if self.log_archiver.log_path.exists():
                Logger.debug(f'Logfile: Current line count: {self.log_archiver.count_lines()}')
            archived = self.log_archiver.archive_if_needed()

    def cleanup_db(self, *args):
        '''Clean up old database records.'''
        if hasattr(self, 'notifications_cleaners'):
            Logger.debug("Application: Starting database cleanup...")
            total_deleted = 0
            for i, cleaner in enumerate(self.notifications_cleaners):
                Logger.debug(f'Application: Cleaning table {i+1}: {cleaner.table_name}, max records: {cleaner.max_records}')
                deleted = cleaner.cleanup_table()
                total_deleted += deleted
                Logger.debug(f'Application: Records deleted from {cleaner.table_name}: {deleted}')
            Logger.debug(f'Application: Total records deleted: {total_deleted}')


if __name__ == '__main__':
    # Set up argument parsing.
    parser = argparse.ArgumentParser(description='Run the Green Machine Control Panel application.')
    parser.add_argument('-s', '--screen', type=str, help='The initial screen to display.', default='Main')
    parser.add_argument('-d', '--developer', action='store_true', help='Enable developer mode.', default=False)
    args = parser.parse_args()
    # Pass the screen name to the application and set the startup_screen to the argument.
    app = ControlPanel(startup_screen=args.screen, developer_mode=args.developer)
    app.run()
