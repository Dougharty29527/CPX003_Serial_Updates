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
                    translated_text = self.app.translate(key)
                    if translated_text is not None:
                        val.text = translated_text.upper()
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
                title = self.app.translate(screen_name, screen_name)
                val.screen_title = title.upper()