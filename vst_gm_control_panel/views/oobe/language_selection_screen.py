'''
Language Selection Screen
'''

# Kivy imports
from kivymd.uix.button import MDButton, MDButtonText
from kivy.properties import StringProperty

# Local imports
from .base_oobe_screen import BaseOOBEScreen
from components import NoDragMDBottomSheet
from utils.database_manager import DatabaseManager


class LanguageSelectionScreen(BaseOOBEScreen):
    '''
    Language Selection Screen:
    - This screen allows the user to select their preferred language.
    '''
    
    MAX_LENGTH = 4
    input_code = StringProperty('')

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.screen_title = "LANGUAGE SELECTION"
        
    def on_language_selected(self, language):
        '''
        Handle language selection.
        
        Args:
            language (str): The selected language code ('EN' or 'ES')
        '''
        # Update language in the app
        self.app.language_handler.switch_language(language)
        
        # Mark language selection as complete
        self.app.oobe_db.add_setting('language_selected', 'true')
        
        # Navigate to the next screen
        self.next_screen('OOBEProfileSelection')
    
    def open_test_keypad(self):
        '''
        Open the test keypad bottom sheet.
        '''
        self.input_code = ''
        self.ids.test_input_field.text = ''
        keypad_sheet = self.ids.test_keypad_sheet
        keypad_sheet.drawer_type = 'modal'
        keypad_sheet.set_state('toggle')
    
    def add_character(self, char):
        '''
        Add a character to the input field.
        
        Args:
            char: The character to add
        '''
        if len(self.input_code) < self.MAX_LENGTH:
            self.input_code += str(char)
            self.ids.test_input_field.text = '*' * len(self.input_code)
        else:
            self.input_code = str(char)
            self.ids.test_input_field.text = '*'
    
    def delete_character(self):
        '''
        Remove the last character from the input field.
        '''
        if len(self.input_code) >= 1:
            self.input_code = self.input_code[:-1]
            self.ids.test_input_field.text = '*' * len(self.input_code)
    
    def submit_code(self):
        '''
        Submit the code and check if it matches the test bypass code from auth.db.
        '''
        # Get bypass code from auth.db (persists across app.db rebuilds)
        auth_db = DatabaseManager.from_table('auth', 'sys/auth.db')
        test_bypass_code = auth_db.get_setting('test_bypass_code', '0917')
        
        if self.input_code == test_bypass_code:
            # Close the bottom sheet
            self.ids.test_keypad_sheet.set_state('toggle')
            
            # Skip to the main screen without modifying the database flags
            # This will only skip OOBE for the current session
            self.app.switch_screen('Main')
        else:
            # Reset the input field for incorrect code
            self.input_code = ''
            self.ids.test_input_field.text = ''