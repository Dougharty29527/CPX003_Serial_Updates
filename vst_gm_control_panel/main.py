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
    _dir = os.path.dirname(__file__)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        self.sm = ScreenManager(transition=NoTransition())

    def load_all_kv_files(self):
        ''' Load all KV files. '''
        for root, _, files in os.walk(os.path.dirname(__file__)):
            for file in files:
                if file.endswith('.kv'):
                    Builder.load_file(os.path.join(root, file))

    def screen_config(self):
        ''' Return a list of screen names and classes. '''
        return {
            'Main': MainScreen
        }

    def configure_screen_manager(self):
        ''' Configure the screen manager. '''
        for screen_name, screen_class in self.screen_config().items():
            self.sm.add_widget(screen_class(name=screen_name))

    def build(self):
        ''' Build the application. '''
        self.title = 'VST: Green Machine Control Panel'
        self.icon = os.path.join('assets', 'images', 'vst_dark.png')
        self.theme_cls.primary_palette = 'Steelblue'
        self.theme_cls.theme_style = 'Dark'
        self.load_all_kv_files()
        self.configure_screen_manager()
        return self.sm
        

if __name__ == '__main__':
    ControlPanel().run()
