'''
GM Serial Screen
'''

# Kivy imports
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.textfield import MDTextField

# Local imports
from .base_oobe_screen import BaseOOBEScreen, OOBE_SCREEN_ORDER


class GMSerialScreen(BaseOOBEScreen):
    '''
    GM Serial Screen:
    - This screen allows the user to enter the GM serial number.
    '''

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.screen_title = "GM SERIAL NUMBER"
        self.serial_number = ""
        
    def add_character(self, char):
        '''
        Add a character to the input field.
        '''
        current_text = self.ids.serial_input.text
        self.ids.serial_input.text = current_text + str(char)
        
    def delete_character(self):
        '''
        Remove a character from the input field.
        '''
        current_text = self.ids.serial_input.text
        
        if len(current_text) >= 1:
            current_text = current_text[:-1]
            self.ids.serial_input.text = current_text
        
    def on_serial_entered(self):
        '''
        Handle GM serial number entry.
        Validates that the serial number is one letter followed by six numbers.
        '''
        # Get the serial number from the text field
        serial_field = self.ids.serial_input
        self.serial_number = serial_field.text.strip()
        
        if not self.serial_number:
            # Show error if serial number is empty
            serial_field.error = True
            serial_field.helper_text = "Serial number cannot be empty"
            return
            
        # Validate format: 1 letter followed by 6 numbers
        if len(self.serial_number) != 7 or not self.serial_number[0].isalpha() or not self.serial_number[1:].isdigit():
            # Clear input and show error if format is invalid
            serial_field.error = True
            serial_field.helper_text = "Serial number must be 1 letter followed by 6 numbers (e.g. A123456)"
            serial_field.text = ""
            return
            
        # Save the serial number to the database
        self.app.gm_db.add_setting('gm_serial', self.serial_number)
        
        # Mark GM serial entry as complete
        self.app.oobe_db.add_setting('gm_serial_entered', 'true')
        
        # Navigate to the power info screen
        self.next_screen('OOBEPowerInfo')
        
    def go_back(self):
        '''
        Navigate to the previous screen in the OOBE flow, skipping any completed screens.
        '''
        self.go_back_skipping_completed(OOBE_SCREEN_ORDER)