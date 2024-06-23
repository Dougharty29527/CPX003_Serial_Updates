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
from components import (
    DropdownMenu,
    SideBar,
    StatusBar,
    StatusBarSmall,
    TopBar
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
from views import MainScreen, TestScreen


class ControlPanel(MDApp):
    '''
    Main Application:
    - This class is used to configure the main application.
    '''

    SCREEN_CONFIG = {
        'Main': MainScreen,
        'Test': TestScreen
    }

    language = StringProperty()
    current_time = StringProperty()
    current_date = StringProperty()
    current_pressure = StringProperty()
    current_run_cycle_count = StringProperty()
    gm_status = StringProperty()
    run_cycle = BooleanProperty(False)
    run_cycle_interval = NumericProperty(43200)
    pin_delay_string = StringProperty('Pin Delay: 10 ms')
    run_cycle_check_interval_string = StringProperty('Run Cycle Check Interval: 720 min')
    debug_mode_string = StringProperty('Debug Mode: False')
    alarm = BooleanProperty(False)
    debug = BooleanProperty(False)

    _logger = Logger(__name__)
    _db = DatabaseManager()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._dir = os.path.dirname(__file__)
        self.log = self._logger.log_message
        self._translations_db = self._db.translations()
        self._user_db = self._db.user()
        self._gm_db = self._db.gm()
        self.sm = ScreenManager(transition=NoTransition())

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
        ''' Switch to the screen that was pressed. '''
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

    def get_datetime(self, *args) -> None:
        '''
        Purpose:
        - Get the current date and time.
        '''
        timezone_map = {'ES': 'Europe/Madrid', 'EN': 'America/New_York'}
        now_local = datetime.now(ZoneInfo(timezone_map.get(self.language, 'UTC')))
        self.set_locale()
        formatted_date = now_local.strftime('%A, %B %d')
        formatted_time = now_local.strftime('%I:%M')
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

    def get_pressure(self, *args) -> None:
        '''
        Purpose:
        - Get the current pressure reading.
        '''
        thresholds = PressureThresholds()
        self.current_pressure = self.pressure_sensor.get_pressure()
        if float(self.current_pressure) > float(thresholds.variable):
            self.start_run_cycle()

    def get_gm_status(self, *args):
        if self.run_cycle:
            gm_status = self.language_handler.translate('gm_active', 'active')
        else:
            gm_status = self.language_handler.translate('gm_idle', 'idle')
        self.gm_status = gm_status.upper()

    def check_last_run_cycle(self, *args):
        last_run_cycle = self._gm_db.get_setting('last_run_cycle')
        if last_run_cycle:
            last_run_time = datetime.fromisoformat(last_run_cycle)
            current_time = datetime.now()
            if current_time - last_run_time >= timedelta(seconds=self.run_cycle_interval):
                self.start_run_cycle()
        else:
            current_time = datetime.now().isoformat()
            self._gm_db.add_setting('last_run_cycle', current_time)

    def get_cycle_count(self):
        run_cycle_count = self._gm_db.get_setting('run_cycle_count')
        if run_cycle_count:
            self.current_run_cycle_count = str(run_cycle_count)
        else:
            self.current_run_cycle_count = '0'

    def start_run_cycle(self):
        self.run_cycle = True
        self.get_cycle_count()
        self.mcp.run_cycle()
        if self.mcp.mode == None or self.mcp.mode == 'Complete':
            self.run_cycle = False

    def set_run_cycle_interval(self, interval):
        self.run_cycle_interval = int(interval) * 60
        self.update_run_cycle_check_interval_string()

    def set_pin_delay(self, delay):
        delay_ms = int(delay) / 1000
        self.mcp.set_pin_delay(delay_ms)
        self.update_pin_delay_string()

    def update_run_cycle_check_interval_string(self):
        if self.run_cycle_interval:
            check_interval = int(self.run_cycle_interval / 60)
        else:
            check_interval = 720
        interval_string = self.language_handler.translate(
            'run_cycle_check_interval',
            'Run Cycle Check Interval'
        )
        self.run_cycle_check_interval_string = f'{interval_string}: {check_interval} min'

    def update_pin_delay_string(self):
        mcp_pin_delay = self.mcp.pin_delay
        if mcp_pin_delay:
            delay = int(mcp_pin_delay * 1000)
        else:
            delay = 10
        delay_string = self.language_handler.translate(
            'pin_delay',
            'Pin Delay'
        )
        self.pin_delay_string = f'{delay_string}: {delay} ms'

    def update_debug_mode_string(self):
        debug_string = self.language_handler.translate(
            'debug',
            'debug'
        )
        if self.debug:
            debug_value = self.language_handler.translate(
                'true',
                'true'
            )
        else:
            debug_value = self.language_handler.translate(
                'false',
                'false'
            )
        self.debug_mode_string = f'{debug_string}: {debug_value}'

    def restore_defaults(self):
        self.debug = False
        self.run_cycle_interval = 43200
        self.set_pin_delay(10)

    def toggle_debug(self):
        self.debug = not self.debug
        self.update_debug_mode_string()

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
        self.language_handler = LanguageHandler()
        self.pressure_sensor = PressureSensor()
        self.mcp = MCP()
        self.language_handler.load_user_language()
        self.get_datetime()
        self.get_cycle_count()
        self.set_update_intervals()
        self.load_all_kv_files()
        self.configure_screen_manager()
        self.dropdown_menu = DropdownMenu()
        self.update_pin_delay_string()
        self.update_run_cycle_check_interval_string()
        Clock.schedule_once(self.language_handler.check_all_screens, 0)
        Clock.schedule_once(self.check_last_run_cycle, 0)
        return self.sm

if __name__ == '__main__':
    ControlPanel().run()
