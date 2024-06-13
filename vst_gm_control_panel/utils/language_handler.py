'''
language_handler.py
'''


# Local imports.
from .database_manager import DatabaseManager
from .logger import Logger


class LanguageHandler:
    '''
    Language Handler:
    - Class to handle translation operations.
    '''

    _logger = Logger(__name__)
    _db = DatabaseManager()

    def __init__(self):
        self.log = self._logger.log_message
        self.translations_db = self._db.translations()
        self.user_db = self._db.user()
        self.lang = self.load_user_language_setting()
        self.translations = self.load_translations()

    def load_user_language_setting(self):
        '''
        Returns:
        - str: The language setting of the user.
        '''
        user_language = self.user_db.get_setting('language')
        return user_language if user_language else 'EN'

    def save_user_language_setting(self):
        '''
        Saves to user database:
        - The language setting of the user.
        '''
        self.user_db.add_setting('language', self.lang)

    def load_translations(self):
        '''
        Returns:
        - dict: A dictionary containing the translations.
        '''
        return self.translations_db.load_translations(self.lang, 'EN')

    def translate_text(self, key, default=None):
        '''
        Parameters:
        - key (str): The key to translate.
        - default (str): The default value to return if the key is not found.
        Returns:
        - str: The translated text.
        '''
        if default is None:
            default = key
        return self.user_db.get_translation(key, default)