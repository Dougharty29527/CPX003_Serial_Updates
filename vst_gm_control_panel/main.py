#!/usr/bin/python3

'''
========================================
Green Machine Control Panel Application
========================================

Author: Tommy Wallace
Date: June 2024
License: Vapor Systems Technologies

Overview:
The Control Panel Application is designed to interface with and monitor the VST Green Machine.

Features:
- Real-time monitoring of Green Machine operational status
- Remote adjustment of settings and configurations
- Historical data analysis and reporting
- Automated alerts and maintenance notifications

Usage:
- To start the application, ensure you have Python 3.9 or higher installed, 
    and run the following command in your terminal:
    
        python3 main.py

'''

# Initial config for kv must be imported first.
import data.config.settings

# Standard imports.
from datetime import datetime, timedelta
import locale
import os
import socket
import subprocess
from zoneinfo import ZoneInfo

# Kivy imports.
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import BooleanProperty, StringProperty, NumericProperty
from kivy.uix.screenmanager import NoTransition, ScreenManager
from kivymd.app import MDApp
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.screen import MDScreen
from kivymd.uix.widget import Widget

# Third party imports.
from materialyoucolor.utils.platform_utils import SCHEMES

# Local imports.
from __init__ import __version__
from views.pages import (
    MainScreen,
    TestScreen,
    TimeEntryScreen
)
from views.components import (
    DropdownMenu,
    StatusBar,
    TopBar,
    NavDrawerItem,
    SideBar,
    NoDragMDBottomSheet,
    Diagnostics
)
from controllers import (
    PressureSensor,
    PressureThresholds,
    MCP
)
from utils import (
    DatabaseManager,
    LanguageHandler,
    Logger
)


class ControlPanel(MDApp):
    '''
    Main Application:
    - This class is used to configure the main application.
    '''

    SCREEN_CONFIG = {
        'Main': MainScreen,
        'Test': TestScreen,
        'TimeEntry': TimeEntryScreen
    }

    language = StringProperty()
    current_time = StringProperty()
    current_date = StringProperty()
    current_pressure = StringProperty()
    current_run_cycle_count = StringProperty()
    gm_status = StringProperty()
    current_mode = StringProperty('rest')
    active_relays = StringProperty('none')
    run_cycle = BooleanProperty(False)
    run_cycle_interval = NumericProperty(43200)
    pin_delay_string = StringProperty('Pin Delay: 10 ms')
    run_cycle_check_interval_string = StringProperty('Run Cycle Check Interval: 720 min')
    debug_mode_string = StringProperty('Debug Mode: False')
    alarm = BooleanProperty(False)
    debug = BooleanProperty(False)
    recent_notification = StringProperty('No Recent Notifications')
    manual_time_set = BooleanProperty(False)
    accepted_dialog = BooleanProperty(False)
    manual_time_set = BooleanProperty(False)

    _logger = Logger(__name__)
    _db = DatabaseManager()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._dir = os.path.dirname(__file__)
        self.log = self._logger.log_message
        self._gm_db = self._db.gm()
        self._translations_db = self._db.translations()
        self._user_db = self._db.user()
        self.language_handler = LanguageHandler()
        self.sm = ScreenManager(transition=NoTransition())

    def setup_io(self):
        '''
        Purpose:
        - Setup the input/output for the application.
        '''
        self.pressure_sensor = PressureSensor()
        self.mcp = MCP()

    def get_gm_settings(self):
        '''
        Purpose:
        - Get the Green Machine settings.
        '''
        self.get_cycle_count()
        self.update_pin_delay_string()
        self.update_run_cycle_check_interval_string()
        self.recent_notification = self.get_latest_update()

    def get_user_settings(self):
        '''
        Purpose:
        - Get the user settings from the database.
        '''
        self.language_handler.load_user_language()

    def load_all_kv_files(self) -> None:
        '''
        Purpose:
        - Load all .kv files in the application directory.
        '''
        for root, _, files in os.walk(self._dir):
            for file in files:
                if file.endswith('.kv'):
                    Builder.load_file(os.path.join(root, file))

    def configure_screen_manager(self) -> None:
        '''
        Purpose:
        - Configure the Screen Manager.
        '''
        for screen_name, screen_class in self.SCREEN_CONFIG.items():
            self.sm.add_widget(screen_class(self, name=screen_name))

    def switch_screen(self, screen_name='Main'):
        '''
        Purpose:
        - Switch the screen to the specified screen.
        Parameters:
        - screen_name: The name of the screen to switch to (str).
        '''
        self.sm.current = screen_name

    def switch_language(self, selected_language) -> None:
        '''
        Purpose:
        - Switch the language and go back to the settings menu.
        Parameters:
        - selected_language: The selected language (str).
        '''
        self.language = selected_language
        self.language_handler.save_user_language(self.language)
        self.get_datetime()
        self.language_handler.check_all_screens()
        self.update_pin_delay_string()
        self.update_run_cycle_check_interval_string()
        self.update_debug_mode_string()

    def check_manual_time(self):
        '''
        Purpose:
        - Check if the time has been manually set.
        '''
        manual_time = self._user_db.get_setting('manual_time_set')
        if manual_time:
            self.manual_time_set = True

    def get_datetime(self, *args) -> None:
        '''
        Purpose:
        - Get the current date and time.
        '''
        now_local = datetime.now()
        timezone_map = {'ES': 'Europe/Madrid', 'EN': 'America/New_York'}
        now_local = datetime.now(ZoneInfo(timezone_map.get(self.language, 'UTC')))
        self.set_locale()
        formatted_date = now_local.strftime('%A, %B %d')
        formatted_time = now_local.strftime('%H:%M')
        self.current_time = formatted_time
        self.current_date = formatted_date

    def set_locale(self) -> None:
        '''
        Purpose:
        - Set the locale for the application.
        '''
        locale_map = {'ES': 'es_ES.UTF-8', 'EN': 'en_US.UTF-8'}
        locale.setlocale(locale.LC_TIME, locale_map.get(self.language, 'en_US.UTF-8'))

    def set_update_intervals(self) -> None:
        '''
        Purpose:
        - Set the update intervals for the application.
        '''
        Clock.schedule_interval(self.get_datetime, 30)
        Clock.schedule_interval(self.get_pressure, 1)
        Clock.schedule_interval(self.get_gm_status, 1)
        Clock.schedule_interval(self.check_last_run_cycle, 60)
        Clock.schedule_once(self.language_handler.check_all_screens, 0)
        Clock.schedule_once(self.check_last_run_cycle, 0)
        # Clock.schedule_interval(self.log_fps, 1)

    def log_fps(self, *args):
        '''
        Purpose:
        - Log the current FPS.
        '''
        logger = Logger('fps')
        logger.log_message('info', f'FPS: {Clock.get_rfps()}')

    def get_pressure(self, *args) -> None:
        '''
        Purpose:
        - Get the current pressure reading.
        '''
        thresholds = PressureThresholds()
        current_pressure = self.pressure_sensor.get_pressure()
        if self.language == 'EN':
            self.current_pressure = f'{current_pressure} IWC'
        else:
            self.current_pressure = current_pressure
        if float(current_pressure) > float(thresholds.variable):
            self.start_run_cycle()

    def calibrate_pressure_sensor(self):
        '''
        Purpose:
        - Calibrate the pressure sensor.
        '''
        self.pressure_sensor.calibrate()

    def get_gm_status(self, *args):
        '''
        Purpose:
        - Get the current status of the Green Machine.
        '''
        gm = self.language_handler.translate('gm_status', 'GREEN MACHINE STATUS')
        if self.mcp.cycle_thread is None:
            self.run_cycle = False
            status = self.language_handler.translate('gm_idle', 'IDLE')
            self.gm_status = f'{status.upper()}'
        else:
            self.run_cycle = True
            status = self.language_handler.translate('gm_active', 'ACTIVE')
            self.gm_status = f'{status.upper()}'
        self.get_current_mode()

    def check_last_run_cycle(self, *args):
        '''
        Purpose:
        - Check the last run cycle and start a new one if necessary.
        '''
        last_run_cycle = self._gm_db.get_setting('last_run_cycle')
        if last_run_cycle is None:
            current_time = datetime.now().isoformat()
            self._gm_db.add_setting('last_run_cycle', current_time)
        else:
            last_run_time = datetime.fromisoformat(last_run_cycle)
            current_time = datetime.now()
            if current_time - last_run_time >= timedelta(seconds=self.run_cycle_interval):
                self.start_run_cycle()

    def get_cycle_count(self):
        '''
        Purpose:
        - Get the current run cycle count.
        '''
        run_cycle_count = self._gm_db.get_setting('run_cycle_count')
        if run_cycle_count:
            self.current_run_cycle_count = str(run_cycle_count)
        else:
            self.current_run_cycle_count = '0'

    def start_run_cycle(self):
        '''
        Purpose:
        - Start the run cycle for the MCP.
        '''
        self.run_cycle = True
        self.get_cycle_count()
        self.mcp.run_cycle()
        now = datetime.now()
        dt = now.strftime('%Y-%m-%d %H:%M:%S')
        notification = self.language_handler.translate(
            'run_sequence_notification',
            'Run Sequence Initiated'
        )
        self._user_db.add_setting('latest_notification', f'{dt}: {notification}')
        self.recent_notification = f'{dt}: {notification}'

    def get_current_mode(self):
        '''
        Purpose:
        - Get the current mode of the MCP.
        '''
        current_mode = self.mcp.get_mode()
        if current_mode:
            mode_string = self.language_handler.translate(current_mode, current_mode)
            if mode_string is not None:
                self.current_mode = mode_string.upper()
        active_relays = self.mcp.get_values()
        if active_relays == 'None':
            relay_string = self.language_handler.translate('none', 'none')
            self.active_relays = relay_string
        else:
            self.active_relays = active_relays

    def set_run_cycle_interval(self, interval):
        '''
        Purpose:
        - Set the run cycle interval for the run cycle check.
        Parameters:
        - interval: The interval in minutes (int).
        '''
        self.run_cycle_interval = int(interval) * 60
        self.update_run_cycle_check_interval_string()

    def set_pin_delay(self, delay):
        '''
        Purpose:
        - Set the pin delay for the MCP.
        Parameters:
        - delay: The delay in milliseconds (int).
        '''
        delay_ms = int(delay) / 1000
        self.mcp.set_pin_delay(delay_ms)
        self.update_pin_delay_string()

    def update_run_cycle_check_interval_string(self):
        '''
        Purpose:
        - Update the run cycle check interval string.
        '''
        if self.run_cycle_interval:
            check_interval = int(self.run_cycle_interval / 60)
        else:
            check_interval = 720
        self.run_cycle_check_interval_string = f'{check_interval} min'

    def update_pin_delay_string(self):
        '''
        Purpose:
        - Update the pin delay string.
        '''
        mcp_pin_delay = self.mcp.pin_delay
        if mcp_pin_delay:
            delay = int(mcp_pin_delay * 1000)
        else:
            delay = 10
        self.pin_delay_string = f'{delay} ms'

    def update_debug_mode_string(self):
        '''
        Purpose:
        - Update the debug mode string.
        '''
        debug_string = self.language_handler.translate('debug', 'debug')
        self.debug_mode_string = debug_string.upper()

    def restore_defaults(self):
        '''
        Purpose:
        - Restore the default application settings.
        '''
        self.debug = False
        self.set_run_cycle_interval(720)
        self.set_pin_delay(10)

    def toggle_debug(self):
        '''
        Purpose:
        - Toggle the debug mode.
        '''
        self.debug = not self.debug
        self.update_debug_mode_string()

    def get_latest_update(self):
        '''
        Purpose:
        - Get the latest notification.
        '''
        recent_notification = self._user_db.get_setting('latest_notification')
        if recent_notification:
            return recent_notification
        return 'No Recent Notifications'

    def open_bottom_sheet(self, sheet):
        '''
        Purpose:
        - Open the bottom sheet.
        Parameters:
        - sheet: The bottom sheet to open (NoDragMDBottomSheet).
        '''
        sheet.drawer_type = 'modal'
        sheet.set_state('toggle')

    def restart_service(self):
        '''
        Purpose:
        - Restart the GM Control Panel service.
        '''
        try:
            subprocess.run(['sudo', 'systemctl', 'stop', 'gm_control_panel.service'])
            subprocess.run(['sudo', 'systemctl', 'start', 'gm_control_panel.service'])
        except subprocess.CalledProcessError as e:
            self.log(f'Error restarting service: {e}')

    def reboot_machine(self):
        '''
        Purpose:
        - Reboot the machine.
        '''
        try:
            subprocess.run(['sudo', 'reboot'])
        except subprocess.CalledProcessError as e:
            self.log(f'Error rebooting machine: {e}')

    def build(self) -> ScreenManager:
        '''
        Purpose:
        - Build the main application.
        Returns:
        - ScreenManager: The main application.
        '''
        self.title = 'VST: Green Machine Control Panel'
        self.icon = os.path.join(self._dir, 'assets', 'images', 'vst_light.png')
        self.theme_cls.primary_palette = 'Steelblue'
        self.theme_cls.theme_style = 'Dark'
        self.software = 'CPX-003'
        self.software_version = __version__
        self.device_name = socket.gethostname().upper()
        self.setup_io()
        self.get_user_settings()
        self.check_manual_time()
        self.get_datetime()
        self.get_gm_settings()
        self.set_update_intervals()
        self.load_all_kv_files()
        self.configure_screen_manager()
        self.dropdown_menu = DropdownMenu()
        return self.sm

if __name__ == '__main__':
    ControlPanel().run()
