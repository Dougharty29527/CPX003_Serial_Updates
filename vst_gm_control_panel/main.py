#!/usr/bin/python3

'''
============================================================
        VST: Green Machine Control Panel Application
============================================================

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
To start the application, ensure you have Python 3.9 or higher installed, 
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
from kivy.utils import hex_colormap
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonIcon, MDButtonText
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.navigationdrawer import MDNavigationLayout
from kivymd.uix.navigationrail import MDNavigationRailItem
from kivymd.uix.screen import MDScreen
from materialyoucolor.utils.platform_utils import SCHEMES

# Local imports.
from utils import DatabaseManager, Logger
from views import MainScreen


class ControlPanel(MDApp):
    '''
    Main Application
    ----------------
    This class is used to configure the main application.
    '''

    _logger = Logger(__name__)
    log = _logger.log_message
    lang = StringProperty('EN')
    current_time = StringProperty()
    current_date = StringProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        self.translations = self.load_translations()
        self.sm = ScreenManager(transition=NoTransition())

    def load_translations(self):
        ''' Load the translations from the database. '''
        self.translation_db = self.db.translations()
        return self.translation_db.load_translations('EN')

    def screen_config(self):
        ''' Return a list of screen classes and names. '''
        return [
            (MainScreen, 'main')
        ]

    def setup_screens(self):
        ''' Load the screens into the screen manager. '''
        for cls, name in self.screen_config():
            self.sm.add_widget(cls(name=name))

    def build(self):
        ''' Build the application. '''
        self.setup_screens()
        return self.sm


if __name__ == '__main__':
    ControlPanel().run()