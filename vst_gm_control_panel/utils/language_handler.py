'''
Module for handling language translations.
'''

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
        self.log = _logger.log_message
        self._user_db = self._db.user()
        self._translations_db = self._db.translations()
        self.language = self.load_user_language()
        self.app = MDApp.get_running_app()

    def load_user_language(self):
        '''
        Purpose:
        - Load the user's language from the database.
        '''
        language = self._user_db.get_setting('language')
        if language is None:
            language = 'EN'
            self.save_user_language(language)
        return language

    def save_user_language(self, language):
        '''
        Purpose:
        - Save the user's language to the database.
        Parameters:
        - language: str
        '''
        self._user_db.add_setting('language', language)

    def translate_text(self, key, default=None):
        '''
        Purpose:
        - Translate a key to the user's language.
        Parameters:
        - key: str
        - default: str (optional)
        '''
        translation = self._translations_db.translate(self.language, key)
        if translation is None:
            self.log('error', f'No translation found for key: {key}')
            return default
        return key

    def switch_language(self, selected_language):
        '''
        Purpose:
        - Switch the language of the app.
        Parameters:
        - selected_language: str
        '''
        self.language = selected_language
        self.save_user_language(selected_language)

    def walk_app_widget_tree(self, widget):
        '''
        Purpose:
        - Walk the app's widget tree and translate text.
        Parameters:
        - widget: kivy.uix.widget
        '''
        # Check if widget has 'ids' attribute and it's not empty.
        if hasattr(widget, 'ids') and widget.ids:
            for key, val in widget.ids.items():
                # Translate and update text if available.
                if hasattr(val, 'text'):
                    translated_text = self.translate(key)
                if translated_text:
                    val.text = translated_text.upper()
                self.udpate_screen_title(key, val)
        for child in widget.children:
            self.walk_app_widget_tree(child)

    def update_screen_title(self, key, val):
        screens = {
            'main_screen': 'main',
            'test_screen': 'test'
        }
        for screen, screen_name in screens.items():
            if key == screen:
                title = self.translate(screen_name, screen_name)
                val.screen_title = title.upper()

    def check_all_screens(self, *args):
        '''
        Purpose:
        - Check all screens for translations.
        '''
        for screen in self.app.sm.screens:
            self.walk_app_widget_tree(screen)