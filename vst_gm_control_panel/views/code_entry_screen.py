'''
Code Entry Screen
'''

# Standard imports.
from datetime import datetime
import os

# Kivy imports.
from kivy.clock import Clock
from kivymd.uix.screen import MDScreen
from kivy.properties import StringProperty
from kivy.logger import Logger


class CodeEntryScreen(MDScreen):
    '''
    CodeEntryScreen:
    - This class sets up the Code Entry Screen.
    '''

    MAX_LENGTH = 4
    previous_screen = StringProperty('')

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app

    def on_enter(self):
        '''
        Called when the screen is entered (becomes active).
        - Store the screen we came from
        - Ensure any running cycles are stopped for safety
        '''
        # Store the screen we came from, excluding CodeEntry itself
        if self.app.sm.current != 'CodeEntry':
            self.previous_screen = self.app.sm.current  
        # Safety measure: Always stop any cycles when entering System Config screen
        self.app.stop_any_cycle()

    def add_character(self, char):
        '''
        Add a character to the input field.
        '''
        current_text = self.ids.user_input_field.text

        if len(current_text) < self.MAX_LENGTH:
            current_text += str(char)
        else:
            current_text = str(char)  # Clear the field and add the first character.

        self.ids.user_input_field.text = current_text

    def delete_character(self):
        '''
        Remove a character from the input field.
        '''
        current_text = self.ids.user_input_field.text

        if len(current_text) >= 1:
            current_text = current_text[:-1]
            self.ids.user_input_field.text = current_text

    def submit_code(self):
        '''
        Submit the code for verification.
        '''
        code_entered = self.ids.user_input_field.text
        self.verify_code(code_entered)

    def verify_code(self, code_entered, *args):
        '''
        Verify the code entered and handle switching screens accordingly.
        Each password can ONLY access:
        - Its own level screens
        - Level 0 screens (base access)
        
        In admin mode, all password checks are bypassed.
        Access is maintained until timeout.
        '''
        # Clear input field immediately
        self.ids.user_input_field.text = ''
        
        # Check if admin mode is currently active (no bypass for expired admin sessions)
        if self.app.admin_mode:
            self.app.switch_screen(self.app.target_screen)
            return
            
        # Get target screen's level
        target_level = self._get_screen_level(self.app.target_screen)
        
        # ALWAYS require password validation - no bypass based on current access level
        # This prevents the security vulnerability where any code works after initial access
        
        # Check if password exists in auth database
        access_level = self.app.auth_db.check_permissions(code_entered)
        if not access_level:
            # Return to previous screen on invalid code
            self.app.switch_screen(self.previous_screen)
            Logger.warning(f'CodeEntry: Invalid code entered: {code_entered}')
            return
            
        # Convert access level to int
        password_level = int(access_level)
        Logger.info(f'CodeEntry: Valid password entered with level {password_level} for target {self.app.target_screen} (requires level {target_level})')

        # Check for admin password (level 4)
        if password_level == 4:
            # Enable admin mode and set timeout
            self.app.admin_mode = True
            self.app.update_user_access(password_level)
            self.app.refresh_access_timeout()
            Logger.info(f'CodeEntry: Admin mode enabled for user with level {password_level}')
            self.app.switch_screen(self.app.target_screen)
            return

        # Allow access if:
        # 1. Target is level 0 (base access for all authenticated users)
        # 2. Password level is greater than or equal to target level (hierarchical access)
        if target_level == 0 or (target_level is not None and password_level >= target_level):
            # Update user access to allow access to this level and all below
            self.app.update_user_access(password_level)
            # Reset screen timeout since we just verified access
            self.app.refresh_access_timeout()
            Logger.info(f'CodeEntry: Access granted to {self.app.target_screen} with level {password_level}')
            self.app.switch_screen(self.app.target_screen)
            return

        # Return to previous screen if access not granted
        Logger.warning(f'CodeEntry: Access denied to {self.app.target_screen} - user level {password_level} insufficient for target level {target_level}')
        self.app.switch_screen(self.previous_screen)

    def _get_screen_level(self, screen_name):
        '''
        Get the access level required for a screen based on its directory location.
        Returns None if screen not found or level not determined.
        '''
        target_level = None
        target_screen_name = screen_name.lower()
        
        # Try both with and without _screen suffix
        possible_names = [
            f'{target_screen_name}.kv',
            f'{target_screen_name}_screen.kv'
        ]
        
        for root, _, files in os.walk(os.path.join(self.app._dir, 'views', 'kv')):
            for file in files:
                file_lower = file.lower()
                if any(file_lower == name for name in possible_names):
                    dir_name = os.path.basename(os.path.dirname(os.path.join(root, file)))
                    if dir_name.isdigit():
                        target_level = int(dir_name)
                        break
            if target_level is not None:
                break
                
        return target_level