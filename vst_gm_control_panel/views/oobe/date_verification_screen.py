'''
Date Verification Screen
'''

# Standard imports
from datetime import datetime
import subprocess
import time

# Kivy imports
from kivy.logger import Logger
from kivy.properties import StringProperty
from kivy.clock import Clock

# Local imports
from .base_oobe_screen import BaseOOBEScreen, OOBE_SCREEN_ORDER
from components import CustomDialog, NoDragMDBottomSheet


class DateVerificationScreen(BaseOOBEScreen):
    '''
    Date Verification Screen:
    - This screen allows the user to verify the current system date.
    - It provides options to verify the current date or enter a new date manually.
    '''
    
    current_date = StringProperty('')
    date_input_string = StringProperty('')
    
    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.screen_title = "DATE VERIFICATION"
        self.get_current_date()
        
    def on_enter(self):
        '''
        Called when the screen is entered (becomes active).
        '''
        self.get_current_date()
        
    def get_current_date(self):
        '''
        Get the current system date and update the display.
        '''
        now = datetime.now()
        
        # Format based on language
        if self.app.language == 'ES':
            # Spanish format: DD/MM/YYYY
            self.current_date = now.strftime('%d/%m/%Y')
        else:
            # English format: MM/DD/YYYY
            self.current_date = now.strftime('%m/%d/%Y')
            
    def on_verify(self):
        '''
        Handle verification of the current date.
        '''
        # Mark date verification as complete in the OOBE database
        self.app.oobe_db.add_setting('date_verified', 'true')
        
        # Check if timezone is verified
        if self.app.oobe_db.get_setting('timezone_verified', 'false') != 'true':
            # Navigate directly to timezone selection
            self.next_screen('OOBETimezoneSelection')
        else:
            # Otherwise, find the next incomplete step using the base class method
            self._go_to_next_screen()
            
    def _go_to_next_screen(self):
        '''
        Navigate to the next screen in the OOBE flow.
        Only skip QuickFunctionalityTest, PressureCalibration, and OverfillOverride screens if completed.
        '''
        self.go_to_next_incomplete_step(OOBE_SCREEN_ORDER)
        
    def on_manual_entry(self):
        '''
        Open the manual date entry keypad.
        '''
        self.date_input_string = ''
        self.ids.date_input_field.text = ''
        keypad_sheet = self.ids.date_keypad_sheet
        keypad_sheet.drawer_type = 'modal'
        keypad_sheet.set_state('toggle')
        
    def add_digit(self, digit):
        '''
        Add a digit to the date input field with automatic formatting.
        
        Args:
            digit: The digit to add (int)
        '''
        # Remove any slashes for processing
        clean_input = self.date_input_string.replace('/', '')
        
        # Maximum 8 digits (MM/DD/YYYY or DD/MM/YYYY)
        if len(clean_input) < 8:
            clean_input += str(digit)
            
            # Format with slashes
            if len(clean_input) <= 2:
                formatted = clean_input
            elif len(clean_input) <= 4:
                formatted = clean_input[:2] + '/' + clean_input[2:]
            else:
                formatted = clean_input[:2] + '/' + clean_input[2:4] + '/' + clean_input[4:]
                
            self.date_input_string = formatted
            self.ids.date_input_field.text = formatted
        
    def backspace(self):
        '''
        Remove the last character from the input field.
        '''
        if self.date_input_string:
            # Remove slashes for processing
            clean_input = self.date_input_string.replace('/', '')
            
            if clean_input:
                # Remove last digit
                clean_input = clean_input[:-1]
                
                # Reformat with slashes
                if len(clean_input) <= 2:
                    formatted = clean_input
                elif len(clean_input) <= 4:
                    formatted = clean_input[:2] + '/' + clean_input[2:]
                else:
                    formatted = clean_input[:2] + '/' + clean_input[2:4] + '/' + clean_input[4:]
                    
                self.date_input_string = formatted
                self.ids.date_input_field.text = formatted
            else:
                self.date_input_string = ''
                self.ids.date_input_field.text = ''
    
    def submit(self):
        '''
        Submit the date input and set the system date.
        '''
        if len(self.date_input_string.replace('/', '')) == 8:
            self.show_confirmation_dialog()
        
    def show_confirmation_dialog(self):
        '''
        Show a confirmation dialog before changing the system date.
        '''
        dialog = CustomDialog()
        title = self.app.language_handler.translate(
            'confirm_date_change',
            'Confirm Date Change?'
        )
        text_start = self.app.language_handler.translate(
            'confirm_date_change_message',
            'Are you sure you want to set the system date to '
        )
        text_end = self.app.language_handler.translate(
            'dialog_confirmation',
            "Click 'Accept' to confirm or 'Cancel' to return."
        )
        text = f'{text_start}{self.date_input_string}?\n\n{text_end}'
        accept = self.app.language_handler.translate('accept', 'Accept')
        cancel = self.app.language_handler.translate('cancel', 'Cancel')
        accept_method = self.set_system_date
        dialog.open_dialog(title, text, accept, accept_method, cancel)
        
    def set_system_date(self, *args):
        '''
        Set the system date based on the date input string.
        '''
        try:
            # Parse the date input
            parts = self.date_input_string.split('/')
            
            if self.app.language == 'ES':
                # Spanish format: DD/MM/YYYY
                day, month, year = parts
            else:
                # English format: MM/DD/YYYY
                month, day, year = parts
                
            # Get current time to preserve it
            now = datetime.now()
            current_time = now.strftime('%H:%M:%S')
            
            # Format for the `date` command
            date_command = f'{year}-{month}-{day} {current_time}'
            
            # Set the system time using the `date` command
            try:
                # First try to stop and disable systemd-timesyncd
                subprocess.run(['sudo', 'systemctl', 'stop', 'systemd-timesyncd'], check=True)
                subprocess.run(['sudo', 'systemctl', 'disable', 'systemd-timesyncd'], check=True)
                print('System-timesyncd disabled')
                
                # Then set the date
                subprocess.run(['sudo', 'date', '--set', date_command], check=True)
                print(f'System date set to {date_command}')
                
                # Calculate time difference for any time-dependent systems
                new_time = datetime.now()
                time_difference = new_time - now
                print(f'Time difference: {time_difference}')
                
                # Update any time-dependent systems if needed
                if hasattr(self.app, 'alarm_manager') and hasattr(self.app.alarm_manager, 'update_alarm_start_times'):
                    self.app.alarm_manager.update_alarm_start_times(time_difference)
                    
                if hasattr(self.app, 'profile_handler') and hasattr(self.app.profile_handler, 'load_alarms'):
                    self.app.profile_handler.load_alarms()
                    
                if hasattr(self.app, 'get_datetime'):
                    self.app.get_datetime()
                    
            except subprocess.CalledProcessError as e:
                Logger.error(f'OOBE: Error executing system command: {e}')
                # Continue with the flow even if date setting fails
            
            # Close the keypad sheet
            self.ids.date_keypad_sheet.set_state('toggle')
            
            # Mark date verification as complete
            self.app.oobe_db.add_setting('date_verified', 'true')
            
            # Check if timezone is verified
            if self.app.oobe_db.get_setting('timezone_verified', 'false') != 'true':
                # Navigate directly to timezone selection
                self.next_screen('OOBETimezoneSelection')
            else:
                # Otherwise, find the next incomplete step using the base class method
                self._go_to_next_screen()
            
        except Exception as e:
            Logger.error(f'OOBE: Failed to set system date: {e}')
            
    def go_back(self):
        '''
        Navigate to the previous screen in the OOBE flow, skipping any completed screens.
        '''
        self.go_back_skipping_completed(OOBE_SCREEN_ORDER)