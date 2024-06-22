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

    def switch_language(self, selected_language):
        '''
        Purpose:
        - Switch the language of the app.
        Parameters:
        - selected_language: str
        '''
        self.language = selected_language
        self.save_user_language(selected_language)

    def translate(self, key, default=None):
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
            if default is None:
                default = key
            translation = default
        return key
            