'''
Module for handling language translations.
'''

# Standard imports.
import locale
from datetime import datetime
from zoneinfo import ZoneInfo

# Kivy imports.
from kivymd.app import MDApp

# Local imports.
from .database_manager import DatabaseManager
from .logger import Logger

class LanguageHandler:
    '''
    Class for handling language translations.
    '''

    _db = DatabaseManager()
    _logger = Logger(__name__)
    
    def __init__(self):
        self.app = MDApp.get_running_app()
        self.log = self._logger.log_message
        self.language = self.load_user_language()

    def load_user_language(self):
        '''
        Purpose:
        - Load the user's language from the database.
        '''
        language = self.app._user_db.get_setting('language')
        if language is None:
            language = 'EN'
            self.save_user_language(language)
        self.app.language = language

    def save_user_language(self, language):
        '''
        Purpose:
        - Save the user's language to the database.
        Parameters:
        - language: str
        '''
        self.app._user_db.add_setting('language', language)

    def translate(self, key, default=None) -> str:
        '''
        Purpose:
        - Translate a key to the current language.
        Parameters:
        - key: The key to translate (str).
        Returns:
        - str: The translated key.
        '''
        language = self.app.language
        translation = self.app._translations_db.translate(language, key)
        if translation is None:
            if default:
                translation = default
            self.log('error', f'No translation found for key: {key}')
        return translation

    def walk_app_widget_tree(self, widget):
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
                    if key == 'pin_delay_0':
                        pin_delay = self.translate('pin_delay', 'pin_delay')
                        if pin_delay is not None:
                            val.text = pin_delay.upper()
                    if key == 'run_cycle_check_interval_0':
                        interval_check = self.translate('run_cycle_check_interval', 'run_cycle_check_interval')
                        if interval_check is not None:
                            val.text = interval_check.upper()
                    if key == 'gm_status_0':
                        gm = self.translate('gm_status', 'gm_status')
                        if gm is not None:
                            val.text = gm.upper()
                self.update_screen_title(key, val)
        # Recursively walk through children widgets
        for child in widget.children:
            self.walk_app_widget_tree(child)

    def update_screen_title(self, key, val):
        for screen, screen_name in {
            'main_screen': 'main',
            'test_screen': 'test'
        }.items():
            if key == screen:
                title = self.translate(screen_name, screen_name)
                val.screen_title = title.upper()

    def check_all_screens(self, *args):
        '''
        Purpose:
        - Iterate through all screens in ScreenManager and apply walk_widget_tree
        '''
        for screen in self.app.sm.screens:
            self.walk_app_widget_tree(screen)