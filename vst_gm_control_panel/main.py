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

# Standard imports.
from datetime import datetime
import locale
import os
from zoneinfo import ZoneInfo

# Kivy imports.
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.screenmanager import NoTransition, ScreenManager
from kivymd.app import MDApp
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.screen import MDScreen
from kivymd.uix.widget import Widget

# Third party imports.
from materialyoucolor.utils.platform_utils import SCHEMES


# Local imports.
from components import DropdownMenu, SideBar
from utils import DatabaseManager, Logger
from views import MainScreen


class ControlPanel(MDApp):
    '''
    Main Application:
    - This class is used to configure the main application.
    '''

    HEIGHT: int = 800
    WIDTH: int = 480

    SCREEN_CONFIG = {
        'Main': MainScreen
    }

    language = StringProperty()
    current_time = StringProperty()
    current_date = StringProperty()

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
        self.language = self._user_db.get_setting('language')

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

    def translate(self, key) -> str:
        '''
        Purpose:
        - Translate a key to the current language.
        Parameters:
        - key: The key to translate (str).
        Returns:
        - str: The translated key.
        '''
        return self._translations_db.translate(self.language, key)

    def walk_widget_tree(self, widget):
        '''
        Purpose:
        - Walk the widget tree.
        '''
        if hasattr(widget, 'ids'):
            for key, val in widget.ids.items():
                if hasattr(val, 'text'):
                    print(f'{key}: {val.text}')
            for child in widget.children:
                self.walk_widget_tree(child)

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
        self.configure_application()
        self.load_user_language()
        self.load_all_kv_files()
        self.configure_screen_manager()
        Clock.schedule_once(lambda dt: self.walk_widget_tree(MDApp.get_running_app().root), 0)
        return self.sm


if __name__ == '__main__':
    ControlPanel().run()
