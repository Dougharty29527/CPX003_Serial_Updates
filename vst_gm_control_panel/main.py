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
    TopBar
)
from controllers import (
    PressureSensor,
    PressureThresholds,
    MCP
)
from utils import DatabaseManager, Logger
from views import MainScreen, TestScreen


class ControlPanel(MDApp):
    '''
    Main Application:
    - This class is used to configure the main application.
    '''

    HEIGHT: int = 800
    WIDTH: int = 480

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
    alarm = BooleanProperty(False)
    debug = BooleanProperty(False)

    _logger = Logger(__name__)
    _db = DatabaseManager()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._dir = os.path.dirname(__file__)
        self.dropdown_menu = DropdownMenu()
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

    def load_user_language(self) -> None:
        '''
        Purpose:
        - Load the user's preferred language.
        '''
        language = self._user_db.get_setting('language')
        if language is None:
            language = 'EN'
            self.save_user_language(language)
        self.language = language

    def save_user_language(self, user_language=None) -> None:
        '''
        Purpose:
        - Save the user's preferred language.
        Parameters:
        - user_language (optional): The user's preferred language (str).
        '''
        if user_language:
            self.language = user_language
        self._user_db.add_setting('language', self.language)

    def switch_language(self, selected_language) -> None:
        '''
        Purpose:
        - Switch the language and go back to the settings menu.
        Parameters:
        - selected_language: The selected language (str).
        '''
        self.language = selected_language
        self.save_user_language()
        self.get_datetime()
        # self.walk_widget_tree(MDApp.get_running_app().root)
        self.check_all_screens()

    def translate(self, key, default=None) -> str:
        '''
        Purpose:
        - Translate a key to the current language.
        Parameters:
        - key: The key to translate (str).
        Returns:
        - str: The translated key.
        '''
        translation = self._translations_db.translate(self.language, key)
        if translation is None:
            if default:
                translation = default
            else:
                self.log('error', f'No translation found for key: {key}')
        return translation

    def walk_widget_tree(self, widget):
        '''
        Purpose:
        - Walk the widget tree and perform translations.
        '''
        # Check if widget has 'ids' attribute and it's not empty.
        if hasattr(widget, 'ids') and widget.ids:
            for key, val in widget.ids.items():
                # Translate and update text if applicable
                if hasattr(val, 'text'):
                    translated_text = self.translate(key)
                    if translated_text is not None:
                        val.text = translated_text.upper()
                # Check if val is an instance of TopBar and key is 'title'
                if key == 'main_screen':
                    main_screen = self.translate('main', 'main')
                    val.screen_title = main_screen.upper()
                if key == 'test_screen':
                    test_screen = self.translate('test', 'test')
                    val.screen_title = test_screen.upper()
        # Recursively walk through children widgets
        for child in widget.children:
            self.walk_widget_tree(child)

    def check_all_screens(self, *args):
        '''
        Purpose:
        - Iterate through all screens in ScreenManager and apply walk_widget_tree
        '''
        for screen in self.sm.screens:
            self.walk_widget_tree(screen)

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
        Clock.schedule_interval(self.get_gm_status, .5)
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
            self.gm_status = self.translate('gm_active', 'Active').upper()
        else:
            self.gm_status = self.translate('gm_idle', 'Idle').upper()

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
        if self.debug:
            self.mcp.run_cycle_debug()
        else:
            self.mcp.run_cycle()
        if self.mcp.mode == None or self.mcp.mode == 'Complete':
            self.run_cycle = False

    def set_run_cycle_interval(self, interval):
        self.run_cycle_interval = int(interval) * 60

    def set_pin_delay(self, delay):
        delay_ms = int(delay) / 1000
        self.mcp.set_pin_delay(delay_ms)

    def restore_defaults(self):
        self.debug = False
        self.run_cycle_interval = 43200
        self.set_pin_delay(10)

    def toggle_debug(self):
        self.debug = not self.debug

    def switch_screen(self, screen_name='main_screen'):
        ''' Switch to the screen that was pressed. '''
        self.sm.current = screen_name

    def configure_application(self) -> None:
        '''
        Purpose:
        - Configure the application.
        '''
        self.title = 'VST: Green Machine Control Panel'
        self.icon = os.path.join(self._dir, 'assets', 'images', 'vst_light.png')
        self.theme_cls.primary_palette = 'Steelblue'
        self.theme_cls.theme_style = 'Dark'
        Window.size = (self.HEIGHT, self.WIDTH)

    def build(self) -> ScreenManager:
        '''
        Purpose:
        - Build the main application.
        Returns:
        - ScreenManager: The main application.
        '''
        self.log = self._logger.log_message
        self._translations_db = self._db.translations()
        self._user_db = self._db.user()
        self._gm_db = self._db.gm()
        self.pressure_sensor = PressureSensor()
        self.mcp = MCP()
        self.mcp.set_rest()
        self.configure_application()
        self.load_user_language()
        self.get_datetime()
        self.get_cycle_count()
        self.set_update_intervals()
        self.load_all_kv_files()
        self.configure_screen_manager()
        Clock.schedule_once(self.check_all_screens, 0)
        Clock.schedule_once(self.check_last_run_cycle, 0)
        # Clock.schedule_once(lambda dt: self.walk_widget_tree(MDApp.get_running_app().root), 0)
        return self.sm

if __name__ == '__main__':
    ControlPanel().run()
