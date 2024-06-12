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